from langgraph.prebuilt import create_react_agent
from core.agents.supervisor_agent import SupervisorAgent
from langchain_openai import ChatOpenAI
from langgraph.func import entrypoint, task
from langgraph.graph import add_messages
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
load_dotenv()  # 自动加载 .env 文件

# 1. 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

##############################################################################
# Agent 1: Joke Generator (Functional API)
##############################################################################

@task
def generate_joke(messages):
    """Generate a short joke (no tool calls)."""
    system_message = {
        "role": "system", 
        "content": "You are a witty comedian. Write a short joke."
    }
    # 直接调用 model.invoke，拼接 system_message + 用户消息
    msg = model.invoke([system_message] + messages)
    return msg

@entrypoint()
def joke_agent(state):
    # 调用上面的函数型任务
    joke = generate_joke(state['messages']).result()
    # 将产物插入消息列表
    messages = add_messages(state["messages"], [joke])
    return {"messages": messages}

joke_agent.name = "joke_agent"

##############################################################################
# Agent 2: Research Expert with Tavily Search (Graph API)
##############################################################################

# 创建Tavily搜索工具
tavily_search = TavilySearchResults(
    max_results=3,
    include_answer=True,
    include_raw_content=False,
    include_images=False,
    search_depth="advanced"
)

research_agent = create_react_agent(
    model=model,
    tools=[tavily_search],
    name="research_expert",
    # Prompt 告诉它是一个研究型 Agent，可调用 tavily_search
    prompt=(
        "You are a world-class researcher. You have access to the 'tavily_search_results_json' tool "
        "which can search the web for real-time information. "
        "When asked a question, use this tool to find accurate and up-to-date information. "
        "Summarize the search results in a clear and concise manner. "
        "Always cite your sources by including the URLs from the search results."
    ),
)

##############################################################################
# 使用带有Planning功能的SupervisorAgent
##############################################################################

# 创建 SupervisorAgent 实例，启用Planning功能
supervisor = SupervisorAgent(
    agents=[research_agent, joke_agent],
    model=model,
    enable_planning=True,  # 启用Planning功能
)

# 编译得到一个可调用的"App"
app = supervisor.compile()

# 获取当前文件名（不含路径和扩展名）
import os
current_file = os.path.basename(__file__)
file_name_without_ext = os.path.splitext(current_file)[0]
graph_dir = os.path.join(os.path.dirname(__file__), "graphs")

# 确保 graphs 目录存在
os.makedirs(graph_dir, exist_ok=True)

# 生成与文件名一致的图片名，并保存到 examples/graphs 目录
image_data = app.get_graph().draw_mermaid_png()
graph_path = os.path.join(graph_dir, f"{file_name_without_ext}.png")

# 保存图片（如果已存在则覆盖）
with open(graph_path, "wb") as f:
    f.write(image_data)

print(f"Image saved as {graph_path}")

##############################################################################
# 测试：复杂请求需要规划和多个步骤
##############################################################################
result = app.invoke({
    "messages": [
        {
            "role": "user",
            "content": (
                "I'm preparing a presentation about tech companies. I need three things: "
                "1) A joke about tech companies to start with, "
                "2) The employee count for FANNG, and "
                "3) A comparison of which company has more employees."
            )
        }
    ]
})

##############################################################################
# 打印最终对话消息
##############################################################################
for m in result["messages"]:
    m.pretty_print()