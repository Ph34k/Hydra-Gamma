import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
# Mock app imports
import sys
from types import SimpleNamespace

# Create mocks for app modules if they don't exist in environment
sys.modules['app.agent.core'] = SimpleNamespace(AgentCore=MagicMock)
sys.modules['app.agent.toolcall'] = SimpleNamespace(ToolCallAgent=MagicMock)
sys.modules['app.logger'] = SimpleNamespace(logger=MagicMock())
sys.modules['app.tool.file_tool'] = SimpleNamespace(FileTool=MagicMock)
sys.modules['app.tool.shell_tool'] = SimpleNamespace(ShellTool=MagicMock)
sys.modules['app.tool.python_execute'] = SimpleNamespace(PythonExecute=MagicMock)
sys.modules['app.metrics.performance'] = SimpleNamespace(PerformanceMonitor=MagicMock)

# Now import the class under test
from app.agent.specialized.meta import MetaProgrammerAgent, ImprovementHypothesis, CodePatch, TestResult

class TestMetaProgrammer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Setup mocks
        self.mock_file_tool = AsyncMock()
        self.mock_shell_tool = AsyncMock()
        self.mock_python_tool = MagicMock()

        # Patch Field defaults in the class definition or instance
        with patch('app.agent.specialized.meta.FileTool', return_value=self.mock_file_tool), \
             patch('app.agent.specialized.meta.ShellTool', return_value=self.mock_shell_tool), \
             patch('app.agent.specialized.meta.PythonExecute', return_value=self.mock_python_tool):
            self.agent = MetaProgrammerAgent()

        # Manually inject mocks because pydantic might have instantiated new ones
        self.agent.file_tool = self.mock_file_tool
        self.agent.shell_tool = self.mock_shell_tool
        self.agent.python_tool = self.mock_python_tool

    def test_analyze_performance(self):
        metrics = {"failure_counts": {"tool_a": 5, "tool_b": 1}}
        hypothesis = self.agent.analyze_performance(metrics)
        self.assertIsNotNone(hypothesis)
        self.assertEqual(hypothesis.target_component, "Tool:tool_a")

    async def test_validate_change(self):
        patch = CodePatch(file_path="test.py", diff_content="new_code", description="fix")

        # Simulate shell success for syntax check
        self.mock_shell_tool.execute.return_value = "Success"
        self.mock_file_tool.write.return_value = None # Write success

        result = await self.agent.validate_change(patch)

        self.assertTrue(result.passed)
        self.mock_file_tool.write.assert_called()
        self.mock_shell_tool.execute.assert_called()

    async def test_deploy_change(self):
        patch = CodePatch(file_path="test.py", diff_content="new_code", description="fix")

        # Simulate file read success
        self.mock_file_tool.read.return_value = "old_code"
        self.mock_file_tool.write.return_value = None

        success = await self.agent.deploy_change(patch)

        self.assertTrue(success)
        # Verify backup
        self.mock_file_tool.write.assert_any_call("test.py.bak", "old_code")
        # Verify patch
        self.mock_file_tool.write.assert_any_call("test.py", "new_code")

if __name__ == '__main__':
    unittest.main()
