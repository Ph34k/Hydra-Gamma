from typing import Any, List, Optional
from pydantic import Field

from app.tool.base import BaseTool
from app.memory.semantic import SemanticMemory

class MemorySearchTool(BaseTool):
    name: str = "memory_search"
    description: str = (
        "Search the agent's long-term semantic memory for information relevant to the query. "
        "Use this tool to recall facts, documentation, or past experiences."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query or description of the information needed.",
            },
            "n_results": {
                "type": "integer",
                "description": "Number of results to retrieve (default: 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    # We use a private field for the memory instance
    _memory: Optional[SemanticMemory] = None

    def set_memory(self, memory: SemanticMemory):
        """Inject an existing SemanticMemory instance."""
        self._memory = memory

    @property
    def memory(self) -> SemanticMemory:
        if self._memory is None:
            # Fallback to creating a new one if not injected (e.g. unit tests)
            # But this warns about inefficiency
            self._memory = SemanticMemory()
        return self._memory

    async def execute(self, query: str, n_results: int = 5) -> Any:
        results = self.memory.search(query, n_results)
        if not results:
            return "No relevant information found in memory."

        formatted_output = "Found relevant memories:\n"
        for res in results:
            formatted_output += f"- {res['content'][:200]}... (Relevance: {res['distance']})\n"
            # Include source if available
            if res.get('metadata') and 'source' in res['metadata']:
                 formatted_output += f"  Source: {res['metadata']['source']}\n"

        return formatted_output
