from enum import Enum
from langchain.tools import Tool

# 定义工具分类枚举
class ToolCategory(Enum):
    SEARCH = "Search"
    CODE_INTERPRETER = "Code Interpreter"
    WEB_BROWSING = "Web Browsing"
    DATABASE = "Database"
    FILE_SYSTEM = "FileSystem"
    OTHER = "Other"

# 全局工具注册表
_registered_tools = {}

def register_tool(tool: Tool, category: ToolCategory):
    """注册一个工具到全局字典中，带有分类信息"""
    if tool.name in _registered_tools:
        raise ValueError(f"工具名 {tool.name} 已存在，请确保工具名唯一")
    _registered_tools[tool.name] = {
        "tool": tool,
        "category": category
    }

def get_registered_tools() -> dict:
    """返回所有已注册的工具"""
    return _registered_tools

def get_tool(name: str) -> dict:
    """根据名称获取工具及其分类"""
    tool_info = _registered_tools.get(name)
    if tool_info:
        return {
            "tool": tool_info["tool"],
            "category": tool_info["category"].value
        }
    return None

def get_tools_by_category(category: ToolCategory) -> list:
    """返回指定分类的工具名称列表"""
    return [name for name, info in _registered_tools.items() if info["category"] == category]