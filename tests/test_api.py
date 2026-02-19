import unittest
import asyncio
import sys
from uuid import uuid4
from unittest.mock import MagicMock

# Mock app.agent.browser to avoid importing Daytona
sys.modules['app.agent.browser'] = MagicMock()
sys.modules['app.daytona'] = MagicMock()
sys.modules['app.daytona.sandbox'] = MagicMock()

from fastapi.testclient import TestClient
from app.api.server import app, tasks, event_queues
from app.api.models import TaskEvent, TaskType

class TestAPIServer(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_create_task(self):
        response = self.client.post("/v1/tasks", json={
            "goal": "Test Task",
            "sandbox_config": {}
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "running")

        # Verify internal state
        self.assertIn(data["id"], tasks)

if __name__ == '__main__':
    unittest.main()
