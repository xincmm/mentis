from typing import Any, Callable, Dict, List, Optional, Type, Union, Literal, Sequence

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    StateSchemaType,
    StructuredResponseSchema,
)
from core.agents.base.base_agent import BaseAgent


class ReactAgent(BaseAgent):
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
        checkpointer: Optional[Checkpointer] = None,
        store: Optional[BaseStore] = None,
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
        self.checkpointer = checkpointer
        self.store = store
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug
        self.version = version
        self.name = name
        self._agent = None
    
    def compile(self) -> CompiledGraph:
        """Build the ReAct agent workflow.
        
        Returns:
            The built CompiledGraph
        """
        # 如果_app已经存在，直接返回，避免重复构建
        if self._agent is not None:
            return self._agent
            
        self._agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=self.prompt,
            response_format=self.response_format,
            state_schema=self.state_schema,
            config_schema=self.config_schema,
            checkpointer=self.checkpointer,
            store=self.store,
            interrupt_before=self.interrupt_before,
            interrupt_after=self.interrupt_after,
            debug=self.debug,
            version=self.version,
            name=self.name,
        )
        
        return self._agent
    
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
        # 确保应用已编译
        if self._agent is None:
            self.compile()
        
        return self._agent.stream(state, **kwargs)