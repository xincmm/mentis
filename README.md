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

## 项目结构

```
.
├── core/               # 核心模块
│   ├── agents/         # 智能体模块
│   │   └── supervisor.py  # Supervisor 实现
│   └── tools/          # 工具模块
├── examples/           # 示例代码
│   ├── 01_supervisor_test.py  # Supervisor 模式示例
│   └── graphs/         # 工作流可视化图表
├── instructions/       # 使用说明文档
│   └── 01.supervisor_pattern.md  # Supervisor 模式详解
├── pyproject.toml      # 项目配置
└── requirements.txt    # 项目依赖
```

## 环境设置

本项目使用 uv 进行依赖管理。

### 安装依赖

```bash
uv venv
uv pip install -r requirements.txt
```

### 激活虚拟环境

```bash
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

## 使用说明

### Supervisor 模式示例

项目包含一个 Supervisor 模式的示例实现，展示了如何协调多个智能体完成复合任务：

1. **笑话生成器**：使用功能型 API 创建的专业智能体，负责生成幽默内容
2. **研究专家**：使用图形 API 创建的专业智能体，负责查询和提供事实信息
3. **Supervisor**：协调上述两个智能体，根据用户需求按顺序调用它们

运行示例：

```bash
python examples/01_supervisor_test.py
```

示例将生成工作流可视化图表，保存在 `examples/graphs/` 目录下。

### 创建自定义智能体

Mentis 支持两种方式创建智能体：

#### 功能型 API（Functional API）

```python
@task
def generate_content(messages):
    # 实现智能体逻辑
    return result

@entrypoint()
def custom_agent(state):
    # 调用任务并处理结果
    return {"messages": messages}
```

#### 图形 API（Graph API）

```python
custom_agent = create_react_agent(
    model=model,
    tools=[tool_function],
    name="custom_agent",
    prompt="智能体的系统提示"
)
```

### 创建 Supervisor

使用 `create_supervisor` 函数创建 Supervisor 并协调多个智能体：

```python
workflow = create_supervisor(
    [agent1, agent2, ...],  # 专业智能体列表
    model=model,            # 语言模型
    prompt="Supervisor 的系统提示"
)
```

## 更多资源

详细的实现说明和使用指南，请参考 `instructions/` 目录下的文档：

- [Supervisor 模式详解](instructions/01.supervisor_pattern.md)：介绍 Supervisor 模式的工作原理和实现细节