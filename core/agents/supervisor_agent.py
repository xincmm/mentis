from typing import Any, Callable, Dict, List, Optional, Union
import re

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from core.agents.supervisor import create_supervisor
from core.agents.base.base_agent import BaseAgent
from core.agents.react_agent import ReactAgent
from core.agents.research_agent import ResearchAgent
from core.agents.coder_agent import CoderAgent
from core.agents.reporter_agent import ReporterAgent
from core.agents.designer_agent import DesignerAgent
from core.agents.data_analyst_agent import DataAnalystAgent
from core.tools.todolist_tool import TodolistTool

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
        
        # 方案一和方案二的实现
        base_prompt = ""
        if enable_planning:
            base_prompt = self._PLANNING_PROMPT_TEMPLATE
        else:
            base_prompt = self._BASE_PROMPT_TEMPLATE
            
        if prompt is None:
            # 方案二：根据传入的agents自动生成适配的提示词
            agents_prompt = self._generate_agents_prompt(agents)
            prompt = base_prompt + agents_prompt
        else:
            # 方案一：将自定义prompt追加到默认提示词后面
            prompt = base_prompt + "\n\n" + prompt
        
        # Initialize the BaseAgent parent class
        super().__init__(
            name=supervisor_name,
            model=model,
            tools=tools,
            prompt=prompt,
        )
        
        # Store supervisor-specific attributes
        self.agents = agents
        self.output_mode = output_mode
        self.supervisor_name = supervisor_name
        self.state_schema = state_schema
        self._workflow = None
        self._app = None
    
    def build(self) -> StateGraph:
        """Build the supervisor workflow.
        
        Returns:
            The built StateGraph
        """
        if self._workflow is not None:
            return self._workflow
            
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
        
    def get_agent(self) -> StateGraph:
        """Get the underlying supervisor workflow.
        
        Returns:
            The StateGraph object
        """
        if self._workflow is None:
            self._workflow = self.build()
            
        return self._workflow
        
    def compile(self) -> CompiledStateGraph: 
        """Compile the supervisor workflow.
        
        Returns:
            The compiled application
        """
        if self._workflow is None:
            self.build()
        
        self._app = self._workflow.compile()
        return self._app
        
    def _generate_agents_prompt(self, agents: List[ReactAgent]) -> str:
        """Generate a prompt based on the types of agents provided.
        
        This method analyzes the agent types and generates appropriate descriptions
        for each agent to be included in the supervisor prompt.
        
        Args:
            agents: List of agents to generate descriptions for
            
        Returns:
            A string containing descriptions of all agents
        """
        agent_descriptions = []
        agent_descriptions.append("\n\n## Available Agents\n")
        agent_descriptions.append("You have access to the following specialized agents:\n")
        
        for agent in agents:
            if isinstance(agent, dict) and "name" in agent:
                # Handle dict-like agents with name attribute
                agent_name = agent["name"]
            elif hasattr(agent, "name"):
                # Handle object-like agents with name attribute
                agent_name = agent.name
            else:
                # Skip agents without name
                continue
                
            # Generate description based on agent type or name
            if "research" in agent_name.lower() or isinstance(agent, ResearchAgent):
                agent_descriptions.append(f"- **{agent_name}**: Specialized in gathering information and conducting research. Use for tasks requiring information retrieval, fact-checking, and synthesizing data from multiple sources.")
            elif "coder" in agent_name.lower() or isinstance(agent, CoderAgent):
                agent_descriptions.append(f"- **{agent_name}**: Specialized in writing, debugging, and optimizing code. Use for programming tasks, code generation, and technical problem-solving.")
            elif "reporter" in agent_name.lower() or isinstance(agent, ReporterAgent):
                agent_descriptions.append(f"- **{agent_name}**: Specialized in creating comprehensive reports and documentation. Use for summarizing information, creating structured documents, and presenting findings.")
            elif "designer" in agent_name.lower() or isinstance(agent, DesignerAgent):
                agent_descriptions.append(f"- **{agent_name}**: Specialized in UI/UX design and visual communication. Use for creating design mockups, improving user interfaces, and visual elements.")
            elif "data" in agent_name.lower() and "analyst" in agent_name.lower() or isinstance(agent, DataAnalystAgent):
                agent_descriptions.append(f"- **{agent_name}**: Specialized in data analysis and visualization. Use for analyzing datasets, creating visualizations, and extracting insights from data.")
            elif "joke" in agent_name.lower():
                agent_descriptions.append(f"- **{agent_name}**: Specialized in generating humor and entertainment content. Use for creating jokes, witty remarks, and light-hearted content.")
            else:
                # Generic description for unknown agent types
                agent_descriptions.append(f"- **{agent_name}**: A specialized agent that can help with specific tasks.")
        
        agent_descriptions.append("\n## Agent Selection Guidelines\n")
        agent_descriptions.append("When deciding which agent to use for a task:\n")
        agent_descriptions.append("1. Consider the primary nature of the task (research, coding, reporting, design, data analysis, etc.)")
        agent_descriptions.append("2. For complex tasks, break them down and assign different components to appropriate agents")
        agent_descriptions.append("3. Ensure clear handoffs between agents when multiple agents are needed")
        agent_descriptions.append("4. Synthesize outputs from multiple agents into a coherent response")
        
        return "\n".join(agent_descriptions)
