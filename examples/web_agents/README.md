# Web Agents

这个目录包含可以通过web界面加载的代理示例。每个子目录代表一个独立的代理实现，可以被server.py动态加载。

## 目录结构

每个代理应遵循以下结构：

```
agent_name/
  __init__.py  # 包含get_graph()函数，返回编译好的LangGraph
  README.md    # 代理的说明文档
```

## 接口规范

每个代理必须实现以下接口：

```python
def get_graph():
    """返回编译好的LangGraph实例"""
    # 构建并返回图
    return compiled_graph
```