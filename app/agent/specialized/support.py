from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import SUPPORT_AGENT_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.memory import MemorySearchTool
from app.tool.file_tool import FileTool
from app.tool.search_tool import SearchTool # Sometimes needed for external docs

class SupportAgent(Manus):
    """
    A specialized agent for customer support (Chapter 44).
    Focuses on empathy, knowledge retrieval (RAG), and issue resolution.
    """
    name: str = "support_agent"
    description: str = "An empathetic support agent focused on ticket resolution using RAG."

    system_prompt: str = SUPPORT_AGENT_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            MemorySearchTool(),
            SearchTool(),
            FileTool(), # For logs or internal docs
            Terminate()
        )
    )
    # MCP tools (Ticket System) are loaded dynamically by Manus base class

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
