### LangGraph 如何使用的关键内容

1. **LangGraph平台介绍**:
   - LangGraph 是一个开源库，旨在帮助开发者构建可控的、适应性的 AI 代理。
   - 提供可靠性和可控性的功能，包括与人类的交互和中介检查等。
   - 网站：[LangGraph](https://langchain-ai.github.io/langgraph/how-tos/)

2. **功能和特性**:
   - **低级别和可扩展**: 提供构建自定义代理所需的底层原语，不会限制自定义。
   - **流式支持**: 支持逐步流式传输和实时显示代理的推理和行动。

3. **使用示例**:
   - **创建 ReAct 代理的示例代码**:
     ```python
     from langgraph.prebuilt import create_react_agent

     def search(query: str):
         """Call to surf the web."""
         if "sf" in query.lower() or "san francisco" in query.lower():
             return "It's 60 degrees and foggy."
         return "It's 90 degrees and sunny."

     agent = create_react_agent("anthropic:claude-3-7-sonnet-latest", tools=[search])
     agent.invoke({"messages": [{"role": "user", "content": "what is the weather in sf"}]})
     ```

4. **快速入门和教程**:
   - LangGraph 提供了多种教程，帮助用户快速上手，包括常见的代理工作流示例。
   - 相关链接：
     - [快速入门](https://langchain-ai.github.io/langgraph/tutorials/introduction/)
     - [教程](https://langchain-ai.github.io/langgraph/tutorials/)
     - [模板](https://langchain-ai.github.io/langgraph/concepts/template_applications/)
     - [API 参考](https://langchain-ai.github.io/langgraph/reference/graphs/)

5. **其他资源**:
   - LangGraph 的学习资源和课程有助于新用户快速掌握基本概念。
   - 相关链接：[LangChain Academy](https://academy.langchain.com/courses/intro-to-langgraph)

### 下步行动
如果需要更深入的内容提取或分析特定模块，请告知我所需的具体信息或方向，我将进行相应的查找和分析。