from typing import Any, Callable, Dict, List, Optional, Type, Union, Literal

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
    StructuredResponseSchema,
)
from langgraph.pregel import Pregel


class ReactAgent(Pregel):
    """ReAct Agent class for reasoning and acting with tools.
    
    This class provides a high-level interface for creating a ReAct agent workflow
    that can perform multi-step reasoning and tool calling.
    """
    
    def __init__(
        self,
        model: LanguageModelLike,
        tools: Optional[List[Union[BaseTool, Callable]]] = None,
        prompt: Optional[str] = None,
        response_format: Optional[
            Union[StructuredResponseSchema, tuple[str, StructuredResponseSchema]]
        ] = None,
        state_schema: StateSchemaType = AgentState,
        config_schema: Type[Any] = None,
        interrupt_before: Optional[List[str]] = None,
        interrupt_after: Optional[List[str]] = None,
        debug: bool = False,
        version: Literal["v1", "v2"] = "v1",
        name: str = "react_agent",
    ):
        """Initialize a ReAct agent.
        
        Args:
            model: Language model to use for the agent
            tools: Optional list of tools available to the agent
            prompt: Optional prompt to use for the agent
            response_format: Optional schema for structured output
            state_schema: State schema to use for the agent graph
            config_schema: Optional schema for configuration
            interrupt_before: Optional list of nodes to interrupt before execution
            interrupt_after: Optional list of nodes to interrupt after execution
            debug: Whether to enable debug mode
            version: Version of the ReAct agent ("v1" or "v2")
            name: Name of the agent
        """
        self.model = model
        self.tools = tools or []
        self.prompt = prompt
        self.response_format = response_format
        self.state_schema = state_schema
        self.config_schema = config_schema
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug
        self.version = version
        self.name = name
        self._workflow = None
        self._app = None
    
    def build(self) -> StateGraph:
        """Build the ReAct agent workflow.
        
        Returns:
            The built StateGraph
        """
        
        self._workflow = create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=self.prompt,
            response_format=self.response_format,
            state_schema=self.state_schema,
            config_schema=self.config_schema,
            interrupt_before=self.interrupt_before,
            interrupt_after=self.interrupt_after,
            debug=self.debug,
            version=self.version,
            name=self.name,
        )
        
        return self._workflow
    
    def compile(self):
        """Compile the ReAct agent workflow.
        
        Returns:
            The compiled application
        """
        if self._workflow is None:
            self.build()
        
        self._app = self._workflow
        return self._app
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the ReAct agent with the given state.
        
        Args:
            state: Current state of the conversation
            
        Returns:
            Updated state after agent processing
        """
        if self._app is None:
            self.compile()
        
        return self._app.invoke(state)
    
    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously invoke the ReAct agent with the given state.
        
        Args:
            state: Current state of the conversation
            
        Returns:
            Updated state after agent processing
        """
        if self._app is None:
            self.compile()
        
        return await self._app.ainvoke(state)
    
    def stream(self, state: Dict[str, Any], **kwargs) -> Any:
        """Stream the ReAct agent execution with the given state.
        
        This method allows monitoring the intermediate states during execution,
        which is useful for tracking the agent's reasoning process and tool calls.
        
        Args:
            state: Current state of the conversation
            **kwargs: Additional arguments to pass to the stream method
            
        Returns:
            Iterator over intermediate states
        """
        if self._app is None:
            self.compile()
        
        return self._app.stream(state, **kwargs)
    
    def get_graph(self) -> StateGraph:
        """Get the underlying graph of the ReAct agent.
        
        Returns:
            The StateGraph object
        """
        if self._workflow is None:
            self.build()
        
        return self._workflow