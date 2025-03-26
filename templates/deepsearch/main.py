# main.py
import asyncio
import json
import os
import re # 用于文件名清理
from datetime import datetime # 用于文件名时间戳
from typing import Literal, List

# --- Internal Imports ---
from reason_graph.graph import app
from reason_graph.state import ResearchState
# 导入需要用到的 Pydantic 模型
from reason_graph.schemas import StreamUpdate, FinalSynthesisResult, KeyFinding 

# --- Helper Functions ---

def slugify(text: str) -> str:
    """将文本转换为安全的文件名部分 (简化版)."""
    text = text.lower()
    # 移除或替换非法字符
    text = re.sub(r'\s+', '_', text) # 空格替换为下划线
    text = re.sub(r'[^\w\-]+', '', text) # 移除所有非字母、数字、下划线、连字符
    text = text.strip('_')
    return text[:100] # 限制长度

def format_report_to_markdown(topic: str, synthesis_result: FinalSynthesisResult) -> str:
    """将 FinalSynthesisResult 对象格式化为 Markdown 字符串."""
    lines = []
    lines.append(f"# Research Report: {topic}\n")

    if synthesis_result.key_findings:
        lines.append("## Key Findings\n")
        for i, finding in enumerate(synthesis_result.key_findings):
            lines.append(f"### Finding {i+1}: {finding.finding}\n")
            lines.append(f"- **Confidence:** {finding.confidence:.2f}") # 格式化为两位小数
            if finding.supporting_evidence:
                lines.append("- **Supporting Evidence:**")
                for evidence in finding.supporting_evidence:
                    lines.append(f"  - {evidence}")
            lines.append("\n") # 添加空行分隔

    if synthesis_result.remaining_uncertainties:
        lines.append("## Remaining Uncertainties\n")
        for uncertainty in synthesis_result.remaining_uncertainties:
            lines.append(f"- {uncertainty}")
        lines.append("\n")

    return "\n".join(lines)

async def run_research(topic: str, depth: Literal['basic', 'advanced'] = 'basic'):
    initial_state: ResearchState = {
        "topic": topic,
        "depth": depth,
        # ... (其他初始状态字段保持不变) ...
        "stream_updates": [],
        # ...
    }

    print("--- Starting Research Graph ---")
    print(f"Initial State (partial): {{'topic': '{topic}', 'depth': '{depth}'}}")
    print("-" * 30)

    processed_updates_count = 0
    config = {"recursion_limit": 50} # 保持递归限制

    # --- Streaming Execution ---
    async for current_state in app.astream(
        initial_state,
        config=config,
        stream_mode="values"
    ):
        all_current_updates: List[StreamUpdate] = current_state.get("stream_updates", [])
        new_updates_count = len(all_current_updates) - processed_updates_count
        if new_updates_count > 0:
            newly_added_updates = all_current_updates[processed_updates_count:]
            for update in newly_added_updates:
                try:
                    print(f"--- STREAM UPDATE (ID: {update.data.id} | Status: {update.data.status}) ---")
                    print(json.dumps(update.model_dump(), indent=2, default=str)) # 使用 model_dump()
                    print("-" * 30)
                except AttributeError as e:
                    print(f"--- Error processing stream update: {e} ---")
                    print(f"Problematic update data: {update}")
                    print("-" * 30)
            processed_updates_count = len(all_current_updates)

        # --- Optional Current State Summary (保持不变) ---
        print(f"--- Current State Summary ---")
        print(f"  Search steps completed: {current_state.get('current_search_step_index', 0)}")
        print(f"  Analysis steps completed: {current_state.get('current_analysis_step_index', 0)}")
        print(f"  Total results so far: {len(current_state.get('search_results', []))}")
        print("-" * 30)


    # --- Get Final State ---
    print("\n--- Graph Execution Finished ---")
    final_state = await app.ainvoke(initial_state, config=config)

   # --- Get Final State ---
    print("\n--- Graph Execution Finished ---")
    # It's generally better to rely on the state from the stream's last value 
    # if using stream_mode="values", but ainvoke is fine too.
    # Let's assume current_state holds the final state after the loop finishes
    final_state = current_state # Or use await app.ainvoke(initial_state, config=config)
    
    # --- Print Final State Summary ---
    print("\n--- FINAL RESEARCH STATE (Summary) ---")
    # ... (print topic, depth, plan, results, gap analysis - same as before) ...

    # --- Check for Final Report Markdown ---
    final_markdown = final_state.get('final_report_markdown')
    
    if final_markdown and "Report Generation Failed" not in final_markdown: # Check if generation succeeded
        # Print summary info about synthesis if available (might be redundant if printed elsewhere)
        final_synthesis_data = final_state.get('final_synthesis')
        if final_synthesis_data:
             print("\nFinal Synthesis Summary:")
             print(f"- {len(final_synthesis_data.key_findings)} Key Findings")
             print(f"- {len(final_synthesis_data.remaining_uncertainties)} Remaining Uncertainties")
             
        print("\n--- Saving Final Report to Markdown ---")
        try:
            # Content is already formatted markdown
            markdown_content = final_markdown
            
            # Generate filename (same logic as before)
            topic_slug = slugify(final_state['topic'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_report_{topic_slug}_{timestamp}.md"
            filepath = filename 

            # Save file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"Successfully saved report to: {filepath}")

        except Exception as e:
            print(f"Error saving report to Markdown: {e}")
    elif final_markdown: # Handle case where generation failed and put error in markdown
         print("\n--- Final Report Generation Failed ---")
         print(final_markdown) # Print the error message from the markdown content
         print("Report not saved.")
    else:
        # If no final_report_markdown field (e.g., basic depth, or error before report node)
        print("\nFinal Report: Not generated (Flow did not reach or complete report generation step).")

    print("\n--- END OF RESEARCH ---")
    return final_state

# --- Main Execution Block ---
async def main():
     topic = "Impact of remote work on employee productivity and well-being"
     await run_research(topic, depth='advanced')

if __name__ == "__main__":
    asyncio.run(main())