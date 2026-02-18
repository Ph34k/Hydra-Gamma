import asyncio
import argparse
import datetime
import os
from typing import Dict, List, Optional, Any
from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.agent.bdi import BeliefSet, GoalSet, IntentionPool, Plan, Phase
from app.schema import Message, ToolCall


class Manus(ToolCallAgent):
    """A BDI-based agent with support for both local and MCP tools."""

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # BDI Components
    beliefs: BeliefSet = Field(default_factory=BeliefSet)
    goals: GoalSet = Field(default_factory=GoalSet)
    intentions: IntentionPool = Field(default_factory=IntentionPool)

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            AskHuman(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])
    browser_context_helper: Optional[BrowserContextHelper] = None

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(
        default_factory=dict
    )  # server_id -> url/command
    _initialized: bool = False

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        """Initialize basic components synchronously."""
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        """Factory method to create and properly initialize a Manus instance."""
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(
                            f"Connected to MCP server {server_id} at {server_config.url}"
                        )
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                        )
                        logger.info(
                            f"Connected to MCP server {server_id} using command {server_config.command}"
                        )
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: List[str] = None,
    ) -> None:
        """Connect to an MCP server and add its tools."""
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url, stdio_args or [], server_id
            )
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url

        # Update available tools with only the new tools from this server
        new_tools = [
            tool for tool in self.mcp_clients.tools if tool.server_id == server_id
        ]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available tools without the disconnected server's tools
        base_tools = [
            tool
            for tool in self.available_tools.tools
            if not isinstance(tool, MCPClientTool)
        ]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    async def cleanup(self):
        """Clean up Manus agent resources."""
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        # Disconnect from all MCP servers only if we were initialized
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False

    def _get_environment_snapshot(self) -> Dict[str, Any]:
        """Capture the current state of the environment."""
        snapshot = {}
        try:
            snapshot["pwd"] = os.getcwd()
            # Limit to 20 files for context to avoid huge prompts
            snapshot["ls"] = os.listdir(os.getcwd())[:20]
            # Only capture relevant environment variables
            snapshot["env"] = {k: v for k, v in os.environ.items() if k in ["USER", "HOME", "PATH", "LANG"]}
        except Exception as e:
            logger.error(f"Failed to get environment snapshot: {e}")
        return snapshot

    async def think(self) -> bool:
        """Process current state and decide next actions using BDI reasoning loop."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        # 1. Perception: Update beliefs from environment
        snapshot = self._get_environment_snapshot()
        self.beliefs.sync_with_environment(snapshot)

        # NOTE: We removed the redundant update_from_observation here because act() already handles it.
        # This prevents duplicate facts.

        # 2. Deliberation: Decide on goals (Desires)
        # If no active goal, derive one from the last user message or context
        if not self.goals.active_goals and self.memory.messages:
             last_user_msg = next((m for m in reversed(self.memory.messages) if m.role == "user"), None)
             if last_user_msg:
                 self.goals.add_goal(last_user_msg.content)
                 self.goals.get_active_goal() # Activate it

        # 3. Planning: Generate or Refine Plan (Intentions)
        # We inject the current plan and beliefs into the prompt

        # Ensure we don't have None values in JSON generation
        current_plan_json = self.intentions.current_plan.model_dump_json() if self.intentions.current_plan else "No plan yet."
        active_goals_desc = [g.description for g in self.goals.active_goals]

        bdi_context = f"""
Current Beliefs:
{self.beliefs.get_summary()}

Current Plan:
{current_plan_json}

Current Goals:
{active_goals_desc}
"""

        original_prompt = self.next_step_prompt
        self.next_step_prompt = f"{original_prompt}\n\n{bdi_context}"

        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        if browser_in_use:
            browser_prompt = await self.browser_context_helper.format_next_step_prompt()
            if browser_prompt:
                self.next_step_prompt = f"{browser_prompt}\n\n{bdi_context}"

        try:
            # Delegate to ToolCallAgent.think to interact with LLM and select tools
            result = await super().think()
        finally:
             self.next_step_prompt = original_prompt

        return result

    async def act(self) -> str:
        """Execute actions and update beliefs."""
        # 4. Execution
        result = await super().act()

        # 5. Observation (Post-Act): Update beliefs with the result of the action
        self.beliefs.update_from_observation(result)

        # 6. Evaluate Progress
        if self.goals.is_satisfied(self.beliefs):
            logger.info("All active goals satisfied. Terminating agent.")
            self.state = AgentState.FINISHED
            self.memory.add_message(Message.assistant_message("Task Completed"))
            return "Task Completed"

        return result
