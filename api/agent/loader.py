# Agent Loader Module
# This module is responsible for loading agents from the web_agents directory

import importlib
import os
import sys
from typing import Dict, Optional
from langgraph.graph import StateGraph

# Add examples directory to Python path to allow importing web_agents
examples_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'examples')
if examples_path not in sys.path:
    sys.path.append(examples_path)


def list_available_agents() -> Dict[str, str]:
    """List all available agents in the web_agents directory
    
    Returns:
        Dict[str, str]: A dictionary mapping agent names to their descriptions
    """
    agents = {}
    web_agents_dir = os.path.join(examples_path, 'web_agents')
    
    # Check if web_agents directory exists
    if not os.path.exists(web_agents_dir) or not os.path.isdir(web_agents_dir):
        return agents
    
    # Iterate through subdirectories in web_agents
    for item in os.listdir(web_agents_dir):
        agent_dir = os.path.join(web_agents_dir, item)
        
        # Skip non-directories and special directories
        if not os.path.isdir(agent_dir) or item.startswith('__') or item.startswith('.'):
            continue
        
        # Check if the directory contains an __init__.py file with get_graph function
        init_file = os.path.join(agent_dir, '__init__.py')
        if os.path.exists(init_file):
            # Try to get description from README.md
            readme_file = os.path.join(agent_dir, 'README.md')
            description = item  # Default description is the directory name
            
            if os.path.exists(readme_file):
                try:
                    with open(readme_file, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            description = first_line[2:]
                except Exception:
                    pass
            
            agents[item] = description
    
    return agents


def load_agent(agent_name: str) -> Optional[StateGraph]:
    """Load an agent from the web_agents directory
    
    Args:
        agent_name (str): The name of the agent to load
        
    Returns:
        Optional[StateGraph]: The compiled graph for the agent, or None if the agent could not be loaded
    """
    try:
        # Import the agent module
        module = importlib.import_module(f'web_agents.{agent_name}')
        
        # Check if the module has a get_graph function
        if hasattr(module, 'get_graph'):
            # Call the get_graph function to get the compiled graph
            return module.get_graph()
        else:
            print(f"Error: Agent '{agent_name}' does not have a get_graph function")
            return None
    except ImportError as e:
        print(f"Error importing agent '{agent_name}': {e}")
        return None
    except Exception as e:
        print(f"Error loading agent '{agent_name}': {e}")
        return None


# Default agent to use if none is specified
DEFAULT_AGENT = 'research_assistant'
# DEFAULT_AGENT = 'weather_agent'


def get_default_agent() -> Optional[StateGraph]:
    """Get the default agent
    
    Returns:
        Optional[StateGraph]: The compiled graph for the default agent, or None if it could not be loaded
    """
    return load_agent(DEFAULT_AGENT)