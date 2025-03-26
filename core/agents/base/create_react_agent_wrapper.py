from typing import Optional, Callable
from langgraph.utils.runnable import RunnableCallable
from langchain_core.runnables.config import RunnableConfig

class CreateReactAgentWrapper(RunnableCallable):
    def __init__(self, agent, name: str = "agent", 
                 before_invoke: Optional[Callable[[dict], None]] = None,
                 after_invoke: Optional[Callable[[dict, dict], None]] = None):
       
        self._agent = agent
        self.name = name or getattr(agent, "name", "agent")
        self.before_invoke = before_invoke
        self.after_invoke = after_invoke

        agent_name = self.name

        def call(state: dict, config: Optional[RunnableConfig] = None, **kwargs) -> dict:
            print(f"🟢 [Sync] Invoking agent: {agent_name}")
            if self.before_invoke:
                self.before_invoke(state)
            output = self._agent.invoke(state, config, **kwargs)
            if self.after_invoke:
                self.after_invoke(state, output)
            print(f"✅ [Sync] Agent '{agent_name}' finished")
            return output

        async def acall(state: dict, config: Optional[RunnableConfig] = None, **kwargs) -> dict:
            print(f"🟢 [Async] Invoking agent: {agent_name}")
            if self.before_invoke:
                self.before_invoke(state)
            output = await self._agent.ainvoke(state, config, **kwargs)
            if self.after_invoke:
                self.after_invoke(state, output)
            print(f"✅ [Async] Agent '{agent_name}' finished")
            return output

        super().__init__(call, acall)