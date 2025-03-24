import os
import json
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools import TavilySearchResults
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv
from core.utils.agent_utils import log_agent_actions, save_agent_graph
load_dotenv()  # 自动加载 .env 文件
# 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

##############################################################################
# 创建Tavily搜索工具 - 配置为深度搜索模式
##############################################################################

tavily_search = TavilySearchResults(
    max_results=3,
    include_answer=True,
    include_raw_content=True,  # 包含原始内容，便于分析
    include_images=False,
    search_depth="advanced"  # 使用高级搜索深度
)

##############################################################################
# 创建REACT Agent - 使用更详细的提示词引导多步思考
##############################################################################

react_agent = create_react_agent(
    model=model,
    tools=[tavily_search],
    name="tesla_research_expert",
    # 提示词强调分解问题、多步思考和综合信息
    prompt=(
        "你是一位专业的研究分析师，擅长分析复杂问题并提供深入见解。\n"
        "你有一个强大的工具'tavily_search_results_json'可以搜索网络获取实时信息。\n\n"
        "当面对复杂问题时，请遵循以下REACT方法论：\n"
        "1. 分解问题：将复杂问题分解为更小的子问题\n"
        "2. 制定计划：确定需要搜索哪些信息，以及搜索的顺序\n"
        "3. 执行搜索：使用tavily_search_results_json工具执行搜索\n"
        "4. 分析结果：分析搜索结果，确定是否需要进一步搜索\n"
        "5. 综合信息：将所有搜索结果综合成一个连贯的回答\n\n"
        "重要提示：\n"
        "- 不要一次性搜索过于宽泛的问题\n"
        "- 对于复杂问题，进行多次有针对性的搜索\n"
        "- 每次搜索后评估结果，决定下一步行动\n"
        "- 在最终回答中引用来源，包括搜索结果中的URL\n"
        "- 清晰地展示你的思考过程，包括问题分解和计划制定\n"
    ),
)

# 保存Agent图表
# save_agent_graph(react_agent)

##############################################################################
# 测试：查询"特斯拉2025年的发展预期"
##############################################################################

if __name__ == "__main__":
    # 复杂查询测试
    print("\n开始测试REACT Agent处理复杂查询的能力...\n")
    print("查询: 特斯拉2025年的发展预期")
    
    # 定义输入
    inputs = {
        "messages": [
            {"role": "user", "content": "分析特斯拉2025年的发展预期，包括新车型计划、销量目标、技术创新和市场扩张战略。"}
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
    print("\n最终回答:")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                message.pretty_print()