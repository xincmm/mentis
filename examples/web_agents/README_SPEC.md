# Web Agent 开发规范

## 1. 概述

本规范旨在统一Web Agent的开发流程和命名约定，确保前后端协同工作，避免出现前端组件无法正确显示后端数据的问题。本文档基于实际开发经验，特别强调前后端节点命名一致性的重要性。

## 2. 节点命名规范

## 2. 前后端交互核心机制

### 2.1 关键概念

- **节点名称匹配**: 前端渲染组件时，会根据后端节点的名称来选择对应的组件进行渲染
- **状态数据结构**: 后端节点生成的状态数据必须符合前端组件期望的结构
- **渲染函数**: 前端的`renderNode`函数是连接后端节点和前端组件的关键桥梁

### 2.2 渲染流程

1. 后端节点执行并生成状态数据
2. 前端通过`useLangGraphAgent`钩子接收节点数据
3. 前端的`renderNode`函数根据节点名称选择对应组件
4. 组件根据状态数据进行渲染

## 3. 节点命名规范

### 3.1 关键节点命名

所有Web Agent必须在图结构中包含处理消息的节点，这些节点名称必须与前端`renderNode`函数中的case语句匹配：

```python
# 后端节点命名 - 必须与前端renderNode函数中的case匹配
builder.add_node("agent", agent_function)  # 或其他在前端已注册的节点名称
```

**重要提示**: 前端`page.tsx`中的`renderNode`函数定义了可识别的节点名称。目前支持的节点名称有：
- `__start__`
- `agent` (替代了原来的`chatbot`)
- `weather`
- `reminder`
- `research`
- `search`
- `report`

如果后端使用了其他节点名称，必须在前端的`renderNode`函数中添加对应的case语句。

### 3.2 状态字段命名

- 状态字段名称应与前端组件期望的字段名称保持一致
- 使用蛇形命名法（snake_case）命名状态字段
- 复杂数据结构应使用数组形式，即使只有一个元素

### 3.3 必要的状态字段

每个Web Agent必须在`agent-types.ts`文件中定义其状态接口，并确保后端发送的状态与此接口匹配：

```typescript
export interface AgentState extends WithMessages {
  // 定义Agent特有的状态字段
  weather_forecast?: WeatherForecast[];
  research_status?: ResearchStatus[];
  // 其他状态字段
}
```

## 4. 前端组件规范

### 4.1 组件结构

- 主组件应根据节点名称渲染不同的子组件
- 子组件应检查所需状态字段是否存在，并提供合理的默认行为

```typescript
export default function renderNode(checkpoint, node) {
  switch (node.name) {
    case '__start__':
    case 'agent':  // 注意：这里使用'agent'替代了原来的'chatbot'
      return <ChatbotNode nodeState={node.state} />;
    case 'weather':
      return <WeatherNode nodeState={node.state} />;
    // 其他节点类型
    default:
      return null;
  }
}
```

### 4.2 组件注册

所有Web Agent的节点组件必须在`page.tsx`的`renderNode`函数中正确注册：

```typescript
const renderNode = (checkpoint, node) => {
  switch (node.name) {
    // 确保这里的节点名称与后端图定义中的节点名称一致
    case '__start__':
    case 'agent':  // 注意：这里使用'agent'替代了原来的'chatbot'
      return <ChatbotNode nodeState={node.state} />;
    case 'weather':
      return <WeatherNode nodeState={node.state} />;
    case 'reminder':
      return <Reminder interruptValue={checkpoint.interruptValue} onResume={handleResume} />;
    case 'research':
    case 'search':
    case 'report':
      return <ResearchNode nodeState={node.state} />;
    // 添加新节点类型的渲染逻辑
    default:
      return null;
  }
}
```

## 5. 后端图结构规范

### 5.1 节点函数

- 节点函数应使用适当的参数来处理状态
- 消息处理必须在与前端匹配的节点中进行

```python
async def agent(state):  # 注意：这里使用'agent'替代了原来的'chatbot'
    # 处理消息并返回结果
    return {"messages": [...]}  # 必须包含messages字段
```

### 5.2 图构建

- 图必须包含与前端匹配的节点，用于处理消息
- 必须实现`get_graph()`函数返回编译好的图实例

```python
def get_graph():
    """返回编译好的LangGraph实例"""
    builder = StateGraph()
    builder.add_node("agent", agent)  # 注意：这里使用'agent'替代了原来的'chatbot'
    # 添加边和其他节点
    graph = builder.compile(checkpointer=MemorySaver())
    return graph
```

## 6. 开发流程

### 6.1 新建Web Agent流程

1. 在`examples/web_agents/`下创建新的Agent目录
2. 创建`graph.py`文件，实现Agent的图结构，确保节点名称与前端`renderNode`函数中的case语句匹配
3. 在`web/app/chat/[id]/agent-types.ts`中添加Agent所需的状态接口
4. 在`web/app/chat/[id]/components/`下创建Agent的组件
5. 在`web/app/chat/[id]/page.tsx`的`renderNode`函数中注册Agent的节点组件（如果使用新的节点名称）

### 6.2 测试验证

在提交代码前，必须进行以下测试：

1. 确认后端图结构中的节点名称与前端`renderNode`函数中的case语句匹配
2. 验证前端组件能正确渲染不同类型的节点
3. 检查状态字段名称与前端组件期望的字段名称一致

## 7. 常见问题与解决方案

### 7.1 前端不显示消息问题

如果前端不显示消息内容，请检查：

1. 后端图结构中的节点名称是否与前端`renderNode`函数中的case语句匹配
2. 前端`renderNode`函数是否正确处理了对应的节点名称
3. 消息是否正确包含在state的messages字段中

### 7.2 状态更新不生效

确保状态更新时，字段名称与前端期望的字段名称一致，并且数据结构符合前端组件的预期。

### 7.3 添加新节点类型

如果需要添加新的节点类型，必须：

1. 在后端图结构中定义新节点
2. 在前端`page.tsx`的`renderNode`函数中添加对应的case语句
3. 创建新节点对应的前端组件
4. 在`agent-types.ts`中添加新节点所需的状态接口

---

遵循本规范可以有效避免前后端不一致导致的显示问题，提高Web Agent的开发效率和质量。