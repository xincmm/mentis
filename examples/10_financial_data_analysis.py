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
# 财务数据分析报表生成示例
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
            content = latest_message.content
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
    name="financial_data_analyst",
    # 提示词强调使用代码解释器工具进行财务数据分析和可视化
    prompt=(
        "你是一位专业的财务数据分析师，擅长使用Python进行财务数据分析和可视化。\n"
        "你有强大的代码执行工具可以使用：\n"
        "- e2b_code_interpreter: 用于执行Python代码，支持数据分析和可视化\n\n"
        "当面对财务数据分析问题时，请遵循以下方法论：\n"
        "1. 分析问题：理解用户的需求和问题本质\n"
        "2. 制定计划：确定解决方案和需要使用的工具\n"
        "3. 编写代码：使用适当的工具编写和执行代码\n"
        "4. 分析结果：解释代码执行结果，提供财务见解\n"
        "5. 优化方案：如有必要，优化代码或提供改进建议\n\n"
        "重要提示：\n"
        "- 优先使用e2b_code_interpreter工具执行Python代码\n"
        "- 对于财务数据分析和可视化任务，确保导入必要的库（如pandas, matplotlib, numpy等）\n"
        "- 对于不存在的库，工具会自动尝试使用pip install进行安装\n"
        "- 在代码中添加详细注释，解释关键步骤\n"
        "- 执行代码后，解释结果含义和财务见解\n"
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
# 从沙箱下载文件到本地的函数
##############################################################################
import os

def download_file_from_sandbox(sandbox, sandbox_path, local_path):
    """从 e2b 沙箱中下载文件并保存到本地，自动区分文本和二进制文件"""
    try:
        print(f"读取文件: {sandbox_path}")

        # 判断是否为常见二进制文件类型（可自行扩展）
        binary_extensions = (
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.svg',
            '.xlsx', '.xls', '.zip', '.bin', '.pyc', '.pyd',
            '.pptx', '.docx', '.mp3', '.mp4', '.avi', '.mov',
        )
        is_binary = sandbox_path.lower().endswith(binary_extensions)

        # 创建目录
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if is_binary:
            print("📦 识别为二进制文件，使用 sandbox.download_file()")
            content = sandbox.files.read(sandbox_path)  # 返回 bytes
            with open(local_path, 'wb') as f:
                f.write(content)
        else:
            print("📄 识别为文本文件，使用 sandbox.files.read()")
            content = sandbox.files.read(sandbox_path)  # 返回 str
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(content)

        print(f"✅ 文件已保存到本地: {local_path}")
        return True

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False
    
def download_directory_from_sandbox(sandbox, sandbox_dir_path, local_dir_path):
    """从沙箱下载整个目录内容到本地
    
    Args:
        sandbox: 沙箱实例
        sandbox_dir_path: 沙箱中的目录路径
        local_dir_path: 本地保存目录路径
    
    Returns:
        bool: 是否成功下载所有文件
    """
    try:
        print(f"尝试下载目录: {sandbox_dir_path} -> {local_dir_path}")
        
        # 确保本地目录存在
        os.makedirs(local_dir_path, exist_ok=True)
        
        # 列出沙箱中指定目录下的所有文件
        try:
            files = sandbox.files.list(sandbox_dir_path)
            # print(f"获取到文件列表: {sandbox_dir_path}, 类型: {type(files)}")
            # if files and len(files) > 0:
            #     print(f"第一个文件类型: {type(files[0])}, 内容: {files[0]}")
            #     # 检查对象属性
            #     print(f"文件对象可用属性: {dir(files[0])}")
        except Exception as e:
            print(f"列出文件时出错: {sandbox_dir_path}, 错误: {str(e)}")
            return False
        
        if not files:
            print(f"沙箱中目录 {sandbox_dir_path} 为空或不存在")
            return False
            
        downloaded_count = 0
        # 定义需要跳过的系统文件
        skip_files = {'.bashrc', '.bash_logout', '.profile'}
        
        # 遍历并下载每个文件
        for file_info in files:
            try:
                # 使用dir()查看对象有哪些属性
                print(f"文件信息对象属性: {dir(file_info)}")
                
                # 尝试安全获取name和type属性
                file_name = getattr(file_info, "name", None)
                if file_name is None:
                    print(f"警告: 无法获取文件名, 跳过此文件")
                    continue
                    
                file_type = getattr(file_info, "type", "file")  # 默认为文件类型
                # 如果 file_type 是枚举, 使用其 value 进行判断
                type_value = file_type.value if hasattr(file_type, "value") else file_type
                
                # 跳过不需要的系统文件或系统目录（隐藏文件/目录）
                if file_name in skip_files or (file_name.startswith('.') and type_value == 'dir'):
                    print(f"跳过系统文件或目录: {file_name}")
                    continue
                
                print(f"处理文件: {file_name}, 类型: {type_value}")
                
                sandbox_file_path = f"{sandbox_dir_path}/{file_name}"
                local_file_path = os.path.join(local_dir_path, file_name)
                
                if type_value == 'dir':
                    # 递归下载子目录
                    print(f"发现子目录: {sandbox_file_path}")
                    if download_directory_from_sandbox(sandbox, sandbox_file_path, local_file_path):
                        downloaded_count += 1
                else:
                    # 下载文件
                    print(f"下载文件: {sandbox_file_path} -> {local_file_path}")
                    if download_file_from_sandbox(sandbox, sandbox_file_path, local_file_path):
                        downloaded_count += 1
            except Exception as e:
                print(f"处理文件时出错: {str(e)}")
                import traceback
                print(f"详细错误跟踪: {traceback.format_exc()}")
                continue
        
        if downloaded_count > 0:
            print(f"从 {sandbox_dir_path} 下载了 {downloaded_count} 个文件/目录到 {local_dir_path}")
            return True
        return False
        
    except Exception as e:
        print(f"从沙箱下载目录时出错: {str(e)}")
        import traceback
        print(f"详细错误跟踪: {traceback.format_exc()}")
        return False

##############################################################################
# 测试：使用E2B代码解释器生成财务数据分析报表
##############################################################################

if __name__ == "__main__":
    print_separator("开始测试ReactAgent使用E2B代码解释器进行财务数据分析")
    print("\n查询: 生成模拟财务数据并进行分析，生成财务报表")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请生成一组模拟的公司财务数据（包括收入、支出、利润等），对数据进行分析，将处理过程（代码）和最终生成的结果保存到本地。")
        ]
    }
    result = agent.invoke(inputs)

    for m in result["messages"]:
        m.pretty_print()

    print("\n下载沙盒里的文件")
    try:
        # 遍历 react_agent.tools 以查找 E2B 相关工具
        sandbox = None
        for tool in react_agent.tools:
            if hasattr(tool, "sandbox"):
                sandbox = tool.sandbox
                break  # 找到后就退出循环

        if sandbox:
            # 设定输出目录
            output_dir = os.path.join(os.getcwd(), "examples/output/sandbox_files")
            os.makedirs(output_dir, exist_ok=True)

            # 直接下载主要工作目录
            print("\n从沙箱下载文件到本地...")
            download_directory_from_sandbox(sandbox, "/home/user", output_dir)

            # 下载临时目录中可能的图表和数据文件
            # download_directory_from_sandbox(sandbox, "/tmp", output_dir)

            print(f"\n文件已保存到目录: {output_dir}")
            sandbox.close()
    except Exception as e:
        print(f"从沙箱下载文件时出错: {str(e)}")