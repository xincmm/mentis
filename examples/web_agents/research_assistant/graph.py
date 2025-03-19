from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langgraph.checkpoint.memory import MemorySaver


load_dotenv()  # 自动加载 .env 文件
# 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

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
    checkpointer=MemorySaver(),
)


def get_graph():
    return research_agent