import os
import sys
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import json
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv
from langchain_community.tools import JinaSearch
from core.tools.firecrawl_tool import FireCrawlTool


load_dotenv()  # 自动加载 .env 文件
# 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")



##############################################################################
# 创建一个记录Agent思考过程的函数
##############################################################################

def log_agent_actions(state: Dict[str, Any]) -> None:
    """记录Agent的思考过程和行动"""
    print("\n" + "=" * 50)
    print("当前状态:")
    
    # 打印最新消息
    if state.get("messages") and len(state["messages"]) > 0:
        latest_message = state["messages"][-1]
        
        if isinstance(latest_message, AIMessage):
            print(f"\nAI思考过程:")
            print(latest_message.content)
            
            # 如果有工具调用，打印工具调用信息
            if latest_message.tool_calls:
                print(f"\n工具调用:")
                for tool_call in latest_message.tool_calls:
                    print(f"- 工具: {tool_call['name']}")
                    print(f"- 参数: {tool_call['args']}")
        
        elif isinstance(latest_message, ToolMessage):
            print(f"\n工具返回结果:")
            print(f"- 工具: {latest_message.name}")
            # 只打印结果的前200个字符，避免输出过长
            content = latest_message.content
            if len(content) > 300:
                content = content[:300] + "... (更多内容省略)"
            print(f"- 结果: {content}")
    
    print("=" * 50)

##############################################################################
# 创建Web提取工具 - FireCrawl用于网站结构，Jina用于内容提取
##############################################################################

# 创建FireCrawl工具 - 用于网站结构分析
firecrawl_tool = FireCrawlTool(
    mode="crawl",  # 使用爬取模式
    params={"max_pages": 10}  # 限制爬取页面数量
)

# 创建Jina Reader工具 - 用于内容提取
jina_reader_tool = JinaSearch()

##############################################################################
# 创建REACT Agent - 使用更详细的提示词引导多步思考
##############################################################################

react_agent = create_react_agent(
    model=model,
    tools=[firecrawl_tool, jina_reader_tool],
    name="web_extraction_expert",
    # 提示词强调分解问题、多步思考和综合信息
    prompt=(
        "你是一位专业的网页内容分析专家，擅长提取和分析网站结构与内容。\n"
        "你有两个强大的工具:\n"
        "1. 'firecrawl_tool': 用于爬取网站结构和下级页面\n"
        "2. 'jina_reader_tool': 用于从特定URL提取结构化内容，获取干净可读的内容\n\n"
        "当面对网站分析任务时，请遵循以下方法论:\n"
        "1. 分析任务: 明确需要从网站获取什么信息\n"
        "2. 网站结构分析: 使用firecrawl_tool爬取网站结构，了解可用页面\n"
        "3. 内容提取: 根据网站结构，使用jina_reader_tool从关键页面提取内容\n"
        "4. 信息整合: 将提取的内容整合成有条理的分析结果\n\n"
        "重要提示:\n"
        "- 先使用firecrawl_tool了解网站结构，再使用jina_reader_tool提取具体内容\n"
        "- 对于大型网站，先分析网站结构，再有针对性地选择重要页面进行内容提取\n"
        "- 每次工具使用后评估结果，决定下一步行动\n"
        "- 在最终回答中提供结构化的分析，包括网站组织方式和关键内容摘要\n"
        "- 清晰地展示你的思考过程，包括为什么选择特定页面进行分析\n"
    ),
)

##############################################################################
# 测试：分析LangGraph文档网站
##############################################################################

if __name__ == "__main__":
    # 测试网站分析
    print("\n开始测试Web提取Agent分析网站的能力...\n")
    print("分析目标: LangGraph文档网站")
    
    # 定义输入
    inputs = {
        "messages": [
            {"role": "user", "content": "爬取LangGraph文档网站的每个章节的内容(https://langchain-ai.github.io/langgraph/how-tos/) "}
        ]
    }
    
    # 使用stream方法逐步获取中间状态
    final_state = None
    for partial_state in react_agent.stream(inputs, stream_mode="values"):
        # 保存最终状态
        final_state = partial_state
        
        # 获取消息列表
        messages = partial_state.get("messages", [])
        if not messages:
            continue
            
        # 获取最新消息
        latest_message = messages[-1]
        
        # 使用原有的log_agent_actions函数记录状态
        log_agent_actions({"messages": [latest_message]})
    
    # 打印最终回答
    print("\n最终分析结果:")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                message.pretty_print()