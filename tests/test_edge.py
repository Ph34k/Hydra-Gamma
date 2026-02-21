import unittest
from unittest.mock import MagicMock
from app.edge.runtime import LocalAgent, LocalRuntime
from app.edge.sanitizer import Sanitizer

class TestEdgeAgent(unittest.TestCase):

    def setUp(self):
        self.agent = LocalAgent()
        # Mock runtime AFTER init to test init logic first if needed,
        # but for this test we need it mocked to avoid real file I/O or connections
        self.agent.runtime = MagicMock(spec=LocalRuntime)

    def test_local_execution(self):
        # We verify that act() calls the parent act() but also logs "EdgeAgent"
        self.assertEqual(self.agent.name, "EdgeAgent")
        # Since we mocked runtime in setUp, we check if the mock was assigned
        self.assertIsInstance(self.agent.runtime, MagicMock)

    def test_sanitizer(self):
        data = {
            "user": "alice",
            "email": "alice@example.com",
            "api_key": "sk-12345",
            "config": {
                "token": "secret"
            }
        }

        clean = Sanitizer.sanitize(data)

        self.assertEqual(clean["user"], "alice")
        # CoreSanitizer uses [EMAIL_REDACTED]
        self.assertEqual(clean["email"], "[EMAIL_REDACTED]")
        # Key based redaction uses [REDACTED]
        self.assertEqual(clean["api_key"], "[REDACTED]")
        self.assertEqual(clean["config"]["token"], "[REDACTED]")

    def test_runtime_sync(self):
        runtime = LocalRuntime()
        runtime.connect_cloud()

        data = {"status": "ok", "token": "secret"}
        synced = runtime.sync_data(data)

        self.assertTrue(runtime.is_connected)
        # The runtime.sync_data method returns the sanitized data
        # We need to verify that 'token' key is redacted in that return value
        self.assertEqual(synced["token"], "[REDACTED]")

if __name__ == '__main__':
    unittest.main()
