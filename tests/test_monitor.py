import unittest
from unittest.mock import MagicMock, patch
import time
import os
import signal
from uuid import uuid4
from app.sandbox.monitor import ResourceMonitor

class TestResourceMonitor(unittest.TestCase):

    def setUp(self):
        self.sandbox_id = uuid4()
        self.limits = {"timeout": 1}
        self.monitor = ResourceMonitor(self.sandbox_id, self.limits)

    @patch('psutil.Process')
    def test_attach_process(self, MockProcess):
        pid = 1234
        self.monitor.attach_process(pid)
        MockProcess.assert_called_with(pid)

    @patch('psutil.Process')
    def test_check_cpu_usage(self, MockProcess):
        mock_process = MockProcess.return_value
        mock_process.cpu_percent.return_value = 50.0
        self.monitor.attach_process(1234)
        cpu_usage = self.monitor.check_cpu_usage()
        self.assertEqual(cpu_usage, 50.0)

    @patch('psutil.Process')
    def test_check_memory_usage(self, MockProcess):
        mock_process = MockProcess.return_value
        mock_process.memory_info.return_value.rss = 1048576  # 1 MB
        self.monitor.attach_process(1234)
        memory_usage = self.monitor.check_memory_usage()
        self.assertEqual(memory_usage, 1.0)  # 1 MB

    def test_check_timeout(self):
        self.assertFalse(self.monitor.check_timeout())
        time.sleep(1.1)
        self.assertTrue(self.monitor.check_timeout())

    @patch('os.kill')
    @patch('psutil.Process')
    def test_kill_process(self, MockProcess, mock_kill):
        pid = 1234
        mock_process = MockProcess.return_value
        mock_process.pid = pid
        self.monitor.attach_process(pid)
        self.monitor.kill_process()
        mock_kill.assert_called_with(pid, signal.SIGKILL)

    @patch('psutil.Process')
    def test_report_status(self, MockProcess):
        mock_process = MockProcess.return_value
        mock_process.cpu_percent.return_value = 25.0
        mock_process.memory_info.return_value.rss = 2097152  # 2 MB
        self.monitor.attach_process(1234)

        status = self.monitor.report_status()
        self.assertEqual(status['sandbox_id'], str(self.sandbox_id))
        self.assertEqual(status['cpu_usage'], 25.0)
        self.assertEqual(status['memory_usage'], 2.0)
        self.assertFalse(status['timeout_exceeded'])

if __name__ == '__main__':
    unittest.main()
