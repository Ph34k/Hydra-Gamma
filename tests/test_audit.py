import unittest
import os
import json
import uuid
import time
from app.utils.audit import AuditLogger

class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.test_log_file = "test_audit.log"
        self.logger = AuditLogger(log_path=self.test_log_file)
        # Clear existing file
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)

    def tearDown(self):
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)

    def test_log_event(self):
        task_id = str(uuid.uuid4())
        user_id = "user_123"
        tool_name = "test_tool"

        self.logger.log_tool_call(task_id, user_id, tool_name, {"arg": "val"})

        # Verify file content
        with open(self.test_log_file, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["task_id"], task_id)
            self.assertEqual(entry["user_id"], user_id)
            self.assertEqual(entry["tool_name"], tool_name)
            self.assertEqual(entry["event_type"], "tool_call")

    def test_log_result(self):
        # Simulate result
        self.logger.log_tool_result("t1", "u1", "tool_x", "success", 100.0, "Output OK")

        with open(self.test_log_file, "r") as f:
            entry = json.loads(f.read().strip())
            self.assertEqual(entry["result_status"], "success")
            self.assertEqual(entry["duration_ms"], 100.0)

if __name__ == "__main__":
    unittest.main()
