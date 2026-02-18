import unittest
from unittest.mock import AsyncMock, MagicMock
from app.tool.bash import Bash
from app.agent.double_check import with_double_check
from app.tool.base import ToolResult

class TestDoubleCheck(unittest.IsolatedAsyncioTestCase):
    async def test_rm_verification(self):
        # Mock Bash tool
        mock_bash = MagicMock(spec=Bash)
        mock_bash.name = "bash"
        mock_bash.description = "Execute bash commands"
        mock_bash.parameters = {"type": "object"}

        # Setup execute side effects
        async def execute_side_effect(command=None, **kwargs):
            if command.startswith("rm"):
                return ToolResult(output="") # Success
            elif command.startswith("ls"):
                # Simulate file gone (error from ls)
                return ToolResult(error="ls: cannot access 'test.txt': No such file or directory")
            return ToolResult(output="unknown")

        mock_bash.execute = AsyncMock(side_effect=execute_side_effect)

        # Wrap tool
        wrapped_tool = with_double_check(mock_bash)

        # Execute rm
        result = await wrapped_tool.execute(command="rm test.txt")

        # Check if verification was called
        self.assertIn("[Double-Check Verification]", str(result.output))
        self.assertIn("ls: cannot access", str(result.output))

        # Verify calls
        calls = mock_bash.execute.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs['command'], "rm test.txt")
        self.assertTrue(calls[1].kwargs['command'].startswith("ls -la test.txt"))

    async def test_mkdir_verification(self):
        # Mock Bash tool
        mock_bash = MagicMock(spec=Bash)
        mock_bash.name = "bash"
        mock_bash.description = "Execute bash commands"
        mock_bash.parameters = {"type": "object"}

        async def execute_side_effect(command=None, **kwargs):
            if command.startswith("mkdir"):
                return ToolResult(output="")
            elif command.startswith("ls"):
                return ToolResult(output="new_dir")
            return ToolResult(output="unknown")

        mock_bash.execute = AsyncMock(side_effect=execute_side_effect)

        wrapped_tool = with_double_check(mock_bash)

        result = await wrapped_tool.execute(command="mkdir new_dir")

        self.assertIn("[Double-Check Verification]", str(result.output))
        self.assertIn("new_dir", str(result.output))

        calls = mock_bash.execute.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].kwargs['command'].startswith("ls -d new_dir"))

if __name__ == '__main__':
    unittest.main()
