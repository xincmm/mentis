import asyncio
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core.agents.react_agent import ReactAgent
from core.tools.tavily_tools import TavilySearchResults

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
            if len(content) > 200:
                content = content[:200] + "... (更多内容省略)"
            print(f"- 结果: {content}")
    
    print("=" * 50)

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
# 创建ReactAgent实例
##############################################################################

def create_react_agent_instance():
    """创建并返回ReactAgent实例"""
    react_agent = ReactAgent(
        model=model,
        tools=[tavily_search],
        name="research_assistant",
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
    
    # 获取图对象并保存
    agent = react_agent.compile()
    graph = agent.get_graph()
    
    # 获取当前文件名（不含路径和扩展名）
    current_file = os.path.basename(__file__)
    file_name_without_ext = os.path.splitext(current_file)[0]
    graph_dir = os.path.join(os.path.dirname(__file__), "graphs")
    
    # 确保 graphs 目录存在
    os.makedirs(graph_dir, exist_ok=True)
    
    # 生成与文件名一致的图片名，并保存到 examples/graphs 目录
    image_data = graph.draw_mermaid_png()
    graph_path = os.path.join(graph_dir, f"{file_name_without_ext}.png")
    
    # 保存图片（如果已存在则覆盖）
    with open(graph_path, "wb") as f:
        f.write(image_data)
    
    print(f"图表已保存为 {graph_path}")
    
    return agent

##############################################################################
# 主函数 - 处理用户输入
##############################################################################

async def main():
    # 创建ReactAgent实例
    react_agent = create_react_agent_instance()
    
    while True:
        # 获取用户输入
        user_input = await asyncio.to_thread(input, "\n请输入您想了解的问题 (输入'退出'结束): ")
        
        # 检查是否退出
        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("\n感谢使用，再见！")
            break
        
        # 准备初始状态
        initial_state = {
            "messages": [HumanMessage(content=user_input)]
        }
        
        try:
            print("\n=== 🔍 开始研究 ===\n")
            
            # 使用stream方法逐步获取中间状态
            final_state = None
            for partial_state in react_agent.stream(initial_state, stream_mode="values"):
                # 保存最终状态
                final_state = partial_state
                
                # 获取消息列表
                messages = partial_state.get("messages", [])
                if not messages:
                    continue
                    
                # 获取最新消息
                latest_message = messages[-1]
                
                # 使用log_agent_actions函数记录状态
                log_agent_actions({"messages": [latest_message]})
            
            # 打印最终回答
            print("\n最终回答:")
            if final_state and final_state.get("messages"):
                for message in final_state["messages"]:
                    if isinstance(message, AIMessage) and not message.tool_calls:
                        print("\n" + "=" * 80)
                        print(message.content)
                        print("=" * 80 + "\n")
        
        except Exception as e:
            print(f"\n处理查询时出错: {e}")

##############################################################################
# 程序入口
##############################################################################

if __name__ == "__main__":
    print("\n欢迎使用ReactAgent研究助手！")
    print("这个助手可以帮助您研究各种问题，使用Tavily搜索工具获取最新信息。")
    print("您可以输入任何问题，助手将使用REACT方法论进行分析和回答。")
    
    # 运行主函数
    asyncio.run(main())