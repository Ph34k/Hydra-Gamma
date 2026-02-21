from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import RESEARCH_AGENT_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.search_tool import SearchTool
from app.tool.browser_tool import BrowserTool
from app.tool.document_processor import DocumentProcessor
from app.tool.file_tool import FileTool

class ResearchAgent(Manus):
    """
    A specialized agent for research and analysis (Chapter 42).
    Focuses on information gathering, synthesis, and grounding.
    """
    name: str = "research_agent"
    description: str = "An expert analyst agent focused on deep research and information synthesis."

    system_prompt: str = RESEARCH_AGENT_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            SearchTool(),
            BrowserTool(),
            DocumentProcessor(),
            FileTool(), # Needed for saving reports
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
