import unittest
import asyncio
import os
import tempfile
from pathlib import Path
from app.tool.file_tool import AtomicFileTool

class TestAtomicFileTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tool = AtomicFileTool(self.test_dir.name)

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

        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
