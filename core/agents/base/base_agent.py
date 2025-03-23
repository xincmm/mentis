from typing import Any, Dict, List, Optional, Type, Union, Callable

from langchain_core.language_models import BaseChatModel, LanguageModelLike
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable, RunnableCallable
from langgraph.pregel import Pregel


class BaseAgent:
    """Base agent class for the multi-agent architecture.

    This class defines the interface for all agents in the system.
    """

    def __init__(
        self,
        name: str,
        model: Union[BaseChatModel, LanguageModelLike],
        tools: Optional[List[BaseTool]] = None,
        prompt: Optional[Union[str, SystemMessage, Callable, Runnable]] = None,  # 允许字符串
    ):
        """Initialize the base agent.

        Args:
            name: Name of the agent.
            model: Language model to use for the agent.  Can be a ChatModel or a more general LanguageModelLike.
            tools: Optional list of tools available to the agent.
            prompt: Optional prompt for the agent.
        """
        self.name = name
        self.model = model
        self.tools = tools or []
        self.prompt = prompt
        self._agent = None  # Will be set by subclasses

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the agent with the given state.

        Args:
            state: Current state of the conversation.

        Returns:
            Updated state after agent processing.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("Subclasses must implement this method")

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronously invoke the agent with the given state.

        Args:
            state: Current state of the conversation.

        Returns:
            Updated state after agent processing.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def get_runnable(self) -> RunnableCallable:
        """Get a runnable callable from this agent.
        
        Returns:
            A RunnableCallable that wraps this agent's invoke and ainvoke methods.
        """
        return RunnableCallable(self.invoke, self.ainvoke)
    
    def get_agent(self) -> Pregel:
        """Get the underlying agent implementation.

        Returns:
            The agent implementation (Pregel instance).

        Raises:
            ValueError: If the agent has not been initialized.
        """
        if self._agent is None:
            raise ValueError("Agent not initialized")
        return self._agent

    def reset(self):
        """Resets the agent's state."""
        pass