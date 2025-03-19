from typing import Any, Callable, Dict, List, Optional, Union

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from core.agents.supervisor import create_supervisor
from core.agents.react_agent import ReactAgent

class SupervisorAgent(ReactAgent):
    """Supervisor class for managing multiple agents.
    
    This class provides a high-level interface for creating a supervisor workflow
    that can manage and coordinate multiple agents.
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
        """
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