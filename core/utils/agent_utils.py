import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, ToolMessage

def log_agent_actions(state: Dict[str, Any]) -> None:
    """记录Agent的思考过程和行动
    
    这个函数用于在控制台打印Agent的思考过程、工具调用和工具返回结果，
    便于观察和调试Agent的行为。
    
    Args:
        state: 包含消息历史的状态字典
    """
    print("\n" + "=" * 50)
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
            # 只打印结果的前500个字符，避免输出过长
            content = latest_message.content
            if len(content) > 500:
                content = content[:500] + "... (更多内容省略)"
            print(f"- 结果: {content}")
    
    print("=" * 50)

def save_agent_graph(agent, caller_file_path: str = None) -> str:
    """保存Agent的图表到指定目录
    
    这个函数用于生成Agent的图表并保存到examples/graphs目录下，
    文件名与调用者的文件名保持一致（不含扩展名）。
    
    Args:
        agent: Agent对象，必须有get_graph方法
        caller_file_path: 调用者的文件路径，如果为None则使用调用栈获取
        
    Returns:
        str: 保存的图表路径
    """
    import inspect
    import os
    
    # 如果没有提供调用者文件路径，则从调用栈获取
    if caller_file_path is None:
        # 获取调用者的栈帧
        frame = inspect.currentframe().f_back
        caller_file_path = frame.f_code.co_filename
    
    # 获取图对象
    graph = agent.get_graph()
    
    # 获取当前文件名（不含路径和扩展名）
    current_file = os.path.basename(caller_file_path)
    file_name_without_ext = os.path.splitext(current_file)[0]
    
    # 确定graphs目录路径
    # 如果调用者在examples目录下，则使用examples/graphs
    # 否则在调用者所在目录创建graphs子目录
    if 'examples' in caller_file_path:
        base_dir = os.path.dirname(os.path.dirname(caller_file_path))
        graph_dir = os.path.join(base_dir, "examples", "graphs")
    else:
        graph_dir = os.path.join(os.path.dirname(caller_file_path), "graphs")
    
    # 确保graphs目录存在
    os.makedirs(graph_dir, exist_ok=True)
    
    # 生成与文件名一致的图片名，并保存
    image_data = graph.draw_mermaid_png()
    graph_path = os.path.join(graph_dir, f"{file_name_without_ext}.png")
    
    # 保存图片（如果已存在则覆盖）
    with open(graph_path, "wb") as f:
        f.write(image_data)
    
    print(f"Image saved as {graph_path}")
    return graph_path