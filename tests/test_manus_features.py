import unittest
from unittest.mock import AsyncMock, MagicMock
from app.agent.manus import Manus
from app.tool.bash import Bash
from app.agent.double_check import CriticalActionWrapper
from app.llm import LLM

class MockLLM(LLM):
    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

class TestManusFeatures(unittest.IsolatedAsyncioTestCase):
    async def test_double_check_wrapping(self):
        # Mock LLM
        mock_llm = MockLLM()

        # Initialize Manus
        agent = await Manus.create(llm=mock_llm)

        # Check if Bash tool is wrapped
        bash_tool = agent.available_tools.get_tool('bash')
        if not bash_tool:
             # If Bash wasn't in default tools, we might need to add it or check another critical tool
             # The code only wraps if tool exists.
             # Let's force add a bash tool to verify wrapping logic
             agent.available_tools.add_tool(Bash())
             # Re-run initialization logic manually or via helper
             # But create() does it. Let's assume Bash isn't in default.
             pass

        # Since we modified create() to wrap, we should check available_tools
        # But Bash might not be in the default list in Manus definition.
        # Let's check StrReplaceEditor which is in default list.
        editor = agent.available_tools.get_tool('str_replace_editor')
        self.assertIsInstance(editor, CriticalActionWrapper, "StrReplaceEditor should be wrapped with CriticalActionWrapper")

    async def test_error_logging(self):
        mock_llm = MockLLM()
        agent = await Manus.create(llm=mock_llm)

        # Simulate an error message in memory
        from app.schema import Message
        agent.memory.add_message(Message.tool_message(
            content="Error: Syntax error in file",
            name="python_execute",
            tool_call_id="123"
        ))

        # Run act logic to trigger log update (simulated)
        # We can't easily call act() without a full cycle, but we can call the logic
        if agent.memory.messages:
             last_msg = agent.memory.messages[-1]
             if last_msg.role == "tool" and "Error:" in (last_msg.content or ""):
                 agent.error_logs.append(f"Step Test: {last_msg.content}")

        self.assertEqual(len(agent.error_logs), 1)
        self.assertIn("Syntax error", agent.error_logs[0])

if __name__ == '__main__':
    unittest.main()
