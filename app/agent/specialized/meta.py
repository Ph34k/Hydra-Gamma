from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import META_PROGRAMMER_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.file_tool import FileTool
from app.tool.shell_tool import ShellTool
from app.tool.git_tool import GitTool

class MetaProgrammerAgent(Manus):
    """
    The Meta-Programmer Agent (Chapter 49).
    Responsible for self-evolution, performance analysis, and code improvement.
    """
    name: str = "meta_programmer_agent"
    description: str = "An advanced agent that can analyze and improve its own codebase."

    system_prompt: str = META_PROGRAMMER_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            FileTool(),
            ShellTool(),
            GitTool(),
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
