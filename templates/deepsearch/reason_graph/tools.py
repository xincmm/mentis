import os
import json
import time
import re
import asyncio # If using asyncio.to_thread or similar async utilities
from datetime import datetime
from typing import Optional, List, Literal, Dict, Any
from dotenv import load_dotenv

# --- LangChain/LLM Imports ---
# Replace with your specific LLM provider if not OpenAI
from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

# --- External Service Clients ---
from tavily import AsyncTavilyClient
from exa_py import Exa

# --- Internal Imports ---
from reason_graph.schemas import SearchResultItem, SearchQuery, StreamUpdate, StreamUpdateData # Relative imports
from reason_graph.state import ResearchState # Needed for add_stream_update type hint

# Load API keys
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Or your LLM key env var

# Initialize clients
# Ensure you have a model capable of reliable structured output / function calling
# Using gpt-4o as an example, adjust model name as needed
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY) 
llm_creative = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=OPENAI_API_KEY) # For analysis

tavily_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
exa_client = Exa(api_key=EXA_API_KEY)

# --- Tool Helper Functions ---

def generate_structured_output(model, schema: BaseModel, prompt: str, system_message: str = ""):
    """Uses langchain `.with_structured_output` for reliable JSON generation."""
    structured_llm = model.with_structured_output(schema)
    messages = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))
    response = structured_llm.invoke(messages)
    return response

def extract_tweet_id(url: str) -> Optional[str]:
    """Extracts tweet ID from twitter.com or x.com URLs."""
    match = re.search(r"(?:twitter\.com|x\.com)\/\w+\/status\/(\d+)", url)
    return match.group(1) if match else None

# Tool Wrappers (can be formal LangChain tools or just functions used in nodes)
async def perform_web_search(query: str, depth: Literal['basic', 'advanced'], priority: int) -> List[SearchResultItem]:
    max_results = min(max(1, 6 - priority), 10) # Clamp results based on priority
    try:
        # Tavily expects 'basic' or 'advanced' for search_depth
        search_depth = depth if depth in ['basic', 'advanced'] else 'basic' 
        response = await tavily_client.search(
            query=query,
            search_depth=search_depth,
            include_answer=False, # Original code used true, but only mapped results. Adjust if answer is needed.
            max_results=max_results
        )
        # Ensure response['results'] exists and is a list
        results_list = response.get('results', []) if isinstance(response, dict) else []
        
        formatted_results = [
            SearchResultItem(
                source='web',
                title=r.get('title', ''),
                url=r.get('url', ''),
                content=r.get('content', '')
            ) for r in results_list if isinstance(r, dict)
        ]
        return formatted_results
    except Exception as e:
        print(f"Error during Tavily search for '{query}': {e}")
        return []


async def perform_academic_search(query: str, priority: int) -> List[SearchResultItem]:
    num_results = min(max(1, 6 - priority), 5)
    try:
        # Note: Exa's search_and_contents is synchronous in the current exa-py.
        # If async is strictly needed, consider wrapping in asyncio.to_thread
        # or check for an updated async method in exa-py.
        # Using synchronous call here for simplicity based on current lib.
        response = exa_client.search_and_contents(
            query,
            type='auto', # 'auto' finds relevant academic papers
            num_results=num_results,
            # category='research paper', # Exa doesn't have 'category' - use type or text filtering if needed
            highlights=True, # Get highlights which might be similar to summary intent
            use_autoprompt=True # Let Exa optimize the query
        )
        formatted_results = [
            SearchResultItem(
                source='academic',
                title=r.title or '',
                url=r.url or '',
                # Using highlights as content proxy, adjust if full text or specific summary is needed/available
                content=r.highlights[0] if r.highlights else r.text or '' 
            ) for r in response.results
        ]
        return formatted_results
    except Exception as e:
        print(f"Error during Exa academic search for '{query}': {e}")
        return []

async def perform_x_search(query_obj: SearchQuery) -> List[SearchResultItem]:
    num_results = max(1, query_obj.priority) # Original code used priority directly
    try:
        # Using synchronous call here for simplicity based on current lib.
        response = exa_client.search_and_contents(
            query_obj.query,
            type='neural', # Neural is often better for specific platforms like Twitter
            num_results=num_results,
            include_domains=['twitter.com', 'x.com'],
            text=True, # Ensure text content is included
            use_autoprompt=True
        )
        processed_tweets = []
        for r in response.results:
            tweet_id = extract_tweet_id(r.url)
            if tweet_id:
                processed_tweets.append(
                    SearchResultItem(
                        source='x',
                        title=r.title or r.author or 'Tweet',
                        url=r.url,
                        content=r.text or '',
                        tweetId=tweet_id
                    )
                )
        return processed_tweets
    except Exception as e:
        print(f"Error during Exa X search for '{query_obj.query}': {e}")
        return []

# Helper to add stream updates consistently
def add_stream_update(state: ResearchState, data_dict: Dict[str, Any]) -> List[StreamUpdate]:
    """Creates and returns a list containing a single StreamUpdate."""
    # Ensure required fields are present
    data_dict.setdefault('timestamp', time.time())
    data_dict.setdefault('overwrite', False) # Default overwrite to False unless specified
    
    try:
        update_data = StreamUpdateData(**data_dict)
        stream_update = StreamUpdate(type='research_update', data=update_data)
        return [stream_update] # Return as a list for Annotated add
    except Exception as e:
        print(f"Error creating stream update for ID {data_dict.get('id', 'N/A')}: {e}")
        print(f"Data causing error: {data_dict}")
        # Return an empty list or a placeholder error update if preferred
        error_update_data = StreamUpdateData(
            id=data_dict.get('id', 'error-id'),
            type='error',
            status='completed', # Or 'failed'
            title='Error generating stream update',
            message=str(e),
            timestamp=time.time()
        )
        stream_update = StreamUpdate(type='research_update', data=error_update_data)
        return [stream_update]