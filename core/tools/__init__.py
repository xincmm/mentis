# # Tools package initialization
# from langchain_community.agent_toolkits.load_tools import load_tools
# from core.tools.registry import register_tool, ToolCategory
# from core.tools.firecrawl_tool import FireCrawlTool
# import os
# import importlib

# # from dotenv import load_dotenv
# # load_dotenv()  # 自动加载 .env 文件
# # # 注册 LangChain 工具
# # langchain_tools = load_tools(["serpapi"])

# # for tool in langchain_tools:
# #     register_tool(tool, ToolCategory.SEARCH)
# # 获取 tools 目录路径
# tools_dir = os.path.dirname(__file__)

# # 遍历目录中的所有文件
# for filename in os.listdir(tools_dir):
#     # 只处理 .py 文件，且排除 __init__.py 和 registry.py
#     if filename.endswith('.py') and filename not in ['__init__.py', 'registry.py']:
#         # 提取模块名（去掉 .py 后缀）
#         module_name = filename[:-3]
#         try:
#             # 动态导入模块
#             module = importlib.import_module(f'.{module_name}', package='core.tools')
#             # 获取模块中的 tool 和 category
#             tool = getattr(module, 'name', None)
#             category = getattr(module, 'category', None)
#             if tool and category:
#                 # 注册工具
#                 register_tool(tool, category)
#             else:
#                 print(f"警告：{module_name} 中未定义 'tool' 或 'category' 变量")
#         except Exception as e:
#             print(f"导入 {module_name} 时出错：{e}")