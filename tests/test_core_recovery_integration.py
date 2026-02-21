import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import asyncio
from app.agent.core import AgentCore
from app.agent.recovery import RecoveryManager, RecoveryStrategy, RecoveryPlan, ErrorCategory
from app.llm import LLM

class TestCoreRecoveryIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Mock RecoveryManager
        self.mock_recovery = MagicMock(spec=RecoveryManager)

        # Patch the class in the recovery module
        patcher = patch("app.agent.recovery.RecoveryManager")
        self.MockRecoveryClass = patcher.start()
        self.MockRecoveryClass.return_value = self.mock_recovery
        self.addCleanup(patcher.stop)

        # Patch dependencies for AgentCore init
        with patch("app.agent.core.Router"), \
             patch("app.agent.core.BudgetManager"), \
             patch("app.agent.core.StateMonitor"), \
             patch("app.agent.core.PerformanceMonitor"), \
             patch("app.agent.core.SemanticMemory"), \
             patch("app.agent.core.EpisodicStore"):

            # Use a mock that passes isinstance(x, LLM) check if possible
            # Or just pass None if allowed. Trying None first.
            # If None fails, we need to mock LLM.

            # Create a mock LLM that satisfies Pydantic validation if possible
            # Pydantic validates based on the type hint.
            # If the type hint is `LLM`, the object must be an instance of LLM.
            # We can skip validation or use a real LLM with mocked methods.
            # Or simpler: Patch `app.llm.LLM` so MagicMock is an instance of it? No.

            # Let's try creating a real LLM instance but with mocked clients?
            # Too complex.

            # Let's try `arbitrary_types_allowed=True` in config?
            # We can't change the code just for tests easily.

            # We will use `unittest.mock.create_autospec` which might help,
            # but Pydantic checks __class__.

            # Let's try to mock the validation or just instantiate AgentCore with .construct() to bypass validation?
            # Pydantic v2 has `model_construct`.

            self.agent = AgentCore.model_construct(
                llm=MagicMock(),
                name="TestAgent",
                description="Test",
                recovery_manager=self.mock_recovery
            )
            # model_construct doesn't run validators or defaults, so we need to set defaults manually if needed.
            if not hasattr(self.agent, "recovery_manager") or not self.agent.recovery_manager:
                 self.agent.recovery_manager = self.mock_recovery

            # Manually trigger the init logic if needed (like setting up other components)
            # But for this test we only need recovery_manager and tool_calls
            self.agent.tool_calls = []

    async def test_act_triggers_recovery_retry(self):
        # Setup tool call that fails
        tool_call = MagicMock()
        tool_call.function.name = "test_tool"
        tool_call.function.arguments = '{"arg": "val"}'
        self.agent.tool_calls = [tool_call]

        # Mock execute_tool to raise exception
        with patch("app.agent.core.ToolCallAgent.act", side_effect=Exception("Timeout Error")):
            # Setup recovery plan
            plan = RecoveryPlan(
                category=ErrorCategory.TIMEOUT,
                strategy=RecoveryStrategy.RETRY_WITH_DELAY,
                reasoning="Retrying after timeout"
            )
            self.mock_recovery.analyze_error.return_value = plan

            # Execute
            result = await self.agent.act()

            # Verify
            self.mock_recovery.analyze_error.assert_called_once()
            self.assertIn("Operation timed out", result)
            self.assertIn("System Advice", result)

    async def test_act_triggers_recovery_modify_args(self):
        # Setup tool call
        tool_call = MagicMock()
        tool_call.function.name = "python_execute"
        tool_call.function.arguments = '{"code": "bad syntax"}'
        self.agent.tool_calls = [tool_call]

        with patch("app.agent.core.ToolCallAgent.act", side_effect=Exception("SyntaxError")):
            plan = RecoveryPlan(
                category=ErrorCategory.SYNTAX,
                strategy=RecoveryStrategy.MODIFY_ARGS,
                reasoning="Fix your syntax"
            )
            self.mock_recovery.analyze_error.return_value = plan

            result = await self.agent.act()

            self.mock_recovery.analyze_error.assert_called_once()
            self.assertIn("Fix your syntax", result)

if __name__ == '__main__':
    unittest.main()
