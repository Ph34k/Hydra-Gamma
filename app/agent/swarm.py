from typing import List

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import MULTI_AGENT_ORCHESTRATOR_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.delegate_tool import DelegateTool
from app.tool.file_tool import FileTool # Useful for reading high level docs

class SwarmOrchestrator(Manus):
    """
    The Orchestrator agent for Multi-Agent Swarms (Chapter 48).
    Responsible for task decomposition and delegation.
    """
    name: str = "swarm_orchestrator"
    description: str = "The central orchestrator that manages specialized agents to solve complex tasks."

    system_prompt: str = MULTI_AGENT_ORCHESTRATOR_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            DelegateTool(),
            FileTool(),
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
