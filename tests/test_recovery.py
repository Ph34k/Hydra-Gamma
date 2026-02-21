import unittest
from app.agent.recovery import RecoveryManager, RecoveryPlan, RecoveryStrategy, ErrorCategory

class TestRecoveryManager(unittest.TestCase):

    def setUp(self):
        self.recovery = RecoveryManager()

    def test_analyze_syntax_error(self):
        error_msg = "SyntaxError: invalid syntax"
        tool_name = "python_execute"
        args = {"code": "def bad(: pass"}

        plan = self.recovery.analyze_error(error_msg, tool_name, args)

        self.assertEqual(plan.category, ErrorCategory.SYNTAX)
        self.assertEqual(plan.strategy, RecoveryStrategy.MODIFY_ARGS)
        self.assertIn("LLM should check file content", plan.reasoning)

    def test_analyze_timeout_error(self):
        error_msg = "TimeoutError: The operation timed out."
        tool_name = "browser_tool"
        args = {"url": "http://slow.com"}

        plan = self.recovery.analyze_error(error_msg, tool_name, args)

        self.assertEqual(plan.category, ErrorCategory.TIMEOUT)
        self.assertEqual(plan.strategy, RecoveryStrategy.RETRY_WITH_DELAY)

    def test_repetitive_failures_escalate(self):
        error_msg = "Some random error"
        tool_name = "flaky_tool"
        args = {}

        # Simulate 3 failures
        self.recovery.analyze_error(error_msg, tool_name, args)
        self.recovery.analyze_error(error_msg, tool_name, args)
        self.recovery.analyze_error(error_msg, tool_name, args)

        plan = self.recovery.analyze_error(error_msg, tool_name, args)

        self.assertEqual(plan.strategy, RecoveryStrategy.ASK_USER)
        self.assertIn("failed repeatedly", plan.reasoning)

if __name__ == '__main__':
    unittest.main()
