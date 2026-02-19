from app.agent.base import BaseAgent
from app.agent.browser import BrowserAgent
from app.agent.mcp import MCPAgent
from app.agent.react import ReActAgent
from app.agent.toolcall import ToolCallAgent
from app.agent.specialized import (
    CodingAgent,
    ResearchAgent,
    SalesAgent,
    SupportAgent,
    DataScienceAgent,
    MetaProgrammerAgent,
)
from app.agent.swarm import SwarmOrchestrator

# Deprecated alias
SWEAgent = CodingAgent

__all__ = [
    "BaseAgent",
    "BrowserAgent",
    "ReActAgent",
    "ToolCallAgent",
    "MCPAgent",
    "CodingAgent",
    "ResearchAgent",
    "SalesAgent",
    "SupportAgent",
    "DataScienceAgent",
    "MetaProgrammerAgent",
    "SwarmOrchestrator",
    "SWEAgent",
]
