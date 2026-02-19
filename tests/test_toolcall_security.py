import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.agent.toolcall import ToolCallAgent
from app.schema import ToolCall, Function
from app.agent.rbac import UserRole
from app.llm import LLM
from app.tool.base import BaseTool, ToolResult
import json

class MockLLM(LLM):
    def __init__(self, *args, **kwargs):
        pass

    async def ask_tool(self, *args, **kwargs):
        return MagicMock()

class MockBashTool(BaseTool):
    name: str = "bash"
    description: str = "Executes bash commands"

    async def execute(self, command: str = "", **kwargs):
        return ToolResult(output=f"Executed: {command}")

class TestToolCallSecurity(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MockLLM()
        self.agent = ToolCallAgent(llm=self.mock_llm)
        self.agent._user.role = UserRole.FREE

        # Add MockBashTool
        self.agent.available_tools.add_tool(MockBashTool())

    async def _execute_tool(self, name, args):
        command = ToolCall(
            id="call_1",
            function=Function(name=name, arguments=json.dumps(args))
        )
        return await self.agent.execute_tool(command)

    def test_security_blocked_command(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 1. Dangerous command (Ethical Guard)
        # "rm -rf /" is blocked by EthicalGuard.check_tool_args
        result = loop.run_until_complete(
            self._execute_tool("bash", {"command": "rm -rf /"})
        )
        self.assertIn("Error: Command blocked by safety policy", result)

        loop.close()

    def test_rbac_denied(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 2. RBAC check
        # Free user cannot run "curl" (advanced shell)
        # Assuming "curl" is blocked for FREE in RBACManager (it checks BASIC_SHELL_COMMANDS)
        result = loop.run_until_complete(
            self._execute_tool("bash", {"command": "curl http://google.com"})
        )
        self.assertIn("Permission denied", result)

        loop.close()

    def test_pii_sanitization_in_logs(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Mock available_tools.execute to return PII
        # We need to find the tool instance in tool_map and mock its execute
        # But ToolCollection calls tool instance directly.
        # My MockBashTool is a class.

        # Let's replace the tool in the map with a MagicMock wrapper
        mock_tool = AsyncMock()
        mock_tool.name = "bash"
        mock_tool.return_value = ToolResult(output="My email is test@example.com")

        # But ToolCollection.execute calls tool(**kwargs).
        # BaseTool.__call__ calls self.execute.

        # I'll simply patch the tool in tool_map
        self.agent.available_tools.tool_map["bash"] = mock_tool

        result = loop.run_until_complete(
            self._execute_tool("bash", {"command": "ls"}) # allowed command
        )

        self.assertIn("[EMAIL_REDACTED]", result)
        self.assertNotIn("test@example.com", result)

        loop.close()

if __name__ == "__main__":
    unittest.main()
