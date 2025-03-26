import os
import sys
import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_community.tools import JinaSearch, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from dotenv import load_dotenv

from core.agents.base.react_agent import ReactAgent
from core.tools import register_direct_tool
from core.tools.registry import get_registered_tools, ToolCategory
from core.tools.firecrawl_tool import FireCrawlTool

load_dotenv()  # 自动加载 .env 文件

##############################################################################
# 工具注册和ReactAgent测试 - 美联储研究任务
##############################################################################

def print_separator(title):
    """打印分隔符"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

##############################################################################
# 创建一个记录Agent思考过程的函数
##############################################################################

def log_agent_actions(state: Dict[str, Any]) -> None:
    """记录Agent的思考过程和行动"""
    print("\n" + "-" * 50)
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
            if len(content) > 200:
                content = content[:200] + "... (更多内容省略)"
            print(f"- 结果: {content}")
    
    print("-" * 50)

##############################################################################
# 注册工具
##############################################################################

print_separator("注册搜索工具")

# 创建JinaSearch工具实例
jina_search = JinaSearch()

# 创建Wikipedia工具实例
# wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

firecrawl_tool = FireCrawlTool()

# 使用register_direct_tool函数注册工具
register_direct_tool(jina_search)
register_direct_tool(firecrawl_tool)
# 注册自定义工具 - FireCrawlTool

# 获取所有已注册的工具（以字典格式）
registered_tools = get_registered_tools(as_dict=True)

# 打印所有已注册的工具
print("\n已注册的工具:")
for name, info in registered_tools.items():
    print(f"- {name} (类别: {info['category'].value})")

##############################################################################
# 创建ReactAgent实例
##############################################################################

print_separator("创建ReactAgent实例")

# 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

# 从注册表中只获取搜索类工具列表
from core.tools.registry import get_tools_by_category, ToolCategory
tools_list = get_tools_by_category(ToolCategory.SEARCH)

# 创建ReactAgent实例
react_agent = ReactAgent(
    model=model,
    tools=tools_list,
    name="fed_research_agent",
    # 提示词强调分解问题、多步思考和综合信息
    prompt=(
        "你是一位专业的经济研究分析师，擅长分析复杂的经济问题并提供深入见解。\n"
        "你有多个强大的工具可以搜索网络获取实时信息：\n"
        "当面对复杂问题时，请遵循以下方法论：\n"
        "1. 分解问题：将复杂问题分解为更小的子问题\n"
        "2. 制定计划：确定需要搜索哪些信息，以及使用哪些工具\n"
        "3. 执行搜索：使用适当的工具执行搜索\n"
        "4. 分析结果：分析搜索结果，确定是否需要进一步搜索\n"
        "5. 综合信息：将所有搜索结果综合成一个连贯的回答\n\n"
        "重要提示：\n"
        "- 每次搜索后评估结果，决定下一步行动\n"
        "- 在最终回答中引用来源\n"
        "- 清晰地展示你的思考过程，包括问题分解和计划制定\n"
    ),
)

# agent = react_agent.compile()
# 获取图对象
# graph = agent.get_graph()

# # 获取当前文件名（不含路径和扩展名）
# current_file = os.path.basename(__file__)
# file_name_without_ext = os.path.splitext(current_file)[0]
# graph_dir = os.path.join(os.path.dirname(__file__), "graphs")

# # 确保 graphs 目录存在
# os.makedirs(graph_dir, exist_ok=True)

# # 生成与文件名一致的图片名，并保存到 examples/graphs 目录
# image_data = graph.draw_mermaid_png()
# graph_path = os.path.join(graph_dir, f"{file_name_without_ext}.png")

# # 保存图片（如果已存在则覆盖）
# with open(graph_path, "wb") as f:
#     f.write(image_data)

# print(f"工作流图已保存为 {graph_path}")

##############################################################################
# 测试：查询"美联储的详细介绍和它如何影响全球经济"
##############################################################################

if __name__ == "__main__":
    print_separator("开始测试ReactAgent处理美联储研究任务")
    print("\n查询: 美联储的详细介绍和它如何影响全球经济")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请提供2025年美联储(Federal Reserve)的详细介绍，包括其历史、结构、职能，以及它如何通过货币政策影响全球经济。")
        ]
    }
    result = react_agent.run(inputs)
##############################################################################
# 打印最终对话消息
##############################################################################
    for m in result["messages"]:
        m.pretty_print()