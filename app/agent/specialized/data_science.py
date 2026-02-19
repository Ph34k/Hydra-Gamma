from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import DATA_SCIENCE_AGENT_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.file_tool import FileTool
from app.tool.python_execute import PythonExecute
from app.tool.media_generation_tool import MediaGenerationTool
from app.tool.shell_tool import ShellTool

class DataScienceAgent(Manus):
    """
    A specialized agent for data analysis and visualization (Chapter 45).
    Focuses on EDA, Python scripting, and visual reporting.
    """
    name: str = "data_science_agent"
    description: str = "An analytical agent focused on data science, visualization, and interpretation."

    system_prompt: str = DATA_SCIENCE_AGENT_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            FileTool(),
            ShellTool(), # For package installation
            PythonExecute(),
            MediaGenerationTool(),
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
