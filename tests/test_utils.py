import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.utils.files_utils import should_exclude_file, clean_path
from app.utils.distributed import Cache, Consensus


class TestFileUtils(unittest.TestCase):
    def test_should_exclude_file(self):
        # Excluded files
        self.assertTrue(should_exclude_file("package-lock.json"))
        self.assertTrue(should_exclude_file(".DS_Store"))

        # Excluded dirs
        self.assertTrue(should_exclude_file("node_modules/test.js"))
        self.assertTrue(should_exclude_file(".git/HEAD"))

        # Excluded extensions
        self.assertTrue(should_exclude_file("image.png"))
        self.assertTrue(should_exclude_file("data.db"))

        # Included files
        self.assertFalse(should_exclude_file("src/main.py"))
        self.assertFalse(should_exclude_file("README.md"))

    def test_clean_path(self):
        self.assertEqual(clean_path("/workspace/src/main.py"), "src/main.py")
        self.assertEqual(clean_path("workspace/src/main.py"), "src/main.py")
        self.assertEqual(clean_path("/src/main.py"), "src/main.py")
        self.assertEqual(clean_path("src/main.py"), "src/main.py")


class TestDistributed(unittest.IsolatedAsyncioTestCase):
    async def test_cache(self):
        cache = Cache()
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")
        self.assertIsNone(cache.get("missing"))

        # Semantic get/set (mocked with md5)
        cache.semantic_set("query", "response")
        self.assertEqual(cache.semantic_get("query"), "response")

    async def test_consensus(self):
        consensus = Consensus()
        result = await consensus.propose_state_update("agent1", "hash123")
        self.assertTrue(result)


class TestScheduler(unittest.IsolatedAsyncioTestCase):
    async def test_check_and_run_tasks(self):
        # We need to import inside test to avoid early import errors
        # but here the error is that app.utils does not expose scheduler
        # or it wasn't imported yet.
        # Directly import module to ensure it's loaded before patching
        import app.utils.scheduler

        with patch("app.utils.scheduler.Manus") as MockManus, \
             patch("app.utils.scheduler.ScheduleTool") as MockTool:

            from app.utils.scheduler import SchedulerService
            import time

            # Setup mock tasks
            mock_tasks = {
                "task1": {
                    "name": "Test Task",
                    "status": "active",
                    "type": "interval",
                    "interval": 60,
                    "last_run": time.time() - 100,  # Due
                    "prompt": "Run me",
                    "repeat": False
                },
                "task2": {
                    "name": "Task 2",
                    "status": "active",
                    "type": "interval",
                    "interval": 60,
                    "last_run": time.time(),  # Not due
                    "prompt": "Wait"
                }
            }

            tool_instance = MockTool.return_value
            tool_instance._load_tasks.return_value = mock_tasks

            # Mock Agent
            # The agent instance isn't necessarily async callable
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock()  # run is async

            # Manus.create is async class method
            # so it should return a coroutine that resolves to mock_agent
            MockManus.create = AsyncMock(return_value=mock_agent)

            scheduler = SchedulerService()

            # Run check
            await scheduler.check_and_run_tasks()

            # Give background tasks a chance to run
            await asyncio.sleep(0.1)

            # Verify task 1 ran
            MockManus.create.assert_called()
            mock_agent.run.assert_called_with("Run me")

            # Verify task status update
            self.assertEqual(mock_tasks["task1"]["status"], "completed")
            tool_instance._save_tasks.assert_called()


if __name__ == '__main__':
    unittest.main()
