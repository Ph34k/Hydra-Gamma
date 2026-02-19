from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import SALES_AGENT_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.search_tool import SearchTool
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_tool import FileTool

class SalesAgent(Manus):
    """
    A specialized agent for sales and CRM management (Chapter 43).
    Focuses on prospecting, qualification, and professional communication.
    """
    name: str = "sales_agent"
    description: str = "A professional sales agent focused on lead generation and CRM management."

    system_prompt: str = SALES_AGENT_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            SearchTool(),
            BrowserUseTool(),
            FileTool(), # For drafting emails
            Terminate()
        )
    )
    # Note: MCP tools (CRM) are loaded dynamically by Manus base class

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
