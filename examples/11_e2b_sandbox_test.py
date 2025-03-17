import os
import sys
import json
from typing import Dict, Any, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv

from core.agents.react_agent import ReactAgent
from core.tools.registry import get_registered_tools, ToolCategory, get_tools_by_category
from core.tools.e2b_tool import E2BCodeInterpreterTool

load_dotenv()  # 自动加载 .env 文件

##############################################################################
# E2B沙盒环境测试程序
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
            if len(content) > 500:
                content = content[:250] + "\n... (内容过长，已截断) ...\n" + content[-250:]
            print(f"- 结果: {content}")
    
    print("-" * 50)

##############################################################################
# 从沙箱下载文件到本地的函数
##############################################################################

def download_file_from_sandbox(sandbox, sandbox_path, local_path):
    """从沙箱下载文件到本地
    
    Args:
        sandbox: 沙箱实例
        sandbox_path: 沙箱中的文件路径
        local_path: 本地保存路径
    """
    try:
        # 从沙箱读取文件内容
        content = sandbox.files.read(sandbox_path)
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 写入本地文件
        with open(local_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        print(f"文件已从沙箱下载到本地: {local_path}")
        return True
    except Exception as e:
        print(f"从沙箱下载文件时出错: {str(e)}")
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
        # 确保本地目录存在
        os.makedirs(local_dir_path, exist_ok=True)
        
        # 列出沙箱中指定目录下的所有文件
        files = sandbox.filesystem.list(sandbox_dir_path)
        
        if not files:
            print(f"沙箱中目录 {sandbox_dir_path} 为空或不存在")
            return False
            
        downloaded_count = 0
        
        # 遍历并下载每个文件
        for file_info in files:
            sandbox_file_path = f"{sandbox_dir_path}/{file_info['name']}"
            local_file_path = os.path.join(local_dir_path, file_info['name'])
            
            if file_info['type'] == 'directory':
                # 递归下载子目录
                success = download_directory_from_sandbox(sandbox, sandbox_file_path, local_file_path)
                if success:
                    downloaded_count += 1
            else:
                # 下载文件
                try:
                    content = sandbox.files.read(sandbox_file_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                    
                    # 处理二进制文件（如图像）
                    if any(sandbox_file_path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf']):
                        with open(local_file_path, 'wb') as file:
                            file.write(content.encode() if isinstance(content, str) else content)
                    else:
                        with open(local_file_path, 'w', encoding='utf-8') as file:
                            file.write(content)
                            
                    print(f"文件已从沙箱下载到本地: {local_file_path}")
                    downloaded_count += 1
                except Exception as e:
                    print(f"下载文件 {sandbox_file_path} 时出错: {str(e)}")
        
        print(f"共下载了 {downloaded_count} 个文件/目录从 {sandbox_dir_path} 到 {local_dir_path}")
        return downloaded_count > 0
        
    except Exception as e:
        print(f"从沙箱下载目录时出错: {str(e)}")
        return False

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
    name="sandbox_test_agent",
    # 提示词强调测试沙箱环境的各种功能
    prompt=(
        "你是一位专业的沙箱环境测试专家，负责测试E2B代码解释器沙箱环境的各种功能。\n"
        "你有强大的代码执行工具可以使用：\n"
        "- e2b_code_interpreter: 用于在沙箱环境中执行Python代码\n\n"
        "当进行沙箱环境测试时，请遵循以下方法论：\n"
        "1. 分析测试需求：理解需要测试的沙箱功能\n"
        "2. 设计测试用例：针对特定功能设计测试代码\n"
        "3. 执行测试：使用e2b_code_interpreter工具执行测试代码\n"
        "4. 分析结果：解释测试结果，判断功能是否正常\n"
        "5. 记录问题：如有异常，记录问题并提供详细信息\n\n"
        "重要提示：\n"
        "- 优先使用e2b_code_interpreter工具执行Python代码\n"
        "- 测试代码应包含详细注释，解释测试目的和预期结果\n"
        "- 测试应覆盖沙箱的各种功能，包括但不限于：\n"
        "  * 基本Python代码执行\n"
        "  * 文件系统操作（创建、读取、写入文件）\n"
        "  * 包管理（安装和使用第三方包）\n"
        "  * 系统命令执行（使用!前缀执行shell命令）\n"
        "  * 数据处理和可视化\n"
        "  * 异常处理和错误恢复\n"
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
# 测试用例1：基本Python代码执行和环境信息
##############################################################################

def run_test_case_1():
    print_separator("测试用例1：基本Python代码执行和环境信息")
    print("\n查询: 测试基本Python代码执行和获取环境信息")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请执行一段Python代码，测试基本的数学运算、字符串操作，并获取沙箱环境的系统信息（Python版本、操作系统信息等）。")
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
    print_separator("测试用例1结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)

##############################################################################
# 测试用例2：文件系统操作
##############################################################################

def run_test_case_2():
    print_separator("测试用例2：文件系统操作")
    print("\n查询: 测试沙箱环境的文件系统操作")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请测试沙箱环境的文件系统操作，包括创建目录、创建文件、写入内容、读取内容、列出目录内容等。创建一个测试目录结构，并将操作结果保存到文件中。")
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
    print_separator("测试用例2结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)
                
                # 检查是否有E2B沙箱实例，尝试下载生成的文件
                for msg in final_state["messages"]:
                    if isinstance(msg, ToolMessage) and msg.name == "e2b_code_interpreter":
                        try:
                            # 尝试解析工具消息内容
                            tool_output = json.loads(msg.content)
                            
                            # 检查是否有原始输出
                            if hasattr(msg, 'raw_output') and msg.raw_output:
                                # 获取沙箱实例
                                if 'sandbox' in dir(react_agent.tools[0]):
                                    sandbox = react_agent.tools[0].sandbox
                                    
                                    # 从沙箱下载生成的文件
                                    output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                    os.makedirs(output_dir, exist_ok=True)
                                    
                                    # 尝试下载测试目录
                                    sandbox_test_path = "/home/user/test_dir"
                                    download_directory_from_sandbox(sandbox, sandbox_test_path, os.path.join(output_dir, "test_dir"))
                        except Exception as e:
                            print(f"处理工具消息时出错: {str(e)}")

##############################################################################
# 测试用例3：包管理和第三方库使用
##############################################################################

def run_test_case_3():
    print_separator("测试用例3：包管理和第三方库使用")
    print("\n查询: 测试沙箱环境的包管理和第三方库使用")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请测试沙箱环境的包管理功能，安装一个不常见的第三方库（如wordcloud、pycountry等），并使用该库编写一个简单的示例程序。验证包安装和使用是否正常。")
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
    print_separator("测试用例3结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)

##############################################################################
# 测试用例4：Shell命令执行
##############################################################################

def run_test_case_4():
    print_separator("测试用例4：Shell命令执行")
    print("\n查询: 测试沙箱环境的Shell命令执行")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请测试沙箱环境中执行Shell命令的功能，使用!前缀执行一系列Linux命令，包括系统信息查询、目录操作、文件查找等。将命令执行结果保存到文件中。")
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
    print_separator("测试用例4结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)
                
                # 尝试下载生成的文件
                for msg in final_state["messages"]:
                    if isinstance(msg, ToolMessage) and msg.name == "e2b_code_interpreter":
                        try:
                            if 'sandbox' in dir(react_agent.tools[0]):
                                sandbox = react_agent.tools[0].sandbox
                                output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                os.makedirs(output_dir, exist_ok=True)
                                
                                # 尝试下载shell命令结果文件
                                sandbox_file_path = "/home/user/shell_commands_results.txt"
                                local_file_path = os.path.join(output_dir, "shell_commands_results.txt")
                                download_file_from_sandbox(sandbox, sandbox_file_path, local_file_path)
                        except Exception as e:
                            print(f"下载文件时出错: {str(e)}")

##############################################################################
# 测试用例5：数据处理和可视化
##############################################################################

def run_test_case_5():
    print_separator("测试用例5：数据处理和可视化")
    print("\n查询: 测试沙箱环境的数据处理和可视化功能")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请测试沙箱环境的数据处理和可视化功能，生成一些随机数据，使用pandas进行数据处理，然后使用matplotlib创建多种类型的图表（折线图、柱状图、散点图等）。将生成的图表保存为图片文件。")
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
    print_separator("测试用例5结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)
                
                # 尝试下载生成的图表文件
                for msg in final_state["messages"]:
                    if isinstance(msg, ToolMessage) and msg.name == "e2b_code_interpreter":
                        try:
                            if 'sandbox' in dir(react_agent.tools[0]):
                                sandbox = react_agent.tools[0].sandbox
                                output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                os.makedirs(output_dir, exist_ok=True)
                                
                                # 尝试下载图表文件
                                download_directory_from_sandbox(sandbox, "/home/user", output_dir)
                        except Exception as e:
                            print(f"下载文件时出错: {str(e)}")

##############################################################################
# 测试用例6：异常处理和错误恢复
##############################################################################

def run_test_case_6():
    print_separator("测试用例6：异常处理和错误恢复")
    print("\n查询: 测试沙箱环境的异常处理和错误恢复能力")
    
    # 定义输入
    inputs = {
        "messages": [
            HumanMessage(content="请测试沙箱环境的异常处理和错误恢复能力。编写一段包含各种常见错误的Python代码（如语法错误、除零错误、文件不存在错误等），然后展示如何捕获和处理这些异常。验证沙箱环境是否能正确报告错误并继续执行后续代码。")
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
    print_separator("测试用例6结果")
    if final_state and final_state.get("messages"):
        for message in final_state["messages"]:
            if isinstance(message, AIMessage) and not message.tool_calls:
                print(message.content)

##############################################################################
# 主函数 - 运行所有测试用例
##############################################################################

if __name__ == "__main__":
    print_separator("开始测试E2B沙箱环境")
    
    try:
        # 运行测试用例1：基本Python代码执行和环境信息
        run_test_case_1()
        
        # 运行测试用例2：文件系统操作
        run_test_case_2()
        
        # 运行测试用例3：包管理和第三方库使用
        run_test_case_3()
        
        # 运行测试用例4：Shell命令执行
        run_test_case_4()
        
        # 运行测试用例5：数据处理和可视化
        run_test_case_5()
        
        # 运行测试用例6：异常处理和错误恢复
        run_test_case_6()
        
        print_separator("E2B沙箱环境测试完成")
        print("测试结果已保存到 examples/output/sandbox_test 目录")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
    finally:
        # 关闭E2B沙箱
        print("\n正在关闭E2B沙箱...")
        for tool in react_agent.tools:
            if hasattr(tool, 'close'):
                tool.close()
        print("E2B沙箱已关闭")