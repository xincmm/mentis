"""FireCrawl tools for the multi-agent architecture.

This module contains tools for crawling and scraping web content using the FireCrawl API,
providing agents with the ability to extract information from websites.
"""
from typing import Dict, List, Literal, Optional, Tuple, Type, Union, Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_community.document_loaders import FireCrawlLoader


class FireCrawlInput(BaseModel):
    """Input for the FireCrawl tool."""

    url: str = Field(description="URL to crawl or scrape")
    mode: str = Field(
        default="crawl",
        description="Mode to run the loader in ('crawl', 'scrape', or 'map')",
    )


class FireCrawlTool(BaseTool):  # type: ignore[override, override]
    """Tool that uses FireCrawl API to crawl or scrape web content.

    Setup:
        Install ``langchain-community`` and set environment variable ``FIRECRAWL_API_KEY``.

        .. code-block:: bash

            pip install -U langchain-community
            export FIRECRAWL_API_KEY="your-api-key"

    Instantiate:

        .. code-block:: python

            from mentis.core.tools import FireCrawlTool

            tool = FireCrawlTool(
                api_key="your-api-key",  # Optional, can use env var
                mode="crawl",  # Default mode
                params={"max_pages": 10}  # Optional additional parameters
            )

    Invoke directly with args:

        .. code-block:: python

            tool.invoke({'url': 'https://example.com'})

    """

    name: str = "firecrawl_tool"
    description: str = (
        "A web crawler and scraper that extracts content from websites. "
        "Useful for when you need to analyze the content of a specific website or webpage. "
        "Input should be a URL to crawl or scrape."
    )
    args_schema: Type[BaseModel] = FireCrawlInput
    """The tool input schema."""

    api_key: Optional[str] = None
    """FireCrawl API key (or read from env FIRECRAWL_API_KEY)"""
    api_url: Optional[str] = None
    """FireCrawl API URL (default is https://api.firecrawl.dev)"""
    mode: str = "crawl"
    """Mode to run the loader in ('crawl', 'scrape', or 'map')"""
    params: Dict[str, Any] = Field(default_factory=dict)
    """Additional parameters for FireCrawl API"""
    response_format: Literal["content_and_artifact"] = "content_and_artifact"

    def _run(
        self,
        url: str,
        mode: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict]:
        """Use the tool."""
        try:
            # Use the provided mode or fall back to the default
            current_mode = mode or self.mode
            
            # Initialize the loader
            loader = FireCrawlLoader(
                url=url,
                api_key=self.api_key,
                api_url=self.api_url,
                mode=current_mode,
                params=self.params,
            )
            
            # Load the documents
            docs = loader.load()
            
            # Format the results
            results = [{
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in docs]
            
            # Create artifact with additional metadata
            artifact = {
                "url": url,
                "mode": current_mode,
                "document_count": len(docs),
                "results": results
            }
            
            return results, artifact
        except Exception as e:
            return repr(e), {}

    async def _arun(
        self,
        url: str,
        mode: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict]:
        """Use the tool asynchronously."""
        try:
            # Use the provided mode or fall back to the default
            current_mode = mode or self.mode
            
            # Initialize the loader
            loader = FireCrawlLoader(
                url=url,
                api_key=self.api_key,
                api_url=self.api_url,
                mode=current_mode,
                params=self.params,
            )
            
            # Load the documents asynchronously
            docs = await loader.aload()
            
            # Format the results
            results = [{
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in docs]
            
            # Create artifact with additional metadata
            artifact = {
                "url": url,
                "mode": current_mode,
                "document_count": len(docs),
                "results": results
            }
            
            return results, artifact
        except Exception as e:
            return repr(e), {}