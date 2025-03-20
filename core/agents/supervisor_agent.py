from typing import Any, Callable, Dict, List, Optional, Union
import re

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from core.agents.supervisor import create_supervisor
from core.agents.react_agent import ReactAgent
from core.tools.todolist_tool import TodolistTool

class SupervisorAgent(ReactAgent):
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
3. Use the handoff tools to delegate tasks to appropriate agents
4. Synthesize the results and provide a coherent response to the user
5. Provide a final summary when all tasks are done

## IMPORTANT: Coordination Guidelines

- Always analyze the user's request thoroughly before delegating tasks
- Choose the most appropriate agent for each subtask based on their capabilities
- Provide clear instructions when handing off tasks to other agents
- Maintain context and continuity throughout the conversation
- Synthesize information from multiple agents into coherent responses

Remember: Effective coordination is essential for successful task completion. Take time to understand the request and delegate appropriately.
"""

    def __init__(
        self,
        agents: List[ReactAgent],
        model: LanguageModelLike,
        tools: Optional[List[Union[BaseTool, Callable]]] = None,
        prompt: Optional[str] = None,
        state_schema: StateSchemaType = AgentState,
        supervisor_name: str = "supervisor",
        output_mode: str = "last_message",
        enable_planning: bool = True,
    ):
        """Initialize a supervisor.
        
        Args:
            agents: List of agents to manage
            model: Language model to use for the supervisor
            tools: Optional list of tools available to the supervisor
            prompt: Optional prompt to use for the supervisor
            state_schema: State schema to use for the supervisor graph
            supervisor_name: Name of the supervisor node
            output_mode: Mode for adding agent outputs to the message history
                ("full_history" or "last_message")
            enable_planning: Whether to enable planning capabilities with todolist
        """
        # Create todolist tool if planning is enabled
        self.enable_planning = enable_planning
        self.todolist_tool = TodolistTool() if enable_planning else None
        
        # Add todolist tool to the tools list if planning is enabled
        if enable_planning and tools is not None:
            tools = tools + [self.todolist_tool]
        elif enable_planning:
            tools = [self.todolist_tool]
        
        # Use appropriate prompt template if no custom prompt is provided
        if prompt is None:
            if enable_planning:
                prompt = self._PLANNING_PROMPT_TEMPLATE
            else:
                prompt = self._BASE_PROMPT_TEMPLATE
        
        # Initialize the ReactAgent parent class
        super().__init__(
            model=model,
            tools=tools,
            prompt=prompt,
            state_schema=state_schema,
            name=supervisor_name,
        )
        
        # Store supervisor-specific attributes
        self.agents = agents
        self.output_mode = output_mode
        self.supervisor_name = supervisor_name
    
    def build(self) -> StateGraph:
        """Build the supervisor workflow.
        
        Returns:
            The built StateGraph
        """
        
        self._workflow = create_supervisor(
            agents=self.agents,
            model=self.model,
            tools=self.tools,
            prompt=self.prompt,
            state_schema=self.state_schema,
            supervisor_name=self.supervisor_name,
            output_mode=self.output_mode,
        )
        
        return self._workflow