import asyncio
import json
from typing import Optional, Dict, Any

from pydantic import PrivateAttr

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.mcp import MCPClients


class MCPTool(BaseTool):
    name: str = "mcp_tool"
    description: str = """
    Interface for interacting with Model Context Protocol (MCP) servers.
    Allows connecting to servers, listing tools, and calling tools (e.g., Notion).
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["connect_server", "list_tools", "call_tool"],
                "description": "Action to perform.",
            },
            "server_name": {
                "type": "string",
                "description": "Name/ID of the MCP server.",
            },
            "server_url": {
                "type": "string",
                "description": "URL (SSE) or command (Stdio) for the MCP server.",
            },
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to call.",
            },
            "args": {
                "type": "string",
                "description": "JSON string of arguments for the tool.",
            },
        },
        "required": ["action"],
    }

    _mcp_clients: MCPClients = PrivateAttr(default_factory=MCPClients)

    async def execute(
        self,
        action: str,
        server_name: Optional[str] = None,
        server_url: Optional[str] = None,
        tool_name: Optional[str] = None,
        args: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "connect_server":
                if not server_name or not server_url:
                    return ToolResult(error="Server name and URL required for connect_server")

                # Simple heuristic: starts with http -> SSE, else Stdio command
                if server_url.startswith("http"):
                    await self._mcp_clients.connect_sse(server_url, server_name)
                else:
                    parts = server_url.split()
                    command = parts[0]
                    cmd_args = parts[1:]
                    await self._mcp_clients.connect_stdio(command, cmd_args, server_name)

                return ToolResult(output=f"Connected to MCP server '{server_name}'")

            elif action == "list_tools":
                result = await self._mcp_clients.list_tools()
                # Format output nicely
                tools_list = [f"{t.name}: {t.description}" for t in result.tools]
                return ToolResult(output="\n".join(tools_list))

            elif action == "call_tool":
                if not tool_name:
                    return ToolResult(error="Tool name required for call_tool")

                # Locate the tool wrapper
                target_tool = None
                # Check direct match or match by original name
                for name, tool in self._mcp_clients.tool_map.items():
                    if name == tool_name or getattr(tool, "original_name", "") == tool_name:
                        target_tool = tool
                        break

                if not target_tool:
                    return ToolResult(error=f"Tool '{tool_name}' not found. Available tools: {list(self._mcp_clients.tool_map.keys())}")

                # Parse arguments
                tool_args = {}
                if args:
                    try:
                        tool_args = json.loads(args)
                    except json.JSONDecodeError:
                        return ToolResult(error="Invalid JSON in 'args'")

                return await target_tool.execute(**tool_args)

            else:
                return ToolResult(error=f"Unknown action: {action}")

        except Exception as e:
            logger.exception(f"MCPTool error: {e}")
            return ToolResult(error=str(e))
