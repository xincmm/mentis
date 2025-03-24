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

def run_ai_generated_code(sandbox, code: str, save_results_dir=None):
    """在 E2B 沙箱中执行 AI 生成的代码
    
    Args:
        sandbox: 沙箱实例
        code: AI 生成的代码字符串
        save_results_dir: 用于保存结果文件的本地目录路径（可选）
    
    Returns:
        dict: 包含执行结果的字典
    """
    try:
        print("在沙箱中执行 AI 生成的代码...")
        # 确保代码是字符串类型
        if not isinstance(code, str):
            code = str(code)
            
        # 执行代码
        execution = sandbox.run_code(code)
        print("代码执行完成!")
        
        # 准备结果字典
        result = {
            "success": True,
            "stdout": "",
            "results": []
        }
        
        # 提取标准输出
        if hasattr(execution, "stdout"):
            result["stdout"] = execution.stdout
            
        # 检查代码是否执行成功
        if hasattr(execution, "error") and execution.error:
            error_name = getattr(execution.error, "name", "Unknown")
            error_value = getattr(execution.error, "value", "Unknown error")
            error_traceback = getattr(execution.error, "traceback", "")
            
            print("AI 生成的代码执行出错:")
            print(f"错误类型: {error_name}")
            print(f"错误信息: {error_value}")
            if error_traceback:
                print(f"错误追踪: {error_traceback}")
                
            result["success"] = False
            result["error"] = {
                "name": error_name,
                "value": error_value,
                "traceback": error_traceback
            }
            return result
        
        # 处理执行结果
        if hasattr(execution, "results") and execution.results:
            import base64
            result_idx = 0
            
            for res in execution.results:
                # 默认为文本结果
                result_data = {"type": "text", "value": str(res)}
                
                # 检查是否有PNG图像
                if hasattr(res, "png") and res.png:
                    result_data["type"] = "png"
                    result_data["value"] = res.png  # base64编码的字符串
                    
                    # 如果指定了保存目录，保存图像到本地
                    if save_results_dir:
                        try:
                            os.makedirs(save_results_dir, exist_ok=True)
                            image_path = os.path.join(save_results_dir, f"result-{result_idx}.png")
                            
                            # 解码并保存图像
                            with open(image_path, 'wb') as f:
                                f.write(base64.b64decode(res.png))
                            print(f"图像已保存到: {image_path}")
                            result_data["local_path"] = image_path
                        except Exception as img_err:
                            print(f"保存图像时出错: {str(img_err)}")
                
                result["results"].append(result_data)
                result_idx += 1
        
        return result
        
    except Exception as e:
        print(f"执行AI生成的代码时出错: {str(e)}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return {
            "success": False,
            "error": {
                "name": type(e).__name__,
                "value": str(e),
                "traceback": traceback.format_exc()
            }
        }

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
        print(f"下载整个目录时出错: {str(e)}")
        import traceback
        print(f"详细错误跟踪: {traceback.format_exc()}")

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
        "- 所有文件和图片必须保存在沙盒环境中的特定目录，不要直接返回图片\n"
        "- 图片不允许在回复中展示！Images are not allowed in the response!\n"
        "- 测试应覆盖沙箱的各种功能，包括但不限于：\n"
        "  * 基本Python代码执行\n"
        "  * 文件系统操作（创建、读取、写入文件）\n"
        "  * 包管理（安装和使用第三方包）\n"
        "  * 系统命令执行（使用!前缀执行shell命令）\n"
        "  * 数据处理和可视化\n"
        "  * 异常处理和错误恢复\n"
    ),
)

# 添加调试信息，验证工具列表和沙箱实例的初始状态
print("\n验证ReactAgent工具列表和沙箱实例初始状态:")
print(f"react_agent.tools类型: {type(react_agent.tools)}")
print(f"react_agent.tools长度: {len(react_agent.tools)}")

# 遍历所有工具，检查是否有sandbox属性
for i, tool in enumerate(react_agent.tools):
    print(f"\n工具[{i}]类型: {type(tool)}")
    print(f"工具[{i}]名称: {getattr(tool, 'name', '未知')}")
    print(f"工具[{i}]是否有sandbox属性: {'sandbox' in dir(tool)}")
    
    # 如果有sandbox属性，打印沙箱实例信息
    if 'sandbox' in dir(tool):
        print(f"工具[{i}]的sandbox类型: {type(tool.sandbox)}")
        print(f"工具[{i}]的sandbox是否可用: {getattr(tool, '_is_available', False)}")
        print(f"工具[{i}]的初始化错误: {getattr(tool, '_init_error', None)}")

# 编译Agent
agent = react_agent.compile()

# # 获取图对象
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
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
            HumanMessage(content="请测试沙箱环境的文件系统操作，包括创建目录、创建文件、写入内容、读取内容、列出目录内容等。创建一个测试目录结构，并将操作结果保存到文件中。文件保存到 /home/user/test_dir")
        ]
    }
    
    # 使用stream方法逐步获取中间状态
    final_state = None
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
                            print(f"\n工具消息内容解析成功: {type(tool_output)}")
                            
                            # 检查是否有原始输出
                            if hasattr(msg, 'raw_output') and msg.raw_output:
                                print(f"\n消息包含raw_output属性: {type(msg.raw_output)}")
                                
                                # 打印react_agent.tools的信息
                                print(f"\nreact_agent.tools类型: {type(react_agent.tools)}")
                                print(f"react_agent.tools长度: {len(react_agent.tools)}")
                                
                                # 遍历所有工具，检查是否有sandbox属性
                                for i, tool in enumerate(react_agent.tools):
                                    print(f"\n工具[{i}]类型: {type(tool)}")
                                    print(f"工具[{i}]名称: {getattr(tool, 'name', '未知')}")
                                    print(f"工具[{i}]是否有sandbox属性: {'sandbox' in dir(tool)}")
                                    if 'sandbox' in dir(tool):
                                        print(f"工具[{i}]的sandbox类型: {type(tool.sandbox)}")
                                
                                # 遍历 react_agent.tools 以查找 E2B 相关工具
                                sandbox = None
                                for tool in react_agent.tools:
                                    if hasattr(tool, "sandbox"):
                                        sandbox = tool.sandbox
                                        break  # 找到后就退出循环
                                
                                if sandbox:
                                    print("\n成功获取沙箱实例!")
                                    print(f"沙箱实例类型: {type(sandbox)}")
                                    
                                    # 从沙箱下载生成的文件
                                    output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                    os.makedirs(output_dir, exist_ok=True)
                                    print(f"输出目录已创建: {output_dir}")
                                    
                                    # 尝试下载测试目录，路径和提示中保持一致
                                    sandbox_test_path = "/home/user/test_dir"
                                    print(f"尝试从沙箱下载目录: {sandbox_test_path}")
                                    download_directory_from_sandbox(sandbox, sandbox_test_path, os.path.join(output_dir, "test_dir"))
                                else:
                                    print("\n错误: 无法获取沙箱实例，没有找到具有sandbox属性的工具")
                            else:
                                print("\n错误: 消息没有raw_output属性")
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
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
            HumanMessage(content="请测试沙箱环境中执行Shell命令的功能，使用!前缀执行一系列Linux命令，包括系统信息查询、目录操作、文件查找等。将命令执行结果保存到文件（/home/user/shell_commands_results.txt）中。")
        ]
    }
    
    # 使用stream方法逐步获取中间状态
    final_state = None
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
                            print(f"\n测试用例4: 检查工具消息类型: {type(msg)}")
                            print(f"测试用例4: 工具消息名称: {msg.name}")
                            
                            # 检查react_agent.tools的信息
                            print(f"\n测试用例4: react_agent.tools类型: {type(react_agent.tools)}")
                            print(f"测试用例4: react_agent.tools长度: {len(react_agent.tools)}")
                            
                            # 遍历 react_agent.tools 以查找 E2B 相关工具
                            sandbox = None
                            for tool in react_agent.tools:
                                if hasattr(tool, "sandbox"):
                                    sandbox = tool.sandbox
                                    break  # 找到后就退出循环
                            
                            if sandbox:
                                print("\n测试用例4: 成功获取沙箱实例!")
                                print(f"测试用例4: 沙箱实例类型: {type(sandbox)}")
                                print(f"测试用例4: 沙箱实例属性: {dir(sandbox)[:10]}...")
                                
                                output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                os.makedirs(output_dir, exist_ok=True)
                                print(f"测试用例4: 输出目录已创建: {output_dir}")
                                
                                # 尝试下载shell命令结果文件，路径和提示中保持一致
                                sandbox_file_path = "/home/user/shell_commands_results.txt"
                                local_file_path = os.path.join(output_dir, "shell_commands_results.txt")
                                print(f"测试用例4: 尝试下载文件: {sandbox_file_path} -> {local_file_path}")
                                download_file_from_sandbox(sandbox, sandbox_file_path, local_file_path)
                            else:
                                print("\n测试用例4: 错误: 无法获取沙箱实例，没有找到具有sandbox属性的工具")
                                print(f"测试用例4: react_agent.tools的类型和长度: {type(react_agent.tools)}, {len(react_agent.tools)}")
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
            HumanMessage(content=(
                "请测试沙箱环境的数据处理和可视化功能，生成一些随机数据，使用pandas进行数据处理，"
                "然后使用matplotlib创建多种类型的图表（折线图、柱状图、散点图等）。\n"
                "严格按照以下要求:\n"
                "1. 将所有图表保存到 /home/user/visualizations 目录\n"
                "2. 不要在回复中包含图片 - 图片直接保存到上述目录即可\n"
                "3. Images are not allowed in the response!\n"
                "4. 只需描述你做了什么，创建了哪些图表，并说明它们保存在哪里\n"
                "5. 请确保目录存在后再保存图片\n"
            ))
        ]
    }
    
    # 使用stream方法逐步获取中间状态
    final_state = None
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
                            # 遍历 react_agent.tools 以查找 E2B 相关工具
                            sandbox = None
                            for tool in react_agent.tools:
                                if hasattr(tool, "sandbox"):
                                    sandbox = tool.sandbox
                                    break  # 找到后就退出循环
                            
                            if sandbox:
                                output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
                                os.makedirs(output_dir, exist_ok=True)
                                
                                # 针对性地下载可视化目录中的图表
                                vis_dir = "/home/user/visualizations"
                                local_vis_dir = os.path.join(output_dir, "visualizations")
                                os.makedirs(local_vis_dir, exist_ok=True)
                                print(f"测试用例5: 下载可视化图表目录: {vis_dir} -> {local_vis_dir}")
                                
                                # 尝试列出可视化目录中的文件
                                try:
                                    files = sandbox.files.list(vis_dir)
                                    if files:
                                        print(f"找到图表文件:")
                                        for file_info in files:
                                            file_name = getattr(file_info, "name", "未知文件")
                                            print(f"- {file_name}")
                                    else:
                                        print(f"警告: 可视化目录为空或不存在")
                                except Exception as e:
                                    print(f"列出可视化目录文件时出错: {str(e)}")
                                
                                # 执行下载
                                success = download_directory_from_sandbox(sandbox, vis_dir, local_vis_dir)
                                if success:
                                    print(f"✅ 成功下载可视化图表")
                                else:
                                    print(f"⚠️ 下载可视化图表失败，尝试下载整个用户目录作为备份")
                                    download_directory_from_sandbox(sandbox, "/home/user", output_dir)
                            else:
                                print("\n错误: 无法获取沙箱实例，没有找到具有sandbox属性的工具")
                        except Exception as e:
                            print(f"下载文件时出错: {str(e)}")
                            import traceback
                            print(f"错误详情: {traceback.format_exc()}")

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
    for partial_state in agent.stream(inputs, stream_mode="values"):
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
        # 确保输出目录存在
        output_dir = os.path.join(os.path.dirname(__file__), "output", "sandbox_test")
        os.makedirs(output_dir, exist_ok=True)
        print(f"创建输出目录: {output_dir}")
        
        # 确保可视化输出目录存在
        vis_output_dir = os.path.join(output_dir, "visualizations")
        os.makedirs(vis_output_dir, exist_ok=True)
        print(f"创建可视化输出目录: {vis_output_dir}")
        
        # # 运行测试用例
        # # 运行测试用例1：基本Python代码执行和环境信息
        # run_test_case_1()
        
        # # 运行测试用例2：文件系统操作
        # run_test_case_2()
        
        # # 运行测试用例3：包管理和第三方库使用
        # run_test_case_3()
        
        # # 运行测试用例4：Shell命令执行
        # run_test_case_4()
        
        # 运行测试用例5：数据处理和可视化
        run_test_case_5()
        
        # # 运行测试用例6：异常处理和错误恢复
        # run_test_case_6()
        
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