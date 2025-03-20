from langgraph.prebuilt import create_react_agent
from core.agents.supervisor_agent import SupervisorAgent
from core.agents.research_agent import ResearchAgent
from core.agents.coder_agent import CoderAgent
from core.agents.reporter_agent import ReporterAgent
from core.agents.designer_agent import DesignerAgent
from core.agents.data_analyst_agent import DataAnalystAgent
from langchain_openai import ChatOpenAI
from langgraph.func import entrypoint, task
from langgraph.graph import add_messages
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
import os
import logging
import sys

load_dotenv()  # 自动加载 .env 文件

# 1. 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

##############################################################################
# Agent 2: Research Expert - 使用自定义的ResearchAgent
##############################################################################

research_agent = ResearchAgent(
    name="research_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
    debug=True
)

##############################################################################
# Agent 3: Coder - 使用自定义的CoderAgent
##############################################################################

coder_agent = CoderAgent(
    name="coder_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
    debug=True
)

##############################################################################
# Agent 4: Reporter - 使用自定义的ReporterAgent
##############################################################################

reporter_agent = ReporterAgent(
    name="reporter_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
    debug=True
)

##############################################################################
# Agent 5: Designer - 使用自定义的DesignerAgent
##############################################################################

designer_agent = DesignerAgent(
    name="designer_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
    debug=True
)

##############################################################################
# Agent 6: Data Analyst - 使用自定义的DataAnalystAgent
##############################################################################

data_analyst_agent = DataAnalystAgent(
    name="data_analyst_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
    debug=True
)

##############################################################################
# 使用带有Planning功能的SupervisorAgent协调所有角色
##############################################################################

# 创建 SupervisorAgent 实例，启用Planning功能
supervisor = SupervisorAgent(
    agents=[
        research_agent,
        coder_agent,
        reporter_agent,
        designer_agent,
        data_analyst_agent,
    ],
    model=model,
    enable_planning=True,  # 启用Planning功能
)

app = supervisor.compile()

# 获取当前文件名（不含路径和扩展名）
current_file = os.path.basename(__file__)
file_name_without_ext = os.path.splitext(current_file)[0]
graph_dir = os.path.join(os.path.dirname(__file__), "graphs")

# 确保 graphs 目录存在
os.makedirs(graph_dir, exist_ok=True)

# 生成与文件名一致的图片名，并保存到 examples/graphs 目录
image_data = app.get_graph().draw_mermaid_png()
graph_path = os.path.join(graph_dir, f"{file_name_without_ext}.png")

# 保存图片（如果已存在则覆盖）
with open(graph_path, "wb") as f:
    f.write(image_data)

print(f"Image saved as {graph_path}")

##############################################################################
# 测试：复杂请求需要规划和多个步骤
##############################################################################

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_interactions.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置langgraph的日志级别为INFO，以便捕获更多交互信息
logging.getLogger('langgraph').setLevel(logging.INFO)

if __name__ == "__main__":
    # 测试1：需要研究和编码的任务
    result1 = app.invoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    "我需要一个简单的Python爬虫来获取最新的科技新闻，并将结果保存为CSV文件。"
                    "请先研究一下如何实现，然后提供代码，最后生成一份报告总结这个解决方案。"
                )
            }
        ]
    })
    
    print("\n测试1结果:")
    for m in result1["messages"]:
        m.pretty_print()
    
    # 测试2：需要设计和数据分析的任务
    result2 = app.invoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    "我有一个电商网站，需要重新设计产品页面，并分析现有的用户行为数据来优化转化率。"
                    "请提供一个设计方案和数据分析建议。最后，讲个笑话来缓解一下压力。"
                )
            }
        ]
    })
    
    print("\n测试2结果:")
    for m in result2["messages"]:
        m.pretty_print()