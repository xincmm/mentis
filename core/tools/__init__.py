# Tools package initialization
from langchain_community.agent_toolkits.load_tools import load_tools
from core.tools.registry import register_tool, ToolCategory, get_registered_tools
from core.tools.firecrawl_tool import FireCrawlTool
import os
import importlib
import inspect
from typing import Any, Dict, List, Type
from langchain_core.tools import BaseTool

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件

# 注册自定义工具 - FireCrawlTool
firecrawl_tool = FireCrawlTool()
register_tool(firecrawl_tool, ToolCategory.WEB_BROWSING)

# 注册 LangChain 工具 - 使用load_tools加载的工具列表
langchain_tools = load_tools(["serpapi"])
for tool in langchain_tools:
    register_tool(tool, ToolCategory.SEARCH)

# 工具类别映射 - 用于自动分类直接导入的工具
tool_category_mapping = {
    # 搜索类工具
    "JinaSearch": ToolCategory.SEARCH,
    "TavilySearchResults": ToolCategory.SEARCH,
    "GoogleSearchResults": ToolCategory.SEARCH,
    "GoogleSerperResults": ToolCategory.SEARCH,
    "WikipediaQueryRun": ToolCategory.SEARCH,
    
    # 网页浏览类工具
    "WebBrowser": ToolCategory.WEB_BROWSING,
    "ArxivQueryRun": ToolCategory.WEB_BROWSING,
    "RequestsGet": ToolCategory.WEB_BROWSING,
    "RequestsPost": ToolCategory.WEB_BROWSING,
    
    # 文件系统类工具
    "WriteFile": ToolCategory.FILE_SYSTEM,
    "ReadFile": ToolCategory.FILE_SYSTEM,
    "ListDirectory": ToolCategory.FILE_SYSTEM,
    
    # 代码解释器类工具
    "PythonREPL": ToolCategory.CODE_INTERPRETER,
    "ShellTool": ToolCategory.CODE_INTERPRETER,
    
    # 数据库类工具
    "SQLDatabaseTool": ToolCategory.DATABASE,
    
    # 默认为其他类别
    "default": ToolCategory.OTHER
}

def register_direct_tool(tool_instance: BaseTool, category: ToolCategory = None) -> None:
    """注册直接从langchain_community.tools导入的工具
    
    Args:
        tool_instance: 工具实例
        category: 工具类别，如果为None则自动根据工具名称判断类别
    """
    if not category:
        # 获取工具类名
        tool_class_name = tool_instance.__class__.__name__
        # 根据工具类名自动判断类别
        category = tool_category_mapping.get(tool_class_name, tool_category_mapping["default"])
    
    # 注册工具
    register_tool(tool_instance, category)
    print(f"已注册工具: {tool_instance.name} (类别: {category.value})")

# 获取 tools 目录路径
tools_dir = os.path.dirname(__file__)

# 遍历目录中的所有文件，注册自定义工具
for filename in os.listdir(tools_dir):
    # 只处理 .py 文件，且排除 __init__.py 和 registry.py
    if filename.endswith('.py') and filename not in ['__init__.py', 'registry.py']:
        # 提取模块名（去掉 .py 后缀）
        module_name = filename[:-3]
        try:
            # 动态导入模块
            module = importlib.import_module(f'.{module_name}', package='core.tools')
            
            # 查找模块中的工具类（继承自BaseTool的类）
            for name, obj in inspect.getmembers(module):
                # 检查是否是类且是BaseTool的子类
                if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                    # 检查该类是否已经被实例化并注册
                    tool_name = getattr(obj, 'name', None)
                    if tool_name and tool_name not in [info['tool'].name for info in get_registered_tools().values()]:
                        # 确定工具类别
                        category = getattr(module, 'category', ToolCategory.OTHER)
                        # 实例化并注册工具
                        try:
                            tool_instance = obj()
                            register_tool(tool_instance, category)
                            print(f"已注册工具类: {name} (工具名: {tool_instance.name}, 类别: {category.value})")
                        except Exception as e:
                            print(f"实例化工具类 {name} 时出错: {e}")
        except Exception as e:
            print(f"导入 {module_name} 时出错: {e}")