import asyncio
import os
from typing import List, Optional

import requests
from pydantic import BaseModel, Field, PrivateAttr

from app.llm import LLM
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


class SearchTool(BaseTool):
    name: str = "search_tool"
    description: str = """
    Advanced search tool with query expansion and image downloading.
    Supports multiple search types: INFO, IMAGE, NEWS, RESEARCH.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "download_image", "expand_query"],
                "description": "Action to perform.",
            },
            "queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of search queries.",
            },
            "type": {
                "type": "string",
                "enum": ["INFO", "IMAGE", "NEWS", "RESEARCH"],
                "default": "INFO",
                "description": "Type of search.",
            },
            "url": {
                "type": "string",
                "description": "URL of the image to download.",
            },
            "query": {
                "type": "string",
                "description": "Initial query for expansion.",
            },
        },
        "required": ["action"],
    }

    _web_search: WebSearch = PrivateAttr(default_factory=WebSearch)
    llm: Optional[LLM] = Field(default_factory=LLM)

    async def execute(
        self,
        action: str,
        queries: Optional[List[str]] = None,
        type: str = "INFO",
        url: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "search":
                if not queries:
                    return ToolResult(error="Queries list required for search")
                return await self._search(queries, type)
            elif action == "download_image":
                if not url:
                    return ToolResult(error="URL required for download_image")
                return await self._download_image(url)
            elif action == "expand_query":
                if not query:
                    return ToolResult(error="Query required for expand_query")
                return await self._expand_query(query)
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"SearchTool error: {e}")
            return ToolResult(error=str(e))

    async def _search(self, queries: List[str], type: str) -> ToolResult:
        results: List[SearchResult] = []
        # We use the existing WebSearch tool for each query
        # Parallel execution would be better
        tasks = []
        for q in queries:
            tasks.append(self._web_search.execute(query=q, num_results=3)) # Limit results per query

        search_responses = await asyncio.gather(*tasks)

        for response in search_responses:
            if response.error:
                continue
            for item in response.results:
                results.append(SearchResult(
                    title=item.title,
                    snippet=item.description,
                    url=item.url
                ))

        # Deduplicate by URL
        unique_results = {r.url: r for r in results}.values()

        return ToolResult(output=str([r.model_dump() for r in unique_results]))

    def _download_sync(self, url: str, path: str):
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True, None
            return False, response.status_code
        except Exception as e:
            return False, str(e)

    async def _download_image(self, url: str) -> ToolResult:
        try:
            filename = url.split("/")[-1] or "image.jpg"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            path = os.path.join(os.getcwd(), "downloads", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)

            loop = asyncio.get_event_loop()
            success, error_code = await loop.run_in_executor(None, self._download_sync, url, path)

            if success:
                return ToolResult(output=f"Image saved to {path}")
            else:
                return ToolResult(error=f"Failed to download image: {error_code}")
        except Exception as e:
            return ToolResult(error=f"Download failed: {str(e)}")

    async def _expand_query(self, query: str) -> ToolResult:
        prompt = f"""
        Generate 3 search query variants for the following topic to cover different angles (e.g., technical, general, news).
        Topic: "{query}"
        Return only the queries, one per line.
        """
        try:
            response = await self.llm.ask([{"role": "user", "content": prompt}])
            variants = [line.strip() for line in response.split("\n") if line.strip()]
            return ToolResult(output=str(variants))
        except Exception as e:
            return ToolResult(error=f"Query expansion failed: {str(e)}")
