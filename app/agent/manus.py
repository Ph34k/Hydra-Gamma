import datetime
from typing import Dict, List, Optional, Any
from pydantic import Field, model_validator

from app.agent.core import AgentCore
from app.agent.memory import ContextManager
from app.agent.reasoning import ReasoningEngine
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.browser_tool import BrowserTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.memory import MemorySearchTool
from app.tool.shell_tool import ShellTool
from app.tool.planning import PlanningTool
from app.sandbox.docker import DockerSandbox


class Manus(AgentCore):
    """
    A BDI-based agent with support for both local and MCP tools.
    Inherits BDI loop and architecture from AgentCore.
    """

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(default_factory=dict)
    _initialized: bool = False

    # Sandbox (Chapter 16)
    sandbox: Optional[Any] = Field(default=None, exclude=True)

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserTool(),
            StrReplaceEditor(),
            AskHuman(),
            Terminate(),
            MemorySearchTool(),
            ShellTool(),
            PlanningTool(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    @model_validator(mode="after")
    def initialize_manus_components(self) -> "Manus":
        """Initialize Manus-specific components including Sandbox."""

        # Initialize Sandbox if configured (or default to try)
        # Note: In restricted environments, this might fail or be skipped.
        # We assume config or availability check.
        try:
            # We delay start() until usage or here?
            # Ideally here if we want tools to be ready.
            # But start() takes time.
            # For now, we just instantiate. start() should be called in create() or async.
            self.sandbox = DockerSandbox()
        except Exception as e:
            logger.warning(f"Could not initialize Docker Sandbox: {e}")
            self.sandbox = None

        # Inject sandbox into tools
        if self.available_tools:
            py_tool = self.available_tools.tool_map.get("python_execute")
            if py_tool:
                py_tool.sandbox = self.sandbox

            sh_tool = self.available_tools.tool_map.get("shell")
            if sh_tool:
                sh_tool.sandbox = self.sandbox

        return self

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        """Factory method to create and properly initialize a Manus instance."""
        instance = cls(**kwargs)

        # Start Sandbox if available
        if instance.sandbox:
            try:
                # Docker start is synchronous in our implementation but fast enough?
                # Ideally async.
                instance.sandbox.start()
            except Exception as e:
                logger.warning(f"Failed to start Docker Sandbox: {e}")
                instance.sandbox = None # Fallback to local
                # Re-inject None to tools
                if instance.available_tools:
                    instance.available_tools.tool_map.get("python_execute").sandbox = None
                    instance.available_tools.tool_map.get("shell").sandbox = None

        await instance.initialize_mcp_servers()
        instance._initialized = True

        # Ensure monitors are ready (from AgentCore)
        if not instance.performance_monitor:
            from app.metrics.performance import PerformanceMonitor
            instance.performance_monitor = PerformanceMonitor()
        if not instance.state_monitor:
            from app.memory.state import StateMonitor
            instance.state_monitor = StateMonitor()

        return instance

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(f"Connected to MCP server {server_id} at {server_config.url}")
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                        )
                        logger.info(f"Connected to MCP server {server_id} using command {server_config.command}")
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
            await self.mcp_clients.connect_stdio(server_url, stdio_args or [], server_id)
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)

        self.connected_servers[server_id or server_url] = server_url

        # Update available tools
        new_tools = [tool for tool in self.mcp_clients.tools if tool.server_id == server_id]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available tools
        base_tools = [tool for tool in self.available_tools.tools if not isinstance(tool, MCPClientTool)]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    async def think(self) -> bool:
        """Override think to ensure MCP servers are initialized before AgentCore think loop."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        return await super().think()

    async def cleanup(self):
        """Clean up Manus agent resources."""
        # Stop Sandbox
        if self.sandbox:
            try:
                self.sandbox.stop()
            except Exception as e:
                logger.error(f"Error stopping sandbox: {e}")

        # Delegate to parent cleanup (ToolCallAgent)
        await super().cleanup()

        # Clean up browser tool
        browser_tool = self.available_tools.tool_map.get("browser_tool")
        if browser_tool and hasattr(browser_tool, "cleanup"):
            await browser_tool.cleanup()

        # Disconnect MCP
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False

        if self.performance_monitor:
            self.performance_monitor.log_metrics()
