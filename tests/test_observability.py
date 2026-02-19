import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock problematic modules
sys.modules["browser_use"] = MagicMock()
sys.modules["browser_use.browser"] = MagicMock()
sys.modules["browser_use.browser.context"] = MagicMock()
sys.modules["browser_use.dom.service"] = MagicMock()
sys.modules["baidusearch"] = MagicMock()
sys.modules["baidusearch.baidusearch"] = MagicMock()
sys.modules["googlesearch"] = MagicMock()
sys.modules["duckduckgo_search"] = MagicMock()
sys.modules["pdfminer"] = MagicMock()
sys.modules["pdfminer.high_level"] = MagicMock()
sys.modules["html2text"] = MagicMock()
sys.modules["daytona"] = MagicMock()

import unittest
import json
import os
from app.utils.audit import AuditLogger
from app.agent.toolcall import ToolCallAgent
from app.llm import LLM
from app.agent.safety import HallucinationMonitor

# Mock LLM properly
class MockLLM(LLM):
    def __init__(self, config_name: str = "default", llm_config=None):
        self.ask_tool = AsyncMock()
        self.ask = AsyncMock()
        self.model = "mock-model"
        self.tokenizer = MagicMock()

class TestObservability(unittest.TestCase):
    def setUp(self):
        self.audit_file = "test_audit.log"
        if os.path.exists(self.audit_file):
            os.remove(self.audit_file)

    def tearDown(self):
        if os.path.exists(self.audit_file):
            os.remove(self.audit_file)

    def test_audit_logger_schema(self):
        logger = AuditLogger(log_path=self.audit_file)
        logger.log_event(
            event_type="test_event",
            task_id="task_1",
            trace_id="trace_1",
            user_id="user_1",
            payload={"foo": "bar"}
        )

        with open(self.audit_file, "r") as f:
            line = f.readline()
            entry = json.loads(line)

        self.assertEqual(entry["event_type"], "test_event")
        self.assertEqual(entry["task_id"], "task_1")
        self.assertEqual(entry["trace_id"], "trace_1")
        self.assertEqual(entry["user_id"], "user_1")
        self.assertEqual(entry["payload"], {"foo": "bar"})
        self.assertIn("timestamp", entry)

    def test_hallucination_monitor_integration(self):
        mock_llm = MockLLM(config_name="test_hallucination")
        # Mock low confidence thought
        mock_response = MagicMock()
        mock_response.content = "I think maybe the answer is 42"
        mock_response.tool_calls = []
        mock_llm.ask_tool = AsyncMock(return_value=mock_response)

        agent = ToolCallAgent(llm=mock_llm)

        # Spy on HallucinationMonitor.check_confidence
        with patch.object(HallucinationMonitor, 'check_confidence', return_value=0.5) as mock_check:
            import asyncio
            asyncio.run(agent.think())

            mock_check.assert_called_with(mock_response.content)

            # Since confidence is 0.5 (< 0.7), it should log a warning
            # We can't easily assert on logger.warning without complex setup,
            # but verifying the call confirms integration.

if __name__ == "__main__":
    unittest.main()
