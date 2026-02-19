import unittest
import asyncio
import os
import tempfile
from pathlib import Path
from app.tool.file_tool import FileTool

class TestFileTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tool = FileTool(base_dir=Path(self.test_dir.name))

    def tearDown(self):
        self.test_dir.cleanup()

    def test_write_read(self):
        async def run():
            await self.tool.write("test.txt", "Hello World")
            content = await self.tool.read("test.txt")
            self.assertEqual(content, "Hello World")

        asyncio.run(run())

    def test_atomic_write(self):
        async def run():
            await self.tool.write("test.txt", "Initial")
            # Verify file exists
            self.assertTrue((Path(self.test_dir.name) / "test.txt").exists())

            # Write again
            await self.tool.write("test.txt", "Updated")
            content = await self.tool.read("test.txt")
            self.assertEqual(content, "Updated")

    def test_execute_interface(self):
        async def run():
            # Test the BaseTool execute interface
            res = await self.tool.execute(action="write", path="exec.txt", content="Executed")
            self.assertIsNone(res.error)

            res = await self.tool.execute(action="read", path="exec.txt")
            self.assertEqual(res.output, "Executed")

        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
