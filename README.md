# Mentis

基于 LangGraph 的多智能体（Multi-Agents）协作系统，专注于实现复杂任务的智能分解与协同处理。

## 项目介绍

Mentis 是一个基于 LangGraph 构建的多智能体系统框架，通过 Supervisor 模式实现多个专业智能体的协同工作。系统的核心特点是将复杂任务分解为多个子任务，由不同专长的智能体协作完成，并由中央监督者（Supervisor）进行任务分发、协调和结果整合。

### 核心特性

- **Supervisor 模式**：中央控制智能体负责任务分发和结果整合
- **专业智能体**：每个智能体专注于特定领域的任务处理
- **控制权转移机制**：通过 `handoff` 工具实现智能体间的控制权转移
- **模块化设计**：便于扩展和维护的模块化架构
- **可视化工作流**：支持工作流程的可视化，便于理解和调试
- **实时信息获取**：通过 Tavily 搜索工具集成，使系统能够获取最新的网络信息

## 项目结构

```
.
├── core/               # 核心模块
│   ├── agents/         # 智能体模块
│   │   └── supervisor/ # Supervisor 实现
│   └── tools/          # 工具模块
├── examples/           # 示例代码
│   └── graphs/         # 工作流可视化图表
├── instructions/       # 使用说明文档
├── pyproject.toml      # 项目配置
└── requirements.txt    # 项目依赖
```

## 环境设置

本项目使用 uv 进行依赖管理。

### 安装依赖

```bash
uv venv
source .venv/bin/activate
uv sync
```

### 配置环境变量

项目使用第三方API服务，需要配置相应的API密钥。请按照以下步骤设置：

1. 复制 .env.example 文件为 .env：

```bash
cp .env.example .env
```

2. 编辑 .env 文件，填入所需的API密钥：

```
# LLM API Keys
OPENAI_API_KEY=your_openai_api_key

# Tool API Keys
TAVILY_API_KEY=your_tavily_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
JINA_API_KEY=your_jina_api_key
```

获取API密钥：
- OpenAI API密钥：在[OpenAI平台](https://platform.openai.com/api-keys)注册并创建
- Tavily API密钥：访问[Tavily AI](https://tavily.com/)注册获取
- FireCrawl API密钥：访问[FireCrawl](https://firecrawl.dev/)注册获取
- Jina API密钥：访问[Jina AI](https://jina.ai/)注册获取

### 配置环境变量

项目使用第三方API服务，需要配置相应的API密钥。请按照以下步骤设置：

1. 复制 .env.example 文件为 .env：

```bash
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

## 使用说明

项目包含多个示例实现，展示了不同功能和模式：

```bash
# 运行 Supervisor 模式示例
python examples/01_supervisor_test.py

# 运行 Supervisor Agent 模式示例
python examples/02_supervisor_agent_test.py

# 运行 Tavily 搜索工具集成示例
python examples/03_tavily_tools_test.py
```

示例将生成工作流可视化图表，保存在 graphs 目录下。

## 详细文档

详细的实现说明和使用指南，请参考 [instructions](https://github.com/foreveryh/mentis/tree/main/instructions) 目录下的文档：

- Supervisor 模式详解：介绍 Supervisor 模式的基本工作流程和控制权转移机制
- Supervisor Agent 模式详解：介绍 Supervisor 模式的 Agent 封装实现
- Tavily 搜索工具集成：介绍如何在多智能体系统中集成 Tavily 搜索工具，为系统提供实时信息获取能力