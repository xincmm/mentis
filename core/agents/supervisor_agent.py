from typing import Any, Callable, Dict, List, Optional, Union
import re

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.types import Checkpointer
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from core.agents.supervisor import create_supervisor
from core.agents.base.base_agent import BaseAgent
from core.tools.todolist_tool import TodolistTool
import logging

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    """Supervisor class for managing multiple agents with planning capabilities.
    
    This class provides a high-level interface for creating a supervisor workflow
    that can manage and coordinate multiple agents. It also includes planning capabilities
    to create and manage a todolist for complex tasks.
    """
    
    _PLANNING_PROMPT_TEMPLATE = """You are a Planning Supervisor Agent. Your job is to analyze user requests, create a clear todolist, and coordinate multiple agents to complete tasks.

## Task Approach Methodology

### Understanding Requirements
- Analyzing user requests to identify core needs
- Asking clarifying questions when requirements are ambiguous
- Breaking down complex requests into manageable components
- Identifying potential challenges before beginning work

### Planning
- Creating a structured todolist for task completion
- Identifying appropriate tools or agents for each subtask
- Coordinating the execution of the plan
- Tracking progress and updating the todolist as tasks are completed

## Todolist Tool Usage Guide

You have access to a todolist tool that can help you manage tasks. Here's how to use it:

1. **Create a todolist**:
   - Use `todolist("create", plan_content="Your detailed plan here")` 
   - The plan_content MUST be formatted as a Markdown todolist with each task on a new line
   - Example: `todolist("create", plan_content="- [ ] Research topic\n- [ ] Write outline\n- [ ] Draft content")`
   - Alternatively, you can use a numbered list format: `todolist("create", plan_content="1. Research topic\n2. Write outline\n3. Draft content")`

2. **View the current todolist**:
   - Use `todolist("view")` to see all current tasks and their status

3. **Add a new task**:
   - Use `todolist("add task", task_description="Description of the new task")`
   - Example: `todolist("add task", task_description="Review final draft")`

4. **Update task status**:
   - By index: `todolist("update_by_index", task_index=0, completed=True)` (indexes start at 0)
   - By description: `todolist("update_by_description", task_description="Research topic", completed=True)`

## Working with Complex Requests

1. FIRST, carefully analyze the user's request and break it down into clear, actionable tasks
2. Create a COMPLETE todolist using the todolist tool with ALL anticipated tasks before starting execution
3. Execute the plan step by step, addressing tasks sequentially
4. Update the todolist as tasks are completed
5. Provide a final summary when all tasks are done

## IMPORTANT: Planning Guidelines

- Always create a comprehensive todolist BEFORE beginning execution
- Your initial plan should include ALL foreseeable tasks needed to complete the request
- Include a brief restatement of the user's request at the beginning of your plan
- Create clear, specific, and actionable tasks in your todolist
- Only add new tasks during execution if absolutely necessary for unexpected requirements
- Mark tasks as 'done' only when fully completed
- Update the todolist before proceeding to the next task
- When creating a todolist, provide detailed task descriptions (at least 15 characters per task)
- Ensure each task is specific and actionable

Remember: A well-structured todolist is essential for successful task completion. Take time to create a thorough plan before beginning execution.
"""

    _BASE_PROMPT_TEMPLATE = """You are a Supervisor Agent. Your job is to analyze user requests and coordinate multiple agents to complete tasks.

## Task Approach Methodology

### Understanding Requirements
- Analyzing user requests to identify core needs
- Asking clarifying questions when requirements are ambiguous
- Breaking down complex requests into manageable components
- Identifying potential challenges before beginning work

### Coordination
- Identifying appropriate agents for each subtask
- Delegating tasks to specialized agents
- Tracking progress and ensuring task completion
- Synthesizing information from multiple agents

## Working with Complex Requests

1. FIRST, carefully analyze the user's request and break it down into clear, actionable tasks
2. Identify which agent is best suited for each part of the task
3. Use the handoff tools to delegate tasks to appropriate agents ONE AT A TIME
4. WAIT for each agent to COMPLETELY FINISH their assigned task before proceeding
5. Review the output from each agent before delegating the next task
6. Maintain a sequential workflow - never delegate multiple tasks simultaneously
7. Synthesize the results and provide a coherent response to the user
8. Provide a final summary when all tasks are done

Remember: Effective coordination is essential for successful task completion. Take time to understand the request and delegate appropriately.
"""

    def __init__(
        self,
        agents: List[BaseAgent],
        model: LanguageModelLike,
        tools: Optional[List[Union[BaseTool, Callable]]] = None,
        prompt: Optional[str] = None,
        state_schema: StateSchemaType = AgentState,
        supervisor_name: str = "supervisor",
        checkpointer: Optional[Checkpointer] = None,
        output_mode: str = "last_message", # * full_history or last_message *
        enable_planning: bool = False,
    ):
        """Initialize a supervisor.
        
        Args:
            agents: List of agents to manage
            model: Language model to use for the supervisor
            tools: Optional list of tools available to the supervisor
            prompt: Optional prompt to use for the supervisor
            state_schema: State schema to use for the supervisor graph
            supervisor_name: Name of the supervisor node
            checkpointer: Optional checkpointer to use for the supervisor
            output_mode: Mode for adding agent outputs to the message history
                ("full_history" or "last_message")
            enable_planning: Whether to enable planning capabilities with todolist
        """
        # Create todolist tool if planning is enabled
        self._enable_planning = enable_planning
        self._todolist_tool = TodolistTool() if enable_planning else None
        
        # Add todolist tool to the tools list if planning is enabled
        if enable_planning and tools is not None:
            tools = tools + [self._todolist_tool]
        elif enable_planning:
            tools = [self._todolist_tool]
        
        # Determine the base prompt based on planning mode
        base_prompt = self._PLANNING_PROMPT_TEMPLATE if enable_planning else self._BASE_PROMPT_TEMPLATE
            
        # Store agent-specific attributes before super().__init__
        self.agents = agents
        self.output_mode = output_mode
        self.supervisor_name = supervisor_name
        self.state_schema = state_schema
        self.checkpointer = checkpointer
        self._workflow = None
        self._agent = None
        
        # Generate final prompt
        _final_prompt = base_prompt
        if prompt is None:
            # Generate prompt based on available agents
            _agents_prompt = self._generate_agents_prompt()
            _final_prompt = base_prompt + _agents_prompt
        else:
            # Append custom prompt to default template
            _final_prompt = base_prompt + "\n\n" + prompt
        
        # Initialize the BaseAgent parent class
        super().__init__(
            name=supervisor_name,
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=_final_prompt,
        )
    
    def build(self) -> StateGraph:
        """Build the supervisor workflow.
        
        Returns:
            The built StateGraph
        """
        if self._workflow is not None:
            return self._workflow
            
        # Get the agent objects from BaseAgent instances
        agent_objects = []
        for agent in self.agents:
            if hasattr(agent, "get_agent") and callable(agent.get_agent):
                try:
                    agent_objects.append(agent.get_agent())
                except Exception as e:
                    logger.warning(f"Failed to get agent from {agent.name}: {str(e)}")
                    # Fallback to using the agent directly if get_agent fails
                    agent_objects.append(agent)
            else:
                # If the agent doesn't have a get_agent method, use it directly
                agent_objects.append(agent)
            
        self._workflow = create_supervisor(
            agents=agent_objects,
            model=self.model,
            tools=self.tools,
            prompt=self.prompt,
            state_schema=self.state_schema,
            supervisor_name=self.supervisor_name,
            output_mode=self.output_mode,
        )
        
        return self._workflow

        
    def _generate_agents_prompt(self) -> str:
        """Generate a prompt based on the types of agents provided.
        
        This method analyzes the agent types and generates appropriate descriptions
        for each agent to be included in the supervisor prompt.
            
        Returns:
            A string containing descriptions of all agents
        """
        agent_descriptions = []
        agent_descriptions.append("\n\n## Available Agents\n")
        agent_descriptions.append("You have access to the following specialized agents:\n")
        
        for agent in self.agents:
            if isinstance(agent, dict) and "name" in agent:
                # Handle dict-like agents with name attribute
                agent_name = agent["name"]
                agent_desc = agent.get("description", f"Handles tasks related to '{agent_name}'")
            elif hasattr(agent, "name"):
                # Handle object-like agents with name attribute
                agent_name = agent.name
                agent_desc = getattr(agent, "description", f"Handles tasks related to '{agent_name}'")
            else:
                # Skip agents without name
                continue
                
            agent_descriptions.append(f"- **{agent_name}**: {agent_desc}")
        
        agent_descriptions.append("\n## Agent Selection Guidelines\n")
        agent_descriptions.append("When deciding which agent to use for a task:\n")
        agent_descriptions.append("1. Consider the primary nature of the task (research, coding, reporting, design, data analysis, etc.)")
        agent_descriptions.append("2. For complex tasks, break them down and assign different components to appropriate agents")
        agent_descriptions.append("3. Ensure clear handoffs between agents when multiple agents are needed")
        agent_descriptions.append("4. Synthesize outputs from multiple agents into a coherent response")
        
        agent_descriptions.append("\n## Handoff Guidelines\n")
        agent_descriptions.append("When transferring tasks between agents:\n")
        agent_descriptions.append("1. Provide clear and specific instructions about what you need the agent to accomplish")
        agent_descriptions.append("2. Include all necessary context and background information in your handoff")
        agent_descriptions.append("3. Specify the expected output format or deliverables you need from the agent")
        agent_descriptions.append("4. Use handoffs only when the task clearly aligns with a specialized agent's capabilities")
        agent_descriptions.append("5. ALWAYS wait for the agent to COMPLETELY finish their current task before proceeding")
        agent_descriptions.append("6. NEVER delegate tasks to multiple agents simultaneously")
        agent_descriptions.append("7. When an agent returns control to you, thoroughly review their output before proceeding")
        agent_descriptions.append("8. Confirm task completion before moving to the next task or agent")
        agent_descriptions.append("9. For multi-step processes, maintain a strict sequential order of handoffs with proper context preservation")
        
        return "\n".join(agent_descriptions)
