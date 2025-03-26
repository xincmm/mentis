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
import io
from contextlib import redirect_stdout, redirect_stderr

load_dotenv()  # 自动加载 .env 文件

# 1. 初始化大模型
model = ChatOpenAI(model="gpt-4o-mini")

# 设置日志捕获
class LogCapture:
    def __init__(self):
        self.log_buffer = io.StringIO()
        self.log_content = []
    
    def start_capture(self):
        self.log_buffer = io.StringIO()
        return self.log_buffer
    
    def stop_capture(self):
        output = self.log_buffer.getvalue()
        self.log_content.append(output)
        return output
    
    def get_content(self):
        return "\n".join(self.log_content)

log_capture = LogCapture()

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
from core.tools.e2b_tool import E2BCodeInterpreterTool
e2b_tool = E2BCodeInterpreterTool()

coder_agent = CoderAgent(
    name="coder_expert",
    model=model,
    tools=[e2b_tool],
    max_iterations=5,
    cache_enabled=True,
)

##############################################################################
# Agent 4: Reporter - 使用自定义的ReporterAgent
##############################################################################

reporter_agent = ReporterAgent(
    name="reporter_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
)

##############################################################################
# Agent 5: Designer - 使用自定义的DesignerAgent
##############################################################################

designer_agent = DesignerAgent(
    name="designer_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
)

##############################################################################
# Agent 6: Data Analyst - 使用自定义的DataAnalystAgent
##############################################################################

data_analyst_agent = DataAnalystAgent(
    name="data_analyst_expert",
    model=model,
    max_iterations=5,
    cache_enabled=True,
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
enable_planning=True)

# 获取当前文件名（不含路径和扩展名）
current_file = os.path.basename(__file__)
file_name_without_ext = os.path.splitext(current_file)[0]
logs_dir = os.path.join(os.path.dirname(__file__), "logs")
# 创建图表输出文件路径
os.makedirs(logs_dir, exist_ok=True)
# 创建Markdown输出文件路径
markdown_path = os.path.join(logs_dir, f"{file_name_without_ext}.md")

##############################################################################
# 测试：复杂请求需要规划和多个步骤
##############################################################################

def save_markdown_log():
    """将执行结果保存为Markdown文件"""
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(f"# 执行结果: {file_name_without_ext}\n\n")
        f.write("## 图表\n\n")
        f.write("## 执行日志\n\n")
        f.write("```\n")
        f.write(log_capture.get_content())
        f.write("\n```\n")
    print(f"执行日志已保存到 {markdown_path}")

if __name__ == "__main__":
    try:
        # 开始捕获输出
        log_buffer = log_capture.start_capture()
        
        with redirect_stdout(log_buffer), redirect_stderr(log_buffer):
            print(f"开始执行 {current_file} 测试...")
            
            # 测试1：需要研究和编码的任务
            print("\n## 测试1：需要研究和编码的任务")
            result1 = supervisor.run({
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "我需要一个简单的Python爬虫来获取最新的科技新闻，并将结果保存为CSV文件。"
                            "请提供完整的代码，并确保代码能够正常运行。"
                            "最后，讲个笑话来缓解一下压力。"
                        )
                    }
                ]
            })
            
            print("\n测试1结果:")
            for m in result1["messages"]:
                m.pretty_print()
            
            # # 测试2：需要设计和数据分析的任务
            # result2 = app.invoke({
            #     "messages": [
            #         {
            #             "role": "user",
            #             "content": (
            #                 "我有一个电商网站，需要重新设计产品页面，并分析现有的用户行为数据来优化转化率。"
            #                 "请提供一个设计方案和数据分析建议。最后，讲个笑话来缓解一下压力。"
            #             )
            #         }
            #     ]
            # })
            
            # print("\n测试2结果:")
            # for m in result2["messages"]:
            #     m.pretty_print()
    finally:
        # 停止捕获并保存结果
        log_capture.stop_capture()
        save_markdown_log()