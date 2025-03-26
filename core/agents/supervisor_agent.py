from typing import Any, Callable, Dict, List, Optional, Union
import re

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from core.agents.supervisor import create_supervisor
from core.agents.supervisor.simple_planning_tool import SimplePlanningTool
from core.agents.base.base_agent import BaseAgent
from core.agents.supervisor.state_schema import PlanningAgentState
import logging

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    """Supervisor class for managing multiple agents with planning capabilities.
    
    This class provides a high-level interface for creating a supervisor workflow
    that can manage and coordinate multiple agents. It also includes planning capabilities
    to create and manage a plan for complex tasks using a state-driven approach.
    
    The planning functionality is implemented using PlanningStateHandler and PlanningTool,
    which provide a more structured and flexible way to manage tasks compared to the
    previous TodolistTool approach.
    """
    _PROMPT_TEMPLATE = """You are a Supervisor Agent. Your job is to analyze user requests and coordinate multiple agents to complete tasks.

## Task Approach Methodology

### Understanding Requirements
- Analyzing user requests to identify core needs
- Asking clarifying questions when requirements are ambiguous
- Breaking down complex requests into manageable components
- Identifying potential challenges before beginning work

### Coordination
- Identifying appropriate agents for each task
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
 {tools}
"""

    _PLANNING_PROMPT_TEMPLATE = """You are a Supervisor agent. Your role is to analyze user requests, break them down into actionable tasks, and coordinate specialized agents (e.g., research_expert, coder_expert, reporter_expert) to complete them.

# Task Coordination Rules
1. Understand the user's request and break it down into steps if necessary.
2. Assign each step to the most appropriate agent. Call the relevant handoff tool to transfer control to that agent.
3. Wait for the agent's response before proceeding to the next step.
4. Maintain a single plan if needed, and do not recreate it unless no plan exists.

# Communication
- Provide clear instructions and outputs to the user.
- Use your specialized agents to handle sub-problems one at a time.
- Return a final answer that addresses the original user request.
"""

    _PLANNING_TOOL_TEMPLATE = """
# Planning Tool Instructions
You have access to a "planning" tool that uses JSON for all operations. Do NOT include any "state" field in your calls. Use the following actions exactly as defined:

1. "create_plan": Create a new plan.
   - Required fields:
     - title (string)
     - description (string)
     - tasks (list of task objects). Each task object must include:
         "description": string,
         "status": "pending" (all tasks must have "status": "pending" initially),
         "agent": string (empty if not assigned),
         "notes": string (empty if none),
         "evaluation": string (empty if none)
   - Example:
   {
     "action": "create_plan",
     "title": "Python Scraper for Tech News",
     "description": "Build a Python scraper to fetch the latest tech news and save it as CSV",
     "tasks": [
       {"description": "Research Python scraping libraries", "status": "pending", "agent": "", "notes": "", "evaluation": ""},
       {"description": "Implement the scraper", "status": "pending", "agent": "", "notes": "", "evaluation": ""},
       {"description": "Test the code", "status": "pending", "agent": "", "notes": "", "evaluation": ""}
     ]
   }

2. "view_plan": Retrieve the current plan.
   - Example:
   {
     "action": "view_plan"
   }

3. "add_tasks": Add additional tasks to the plan.
   - Required:
     - tasks: list of task objects (same format as above)
   - Example:
   {
     "action": "add_tasks",
     "tasks": [
       {"description": "Write documentation", "status": "pending", "agent": "", "notes": "", "evaluation": ""}
     ]
   }

4. "update_task": Update an existing task.
   - Identify the task by "by_id" (the task's unique ID from the plan).
   - You may update any of: "description", "status", "agent", "notes", "evaluation".
   - Example:
   {
     "action": "update_task",
     "by_id": "TASK-UUID",
     "status": "completed",
     "evaluation": "The scraper works perfectly."
   }

5. "set_current_task": Set the current task by its ID.
   - Example:
   {
     "action": "set_current_task",
     "task_id": "TASK-UUID"
   }

6. "finish_plan": Mark the entire plan as completed.
   - Example:
   {
     "action": "finish_plan"
   }

Important:
- Always produce valid JSON for your tool calls.
- Continuously update and monitor the plan until every task's status is "completed" before delivering your final answer.
- If the plan is not fully completed, do not stop; keep updating the plan with appropriate calls.
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
        enable_planning: bool = True, # * True or False *
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
            enable_planning: Whether to enable planning capabilities
            auto_planning: Whether to automatically generate plans for complex tasks
        """
        # 设置规划相关属性
        self._enable_planning = enable_planning
        
        # 如果启用规划功能，设置状态模式为PlanningAgentState
        if self._enable_planning and state_schema == AgentState:
            state_schema = PlanningAgentState
            
        # Store agent-specific attributes before super().__init__
        self.agents = agents
        self.output_mode = output_mode
        self.supervisor_name = supervisor_name
        self.state_schema = state_schema
        self.checkpointer = checkpointer
        self.tools = tools or []
        self._workflow = None
        self._agent = None
            
        # 生成基础提示词
        # _agents_prompt = self._generate_agents_prompt()
        _final_prompt = self._PLANNING_PROMPT_TEMPLATE + "/n/n" + self._PLANNING_TOOL_TEMPLATE if self._enable_planning else self._PROMPT_TEMPLATE
        
        if tools is None:
            tools = []
        # 如果启用规划功能，添加规划提示模板并添加规划工具
        if self._enable_planning:
            tools.append(SimplePlanningTool())
        
        # 初始化BaseAgent父类
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

    def compile(self) -> CompiledStateGraph:
        return super().compile()
    
   
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
        
        # agent_descriptions.append("\n## Agent Selection Guidelines\n")
        # agent_descriptions.append("When deciding which agent to use for a task:\n")
        # agent_descriptions.append("1. Consider the primary nature of the task (research, coding, reporting, design, data analysis, etc.)")
        # agent_descriptions.append("2. For complex tasks, break them down and assign different components to appropriate agents")
        # agent_descriptions.append("3. Ensure clear handoffs between agents when multiple agents are needed")
        # agent_descriptions.append("4. Synthesize outputs from multiple agents into a coherent response")
        # agent_descriptions.append("\n## Handoff Guidelines\n")
        # agent_descriptions.append("When transferring tasks between agents:\n")
        # agent_descriptions.append("1. Provide clear and specific instructions about what you need the agent to accomplish")
        # agent_descriptions.append("2. Include all necessary context and background information in your handoff")
        # agent_descriptions.append("3. Specify the expected output format or deliverables you need from the agent")
        # agent_descriptions.append("4. Use handoffs only when the task clearly aligns with a specialized agent's capabilities")
        # agent_descriptions.append("5. ALWAYS wait for the agent to COMPLETELY finish their current task before proceeding")
        # agent_descriptions.append("6. NEVER delegate tasks to multiple agents simultaneously")
        # agent_descriptions.append("7. When an agent returns control to you, thoroughly review their output before proceeding")
        # agent_descriptions.append("8. Confirm task completion before moving to the next task or agent")
        # agent_descriptions.append("9. For multi-step processes, maintain a strict sequential order of handoffs with proper context preservation")
        
        return "\n".join(agent_descriptions)