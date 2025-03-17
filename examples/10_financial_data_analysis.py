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
        
        # 判断是否为二进制文件
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.svg', '.xlsx', '.xls', '.zip', '.bin']
        is_binary = any(sandbox_path.lower().endswith(ext) for ext in binary_extensions)
        
        # 根据文件类型选择写入模式
        if is_binary:
            with open(local_path, 'wb') as file:
                file.write(content.encode() if isinstance(content, str) else content)
        else:
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
                if download_directory_from_sandbox(sandbox, sandbox_file_path, local_file_path):
                    downloaded_count += 1
            else:
                # 下载文件
                if download_file_from_sandbox(sandbox, sandbox_file_path, local_file_path):
                    downloaded_count += 1
        
        if downloaded_count > 0:
            print(f"从 {sandbox_dir_path} 下载了 {downloaded_count} 个文件/目录到 {local_dir_path}")
            return True
        return False
        
    except Exception as e:
        print(f"从沙箱下载目录时出错: {str(e)}")
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
                
                # # 检查是否有E2B沙箱实例并下载文件
                # for msg in final_state["messages"]:
                #     if isinstance(msg, ToolMessage) and msg.name == "e2b_code_interpreter":
                #         try:
                #             # 获取沙箱实例
                #             if 'sandbox' in dir(react_agent.tools[0]):
                #                 sandbox = react_agent.tools[0].sandbox
                                
                #                 # 设置输出目录
                #                 output_dir = os.path.join(os.path.dirname(__file__), "output")
                #                 os.makedirs(output_dir, exist_ok=True)
                                
                #                 # 直接下载主要工作目录
                #                 print("\n从沙箱下载文件到本地...")
                #                 download_directory_from_sandbox(sandbox, "/home/user", output_dir)
                                
                #                 # 下载临时目录中可能的图表和数据文件
                #                 download_directory_from_sandbox(sandbox, "/tmp", output_dir)
                                
                #                 print(f"\n文件已保存到目录: {output_dir}")
                #         except Exception as e:
                #             print(f"从沙箱下载文件时出错: {str(e)}")              
    
    # 关闭E2B沙箱
    for tool in react_agent.tools:
        if hasattr(tool, 'close'):
            tool.close()

# 工具调用:
# - 工具: e2b_code_interpreter
# - 参数: {'code': "import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\n\n# 设置随机数种子，以便结果可重复\nnp.random.seed(42)\n\n# 生成模拟的财务数据\nnum_months = 12\nmonths = pd.date_range(start='2023-01-01', periods=num_months, freq='M')\n\n# 随机生成收入、支出、利润\nrevenue = np.random.randint(10000, 50000, num_months)\nexpenses = np.random.randint(5000, 20000, num_months)\nprofit = revenue - expenses\n\n# 创建 DataFrame\ndata = pd.DataFrame({'Month': months, 'Revenue': revenue, 'Expenses': expenses, 'Profit': profit})\n\ndata.set_index('Month', inplace=True)\n\n# 计算总收入、总支出、总利润\ntotal_revenue = data['Revenue'].sum()\ntotal_expenses = data['Expenses'].sum()\ntotal_profit = data['Profit'].sum()\n\n# 输出分析结果\nanalysis_results = {'Total Revenue': total_revenue, 'Total Expenses': total_expenses, 'Total Profit': total_profit}\n\n# 可视化数据\t\nplt.figure(figsize=(10, 5))\nplt.plot(data.index, data['Revenue'], label='Revenue', marker='o')\nplt.plot(data.index, data['Expenses'], label='Expenses', marker='o')\nplt.plot(data.index, data['Profit'], label='Profit', marker='o')\nplt.title('Monthly Financial Data')\nplt.xlabel('Month')\nplt.ylabel('Amount ($)')\nplt.legend()\nplt.grid()\n\n# 创建output目录用于存储生成的文件\nimport os\noutput_dir = '/home/user/output'\nos.makedirs(output_dir, exist_ok=True)\n\n# 保存图表到output目录\nmonthly_chart_path = os.path.join(output_dir, 'monthly_financial_data.png')\nplt.savefig(monthly_chart_path)\n\n# 保存数据和分析结果到 CSV 文件\ncsv_path = os.path.join(output_dir, 'financial_data.csv')\ndata.to_csv(csv_path)\n\n# 创建财务分析报告\nreport = f\"\"\"# 财务数据分析报告\n\n## 概述\n\n本报告分析了2023年1月至12月的财务数据，包括收入、支出和利润情况。\n\n## 财务摘要\n\n- **总收入**: ${total_revenue:,}\n- **总支出**: ${total_expenses:,}\n- **总利润**: ${total_profit:,}\n- **平均月收入**: ${data['Revenue'].mean():,.2f}\n- **平均月支出**: ${data['Expenses'].mean():,.2f}\n- **平均月利润**: ${data['Profit'].mean():,.2f}\n\n## 月度表现\n\n- **最高收入月**: {data['Revenue'].idxmax().strftime('%Y年%m月')} (${data['Revenue'].max():,})\n- **最低收入月**: {data['Revenue'].idxmin().strftime('%Y年%m月')} (${data['Revenue'].min():,})\n- **最高利润月**: {data['Profit'].idxmax().strftime('%Y年%m月')} (${data['Profit'].max():,})\n- **最低利润月**: {data['Profit'].idxmin().strftime('%Y年%m月')} (${data['Profit'].min():,})\n\n## 趋势分析\n\n收入趋势: {\"上升\" if data['Revenue'].iloc[-1] > data['Revenue'].iloc[0] else \"下降\"}\n支出趋势: {\"上升\" if data['Expenses'].iloc[-1] > data['Expenses'].iloc[0] else \"下降\"}\n利润趋势: {\"上升\" if data['Profit'].iloc[-1] > data['Profit'].iloc[0] else \"下降\"}\n\n## 结论与建议\n\n根据分析结果，提出以下建议：\n\n1. {\"增加营销投入以提高收入\" if data['Revenue'].mean() < 30000 else \"维持当前营销策略\"}\n2. {\"控制支出\" if data['Expenses'].mean() > 15000 else \"可适当增加投资\"}\n3. {\"关注利润率提升\" if (data['Profit'] / data['Revenue']).mean() < 0.5 else \"保持良好的利润率\"}\n\n## 附件\n\n- 月度财务数据图表 (monthly_financial_data.png)\n- 财务数据CSV文件 (financial_data.csv)\"\"\"\n\n# 保存报告到文件\nreport_path = os.path.join(output_dir, 'financial_analysis_report.md')\nwith open(report_path, 'w', encoding='utf-8') as f:\n    f.write(report)\n\n# 返回分析结果和文件路径信息\nanalysis_results"}