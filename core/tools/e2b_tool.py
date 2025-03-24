"""E2B Code Interpreter Tool for the multi-agent architecture.

This module contains a tool for executing Python code in a sandboxed environment using the E2B Code Interpreter SDK,
providing agents with the ability to run and analyze code safely.
"""
from typing import Dict, Any, Optional
import os
import json

from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field

# 定义工具分类 - 使用与registry.py中相同的枚举
from core.tools.registry import ToolCategory

# 设置工具分类为代码解释器
category = ToolCategory.CODE_INTERPRETER

# 定义富文本工具消息类，用于返回包含原始输出的工具消息
class RichToolMessage(ToolMessage):
    """扩展的工具消息类，包含原始输出数据"""
    raw_output: dict

# 定义代码解释器工具输入模型
class E2BCodeInterpreterToolInput(BaseModel):
    """E2B代码解释器工具的输入模型"""
    code: str = Field(description="要执行的Python代码")

# 定义E2B代码解释器工具类
class E2BCodeInterpreterTool(BaseTool):
    """使用E2B SDK执行Python代码的工具
    
    该工具创建一个安全的沙箱环境，用于执行Python代码，并返回执行结果、
    标准输出、标准错误和任何错误信息。
    
    Setup:
        安装 e2b_code_interpreter 包并设置环境变量 E2B_API_KEY

        .. code-block:: bash

            pip install e2b_code_interpreter
            export E2B_API_KEY="your-api-key"

    使用示例:

        .. code-block:: python

            from core.tools import E2BCodeInterpreterTool

            tool = E2BCodeInterpreterTool()
            result = tool.invoke({"code": "print('Hello, World!')"})            
    """
    
    name: str = "e2b_code_interpreter"
    description: str = (
        "Use this Python-only sandbox for calculations, data analysis, or visualizations"
        "matplotlib, pandas, numpy, sympy, and yfinance are available"
        "Remember to add the necessary imports for the libraries you use as they are not pre-imported"
        "Include library installations (!pip install <library_name>) in the code where required"
        "You can generate line based charts for data analysis"
        "Use 'plt.show()' for plots, and mention generated URLs for outputs"
        "Images are not allowed in the response!"
    )
    args_schema: type = E2BCodeInterpreterToolInput
    # 显式声明字段
    sandbox: Optional[Any] = None

    def __init__(self):
        """初始化E2B代码解释器工具"""
        # 调用父类的初始化方法
        super().__init__()
        # 设置自己的属性
        self._is_available = False
        self._init_error = None
        self._initialize_sandbox()
    
    def _initialize_sandbox(self):
        """初始化沙箱环境"""
        try:
            # 导入Sandbox类
            try:
                from e2b_code_interpreter import Sandbox
                print("使用E2B Sandbox API")
            except ImportError as e:
                self._init_error = f"未安装e2b_code_interpreter包: {str(e)}"
                print(f"错误: {self._init_error}")
                return

            # 检查环境变量
            if "E2B_API_KEY" not in os.environ:
                self._init_error = "未设置E2B_API_KEY环境变量"
                print(f"错误: {self._init_error}")
                print("提示: 可以通过以下方式设置环境变量:")
                print("  - 在.env文件中添加: E2B_API_KEY=your-api-key")
                print("  - 或在终端中执行: export E2B_API_KEY=your-api-key")
                return
            
            # 实例化沙箱
            print("正在初始化E2B沙箱...")
            self.sandbox = Sandbox()
            print("E2B沙箱初始化成功!")
            self._is_available = True
            self._init_error = None
            
        except Exception as e:
            self._init_error = f"初始化E2B沙箱时出错: {str(e)}"
            print(f"错误: {self._init_error}")
            self._is_available = False
    
    def _run(self, code: str, **kwargs) -> Dict[str, Any]:
        """执行Python代码并返回结果"""
        if not self._is_available or self.sandbox is None:
            error_message = "E2B沙箱未正确初始化"
            if self._init_error:
                error_message += f": {self._init_error}"
            
            # 提供安装和配置指南
            installation_guide = (
                "\n\n解决方法:\n"
                "1. 安装e2b_code_interpreter包: uv add e2b_code_interpreter\n"
                "2. 获取E2B API密钥: 访问 https://e2b.dev 注册并获取API密钥\n"
                "3. 设置环境变量: 在.env文件中添加 E2B_API_KEY=your-api-key 或在终端中执行 export E2B_API_KEY=your-api-key\n"
                "4. 重新运行程序"
            )
            
            return {
                "error": error_message + installation_guide,
                "results": None,
                "stdout": "",
                "stderr": ""
            }
        
        try:
            print(f"执行代码...\n{code}\n-----")
            
            # 使用Sandbox API执行代码
            execution = self.sandbox.run_code(code)
            
            # 返回结果
            return {
                "results": execution.results,
                "stdout": execution.logs.stdout,
                "stderr": execution.logs.stderr,
                "error": execution.error,
            }
        except Exception as e:
            return {
                "error": str(e),
                "results": None,
                "stdout": "",
                "stderr": f"执行代码时出错: {str(e)}"
            }
    
    def close(self):
        """关闭沙箱，释放资源"""
        if hasattr(self, "sandbox") and self._is_available and self.sandbox is not None:
            try:
                print("正在关闭E2B沙箱并释放资源...")
                self.sandbox.kill()
                print("E2B沙箱已成功关闭")
            except Exception as e:
                print(f"关闭E2B沙箱时出错: {str(e)}")
    
    @staticmethod
    def format_to_tool_message(tool_call_id: str, output: Dict[str, Any]) -> RichToolMessage:
        """将代码解释器输出格式化为工具消息
        
        Args:
            tool_call_id: 工具调用ID
            output: 代码解释器输出
            
        Returns:
            格式化的工具消息
        """
        # 将输出转换为JSON字符串，排除results字段
        content = json.dumps(
            {k: v for k, v in output.items() if k not in ("results")},
            ensure_ascii=False,
            indent=2
        )
        
        return RichToolMessage(
            content=content,
            raw_output=output,
            tool_call_id=tool_call_id,
        )

    def run_ai_code(self, code: str):
        """
        直接在沙箱中执行AI生成的代码
        
        Args:
            code (str): 要执行的代码字符串
            
        Returns:
            dict: 包含执行结果的字典
        """
        if not self._is_available:
            return {
                "success": False,
                "error": {
                    "name": "SandboxUnavailable",
                    "value": f"E2B沙箱不可用: {self._init_error}",
                    "traceback": ""
                }
            }
        
        try:
            # 执行代码
            execution = self.sandbox.run_code(code)
            
            result = {
                "success": True,
                "stdout": execution.stdout if hasattr(execution, "stdout") else "",
                "results": []
            }
            
            # 检查错误
            if hasattr(execution, "error") and execution.error:
                result["success"] = False
                result["error"] = {
                    "name": execution.error.name,
                    "value": execution.error.value,
                    "traceback": execution.error.traceback
                }
                return result
            
            # 处理结果
            if hasattr(execution, "results") and execution.results:
                for res in execution.results:
                    result_data = {"type": "text", "value": str(res)}
                    
                    # 处理PNG图像
                    if hasattr(res, "png") and res.png:
                        result_data["type"] = "png"
                        result_data["value"] = res.png  # base64编码的字符串
                    
                    result["results"].append(result_data)
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": {
                    "name": type(e).__name__,
                    "value": str(e),
                    "traceback": traceback.format_exc()
                }
            }