from typing import List, Dict, Any, Optional, Union, Callable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.types import Checkpointer
from langgraph.graph.state import CompiledStateGraph
from langgraph.utils.runnable import RunnableCallable
import logging

logger = logging.getLogger(__name__)

# === BaseAgent ===
class BaseAgent:
    def __init__(
        self,
        name: str,
        model: Union[BaseChatModel, LanguageModelLike],
        tools: Optional[List[BaseTool]] = None,
        prompt: Optional[Union[str, SystemMessage, Callable]] = None,
        checkpointer: Optional[Checkpointer] = None,
        max_context_messages: Optional[int] = None,  # Limit number of recent messages
        max_context_tokens: Optional[int] = None,    # Limit total estimated tokens
        model_name: Optional[str] = "gpt-4o-mini", # Optional, used for future token estimation improvements
    ):
        if max_context_messages and max_context_tokens:
            raise ValueError("Only one of max_context_messages or max_context_tokens should be set.")

        self.name = name
        self.model = model
        self.tools = tools or []
        self.prompt = prompt
        self.checkpointer: Checkpointer = checkpointer
        self.max_context_messages = max_context_messages
        self.max_context_tokens = max_context_tokens
        self.model_name = model_name
        self._workflow = None
        self._agent = None

    def _estimate_tokens(self, message: BaseMessage) -> int:
        """
        Estimate tokens using a naive character-length approximation.
        You can replace this with tiktoken or other tokenizer in future.
        """
        content = getattr(message, "content", str(message))
        return len(content) // 2

    def _truncate_by_tokens(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Truncate messages from the end based on token estimation.
        """
        truncated = []
        total_tokens = 0
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens(msg)
            if total_tokens + msg_tokens > self.max_context_tokens:
                break
            truncated.append(msg)
            total_tokens += msg_tokens
        return list(reversed(truncated))

    def _truncate_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Truncate messages using either token count or message count.
        """
        if self.max_context_messages is not None:
            return messages[-self.max_context_messages:]
        elif self.max_context_tokens is not None:
            return self._truncate_by_tokens(messages)
        return messages

    def _inject_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject memory and truncate messages based on configuration.
        """
        memory = state.get("memory") or []
        messages = state.get("messages", [])
        messages = self._truncate_messages(messages)
        memory_messages = [SystemMessage(content=chunk) for chunk in memory]
        state["messages"] = memory_messages + messages
        return state
    
    def build(self) -> StateGraph:
        """Build the supervisor workflow.
        
        Returns:
            The built StateGraph
        """
        if self._workflow is not None:
            return self._workflow

        # Build the workflow using LangGraph
        self._workflow = StateGraph()
        return self._workflow  # Return the workflow, not 'self
        
    def compile(self) -> CompiledStateGraph: 
        """Compile the supervisor workflow.
        
        Returns:
            The compiled application
        """
        if self._workflow is None:
            self.build()
        
        self._agent = self._workflow.compile(checkpointer=self.checkpointer)
        return self._agent
        
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the supervisor workflow synchronously.
        
        Args:
            state: The input state for the workflow
            
        Returns:
            The output state from the workflow
        """
        if self._agent is None:
            self.compile()
            
        # Apply context injection from BaseAgent
        state = self._inject_context(state)
        
        return self._agent.invoke(state)
        
    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the supervisor workflow asynchronously.
        
        Args:
            state: The input state for the workflow
            
        Returns:
            The output state from the workflow
        """
        if self._agent is None:
            self.compile()
            
        # Apply context injection from BaseAgent
        state = self._inject_context(state)
        
        return await self._agent.ainvoke(state)

    def reset(self):
        """Reset the agent's state.
        
        This method resets the agent's state by clearing the checkpointer's checkpoint.
        It allows the agent to be reused for new conversations.
        """
        # 重置checkpointer状态
        if self.checkpointer:
            self.checkpointer= None
            
        # 重置_app，以便下次使用时重新构建
        self._agent = None

    def get_runnable(self) -> RunnableCallable:
        """
        Wrap this agent as a RunnableCallable for LangGraph.
        """
        return RunnableCallable(self.invoke, self.ainvoke)
