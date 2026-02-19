from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import CODING_AGENT_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.file_tool import FileTool
from app.tool.shell_tool import ShellTool
from app.tool.git_tool import GitTool


class CodingAgent(Manus):
    """
    A specialized agent for software engineering tasks (Chapter 41).
    Focuses on TDD, atomic commits, and robust file editing.
    """
    name: str = "coding_agent"
    description: str = "An expert software engineer agent focused on coding, testing, and git operations."

    system_prompt: str = CODING_AGENT_PROMPT

    # Coding agent needs specific tools
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            FileTool(),
            ShellTool(),
            GitTool(),
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def think(self) -> bool:
        # Override if specific reasoning logic is needed beyond Manus base
        return await super().think()
