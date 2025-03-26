import logging
from typing import Optional, Callable, Dict
from langgraph.utils.runnable import RunnableCallable
from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)

class CreateReactAgentWrapper(RunnableCallable):
    def __init__(
        self, 
        agent, 
        name: str = "agent", 
        before_invoke: Optional[Callable[[dict], dict]] = None,
        before_ainvoke: Optional[Callable[[dict], dict]] = None,
        after_invoke: Optional[Callable[[dict, dict], None]] = None,
        after_ainvoke: Optional[Callable[[dict, dict], None]] = None
    ):
        """
        :param agent: The underlying compiled graph or runnable
        :param name: Unique name for this wrapper (avoid duplicates)
        :param before_invoke: A sync callback that modifies the state before the wrapped agent call
        :param before_ainvoke: An async callback that modifies the state before the wrapped agent call
        :param after_invoke: A sync callback that inspects (state, output) after the wrapped call
        :param after_ainvoke: An async callback that inspects (state, output) after the wrapped call
        """
        self._agent = agent
        self.name = name or getattr(agent, "name", "agent")
        self.before_invoke = before_invoke
        self.after_invoke = after_invoke
        self.before_ainvoke = before_ainvoke
        self.after_ainvoke = after_ainvoke

        # We define the sync/async "call" functions for RunnableCallable
        def call(state: Dict, config: Optional[RunnableConfig] = None, **kwargs) -> Dict:
            logger.info(f"[{self.name}] (sync) call() - started. State keys: {list(state.keys())}")
            # Or use print if you prefer
            # print(f"🟢 [Sync] Invoking wrapper: {self.name}, state keys: {list(state.keys())}")

            # before_invoke callback
            if self.before_invoke:
                state = self.before_invoke(state)

            # Call the underlying agent
            output = self._agent.invoke(state, config, **kwargs)

            # after_invoke callback
            if self.after_invoke:
                self.after_invoke(state, output)

            logger.info(f"[{self.name}] (sync) call() - finished. Output keys: {list(output.keys())}")
            return output

        async def acall(state: Dict, config: Optional[RunnableConfig] = None, **kwargs) -> Dict:
            logger.info(f"[{self.name}] (async) acall() - started. State keys: {list(state.keys())}")
            # print(f"🟢 [Async] Invoking wrapper: {self.name}, state keys: {list(state.keys())}")

            if self.before_ainvoke:
                state = await self.before_ainvoke(state)

            output = await self._agent.ainvoke(state, config, **kwargs)

            if self.after_ainvoke:
                await self.after_ainvoke(state, output)

            logger.info(f"[{self.name}] (async) acall() - finished. Output keys: {list(output.keys())}")
            return output

        # Pass these to RunnableCallable
        super().__init__(call, acall, name=self.name)