from typing import Any, Callable, Dict, List, Optional, Union

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
)
from langgraph.pregel import Pregel
from core.agents.supervisor import create_supervisor

class SupervisorAgent(Pregel):
    """Supervisor class for managing multiple agents.
    
    This class provides a high-level interface for creating a supervisor workflow
    that can manage and coordinate multiple agents.
    """
    
    def __init__(
        self,
        agents: List[Pregel],
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
        self.agents = agents
        self.model = model
        self.tools = tools or []
        self.prompt = prompt
        self.state_schema = state_schema
        self.supervisor_name = supervisor_name
        self.output_mode = output_mode
        self._workflow = None
        self._app = None
    
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
    
    def compile(self):
        """Compile the supervisor workflow.
        
        Returns:
            The compiled application
        """
        if self._workflow is None:
            self.build()
        
        self._app = self._workflow.compile()
        return self._app
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the supervisor with the given state.
        
        Args:
            state: Current state of the conversation
            
        Returns:
            Updated state after supervisor processing
        """
        if self._app is None:
            self.compile()
        
        return self._app.invoke(state)
    
    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously invoke the supervisor with the given state.
        
        Args:
            state: Current state of the conversation
            
        Returns:
            Updated state after supervisor processing
        """
        if self._app is None:
            self.compile()
        
        return await self._app.ainvoke(state)