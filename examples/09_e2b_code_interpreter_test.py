import os
import sys
import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv

from core.agents.react_agent import ReactAgent
from core.tools.registry import get_registered_tools, ToolCategory, get_tools_by_category
from core.tools.e2b_tool import E2BCodeInterpreterTool

load_dotenv()  # 自动加载 .env 文件

##############################################################################
# E2B代码解释器工具测试
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
            if len(content) > 500:
                content = content[:500] + "... (更多内容省略)"
            print(f"- 结果: {content}")
    
    print("-" * 50)

##############################################################################
# 检查E2B代码解释器工具是否已注册
##############################################################################

print_separator("检查E2B代码解释器工具是否已注册")

# 获取所有已注册的工具（以字典格式）
registered_tools = get_registered_tools(as_dict=True)

# 打印所有已注册的工具
print("\n已注册的工具:")
for name, info in registered_tools.items():
    print(f"- {name} (类别: {info['category'].value})")

# 检查E2B代码解释器工具是否已注册
e2b_tool_name = "e2b_code_interpreter"
if e2b_tool_name in registered_tools:
    print(f"\nE2B代码解释器工具已成功注册: {e2b_tool_name}")
else:
    print(f"\n警告: E2B代码解释器工具未注册")
    # 手动注册E2B代码解释器工具
    print("尝试手动注册E2B代码解释器工具...")
    try:
        from core.tools.registry import register_tool
        e2b_tool = E2BCodeInterpreterTool()
        register_tool(e2b_tool, ToolCategory.CODE_INTERPRETER)
        print(f"已手动注册工具: {e2b_tool.name}")
    except Exception as e:
        print(f"手动注册E2B代码解释器工具失败: {e}")

##############################################################################
# 创建ReactAgent实例
##############################################################################

print_separator("创建ReactAgent实例")

# 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

# 从注册表中只获取代码解释器类工具列表
tools_list = get_tools_by_category(ToolCategory.CODE_INTERPRETER)

# 打印获取到的代码解释器工具
print("\n获取到的代码解释器工具:")
for tool in tools_list:
    print(f"- {tool.name}: {tool.description}")

# 创建ReactAgent实例
react_agent = ReactAgent(
    model=model,
    tools=tools_list,
    name="code_interpreter_agent",
    # 提示词强调使用代码解释器工具进行数据分析和可视化
    prompt=(
        "你是一位专业的数据分析师和编程助手，擅长使用Python进行数据分析和可视化。\n"
        "你有多个强大的代码执行工具可以使用：\n"
        "- e2b_code_interpreter: 用于执行Python代码，支持数据分析和可视化\n"
        "- exec_python: 用于执行Python代码\n"
        "- exec_javascript: 用于执行JavaScript代码\n\n"
        "当面对编程和数据分析问题时，请遵循以下方法论：\n"
        "1. 分析问题：理解用户的需求和问题本质\n"
        "2. 制定计划：确定解决方案和需要使用的工具\n"
        "3. 编写代码：使用适当的工具编写和执行代码\n"
        "4. 分析结果：解释代码执行结果，提供见解\n"
        "5. 优化方案：如有必要，优化代码或提供改进建议\n\n"
        "重要提示：\n"
        "- 优先使用e2b_code_interpreter工具执行Python代码\n"
        "- 对于数据分析和可视化任务，确保导入必要的库（如pandas, matplotlib, numpy等）\n"
        "- 对于不存在的库，工具会自动尝试使用pip install进行安装\n"
        "- 在代码中添加详细注释，解释关键步骤\n"
        "- 执行代码后，解释结果含义和见解\n"
    ),
)

# 编译Agent
agent = react_agent.compile()

# 获取图对象
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

print(f"工作流图已保存为 {graph_path}")

##############################################################################
# 测试：使用E2B代码解释器执行简单的数据分析任务
##############################################################################

if __name__ == "__main__":
    print_separator("开始测试ReactAgent使用E2B代码解释器")
    print("\n查询: 使用Python生成一个简单的正弦波图形")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="使用Python生成一个简单的正弦波图形，如果有找不到的模块，需要自动安装")
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
        
        # 使用log_agent_actions函数记录状态
        log_agent_actions({"messages": [latest_message]})
    
    # 打印最终回答
    print_separator("最终回答")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)
                
                # 将结果保存到文件
                output_dir = os.path.join(os.path.dirname(__file__), "output")
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, "e2b_code_interpreter_result.md")
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("# E2B代码解释器测试结果\n\n")
                    f.write(message.content)
                
                print(f"\n结果已保存到: {output_file}")