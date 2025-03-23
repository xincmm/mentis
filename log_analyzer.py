import re
import sys
import argparse
from collections import defaultdict
import json

def parse_log_file(file_path):
    """Parse the execution log file and extract agent interactions."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract different sections of the log
    sections = content.split("================================ Human Message =================================")
    if len(sections) > 1:
        main_content = sections[1]  # Skip header
    else:
        main_content = content
    
    # Extract messages
    messages = []
    
    # Pattern for AI messages
    ai_pattern = r"================================== Ai Message ==================================\nName: (\w+)\n\n(.*?)(?=(==================================|$))"
    ai_matches = re.finditer(ai_pattern, main_content, re.DOTALL)
    
    for match in ai_matches:
        agent_name = match.group(1)
        message_content = match.group(2).strip()
        
        # Check if message has tool calls
        tool_calls = []
        tool_call_pattern = r"Tool Calls:\n(.*?)(?=\n==================================|$)"
        tool_call_match = re.search(tool_call_pattern, message_content, re.DOTALL)
        if tool_call_match:
            # Extract tool calls
            tool_calls_text = tool_call_match.group(1)
            tool_call_entries = re.findall(r"  (\w+) \(([^)]+)\)", tool_calls_text)
            tool_calls = [{"name": name, "id": call_id} for name, call_id in tool_call_entries]
            
            # Remove tool calls from the message content
            message_content = re.sub(r"Tool Calls:.*?(?=\n==================================|$)", "", message_content, flags=re.DOTALL).strip()
        
        messages.append({
            "role": "agent",
            "agent": agent_name,
            "content": message_content,
            "tool_calls": tool_calls
        })
    
    # Pattern for Tool messages
    tool_pattern = r"================================= Tool Message =================================\nName: (\w+)\n\n(.*?)(?=(==================================|$))"
    tool_matches = re.finditer(tool_pattern, main_content, re.DOTALL)
    
    for match in tool_matches:
        tool_name = match.group(1)
        tool_content = match.group(2).strip()
        
        messages.append({
            "role": "tool",
            "tool": tool_name,
            "content": tool_content
        })
    
    # Sort messages by their position in the log
    messages.sort(key=lambda x: main_content.find(x["content"]))
    
    return messages

def analyze_agent_interactions(messages):
    """Analyze the interactions between agents."""
    interactions = []
    current_sender = None
    tool_call_map = {}
    
    for i, msg in enumerate(messages):
        if msg["role"] == "agent":
            current_sender = msg["agent"]
            # Check if this agent is using tool calls
            for tool_call in msg.get("tool_calls", []):
                tool_name = tool_call["name"]
                tool_id = tool_call["id"]
                tool_call_map[tool_id] = {
                    "sender": current_sender,
                    "tool": tool_name
                }
                interactions.append({
                    "step": i,
                    "from": current_sender,
                    "to": f"SYSTEM ({tool_name})",
                    "action": f"Called tool {tool_name}",
                    "content": f"Tool call ID: {tool_id}"
                })
        elif msg["role"] == "tool":
            # Find which agent invoked this tool
            for prev_msg in reversed(messages[:i]):
                if prev_msg["role"] == "agent" and any(tc["name"] == msg["tool"] for tc in prev_msg.get("tool_calls", [])):
                    sender = prev_msg["agent"]
                    break
            else:
                sender = "SYSTEM"
            
            interactions.append({
                "step": i,
                "from": f"SYSTEM ({msg['tool']})",
                "to": sender,
                "action": f"Tool response",
                "content": msg["content"]
            })
    
    return interactions

def visualize_interactions(interactions):
    """Visualize the interactions between agents."""
    print("\n" + "="*100)
    print(" "*40 + "AGENT INTERACTIONS SUMMARY")
    print("="*100 + "\n")
    
    for idx, interaction in enumerate(interactions):
        print(f"[{idx+1}] {interaction['from']} → {interaction['to']}")
        print(f"    Action: {interaction['action']}")
        content = interaction['content']
        if len(content) > 100:
            content = content[:97] + "..."
        print(f"    Content: {content}\n")

def visualize_conversation_flow(messages):
    """Visualize the conversation flow between agents."""
    print("\n" + "="*100)
    print(" "*40 + "CONVERSATION FLOW")
    print("="*100 + "\n")
    
    for idx, message in enumerate(messages):
        if message["role"] == "agent":
            agent_name = message["agent"]
            print(f"[{idx+1}] Agent: {agent_name}")
            content = message["content"]
            if len(content) > 150:
                content = content[:147] + "..."
            print(f"    Content: {content}")
            
            if message.get("tool_calls"):
                tools = ", ".join([tc["name"] for tc in message["tool_calls"]])
                print(f"    Tools Called: {tools}")
        else:
            print(f"[{idx+1}] Tool: {message['tool']}")
            content = message["content"]
            if len(content) > 100:
                content = content[:97] + "..."
            print(f"    Response: {content}")
        print()

def main():
    parser = argparse.ArgumentParser(description='Analyze Mentis execution logs.')
    parser.add_argument('log_file', help='Path to the log file')
    parser.add_argument('--format', choices=['interactions', 'flow', 'all'], default='all',
                      help='Output format: interactions, flow, or all')
    
    args = parser.parse_args()
    
    try:
        messages = parse_log_file(args.log_file)
        interactions = analyze_agent_interactions(messages)
        
        if args.format in ['interactions', 'all']:
            visualize_interactions(interactions)
        
        if args.format in ['flow', 'all']:
            visualize_conversation_flow(messages)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
