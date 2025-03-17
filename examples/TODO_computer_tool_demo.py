from typing import Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.runnables.graph import StateGraph, END, START
from langchain.tools.render import render_text_description
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain.agents.format_scratchpad import format_to_openai_tool_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import Command, InjectedState

# Import our custom computer tool
# TODO: MarinaBox - Import our custom computer tool
from marinabox import mb_start_computer, mb_stop_computer, mb_use_computer_tool

# Set up model with tools
model = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
tools = [mt_use_computer_tool()]
model_with_tools = model.bind_tools(tools)

# Define workflow nodes
def should_continue(state: Annotated[dict, InjectedState()]):
    messages = state["messages"]
    if len(messages) > 0:
        last_message = messages[-1]
        if last_message.tool_calls:
            return Command(goto="tool_node")
    else:
        return Command(goto="stop_computer")
    return Command(goto="stop_computer")

def call_model(state: Annotated[dict, InjectedState()]):
    input_message = input("Enter your message: ")
    if input_message != "stop_computer":
        messages = [HumanMessage(content=input_message)]
        response = model_with_tools.invoke(messages)
        return {"messages": [response], "session_id": state.get("session_id")}
    else:
        return {"messages": [], "session_id": state.get("session_id")}

# Set up workflow
workflow = StateGraph(dict)
workflow.add_node("start_computer", mt_start_computer)
workflow.add_node("agent", call_model)
workflow.add_node("tool_node", ToolNode(tools=tools))
workflow.add_node("stop_computer", mt_stop_computer)
workflow.add_node("should_continue", should_continue)

# Define workflow edges
workflow.add_edge(START, "start_computer")
workflow.add_edge("start_computer", "agent")
workflow.add_edge("tool_node", "agent")
workflow.add_edge("agent", "should_continue")
workflow.add_edge("stop_computer", END)

# Compile and run workflow
app = workflow.compile()
if __name__ == "__main__":
    app.invoke({"messages": ""})
