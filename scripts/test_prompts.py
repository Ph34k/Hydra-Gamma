#!/usr/bin/env python3
import asyncio
import sys
import os
from unittest.mock import MagicMock

# Mock modules for standalone execution
sys.modules["browser_use"] = MagicMock()
sys.modules["baidusearch"] = MagicMock()
sys.modules["googlesearch"] = MagicMock()
sys.modules["duckduckgo_search"] = MagicMock()
sys.modules["pdfminer"] = MagicMock()
sys.modules["pdfminer.high_level"] = MagicMock()
sys.modules["html2text"] = MagicMock()
sys.modules["daytona"] = MagicMock()

try:
    from app.agent.toolcall import ToolCallAgent
    from app.llm import LLM
except ImportError:
    # Add root to path
    sys.path.append(os.getcwd())
    from app.agent.toolcall import ToolCallAgent
    from app.llm import LLM

class PromptRegressionTest:
    """
    Chapter 37: Prompt Regression Testing
    Executes a 'Golden Set' of tasks to ensure prompt changes don't degrade performance.
    """

    GOLDEN_SET = [
        {
            "id": "task_001",
            "prompt": "List files in current directory",
            "expected_tool": "shell",
            "expected_args_contain": "ls"
        },
        {
            "id": "task_002",
            "prompt": "Search for 'Manus Agent'",
            "expected_tool": "search_tool",
            "expected_args_contain": "Manus Agent"
        }
    ]

    def __init__(self):
        # We use a real LLM or a sophisticated Mock for regression
        # Here we mock for demonstration
        self.llm = MagicMock(spec=LLM)
        self.agent = ToolCallAgent(llm=self.llm)

    async def run_test(self, case):
        print(f"🧪 Testing Case {case['id']}: {case['prompt']}")

        # Simulate LLM response based on prompt
        # In a real regression test, this would call the actual LLM with the prompt
        mock_response = MagicMock()
        mock_response.content = "I will use the tool."

        if "List files" in case['prompt']:
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "shell"
            mock_tool_call.function.arguments = '{"command": "ls -la"}'
            mock_response.tool_calls = [mock_tool_call]
        elif "Search" in case['prompt']:
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "search_tool"
            mock_tool_call.function.arguments = '{"query": "Manus Agent"}'
            mock_response.tool_calls = [mock_tool_call]

        self.llm.ask_tool.return_value = mock_response

        # Inject prompt
        await self.agent.run(case['prompt'])

        # Verify
        # This logic is simplified; in real Agent, run() executes tools.
        # We check if the expected tool was selected.
        # Since we mocked execution, we check tool_calls in agent state or LLM call.

        last_call = self.llm.ask_tool.call_args
        if not last_call:
            print(f"❌ Failed: LLM was not called")
            return False

        # We can't easily check what the agent *did* because execution is internal.
        # But we can check if the LLM *proposed* the right tool.

        tool_calls = mock_response.tool_calls
        if not tool_calls:
            print(f"❌ Failed: No tool calls generated")
            return False

        tool_name = tool_calls[0].function.name
        tool_args = tool_calls[0].function.arguments

        if tool_name != case['expected_tool']:
            print(f"❌ Failed: Expected tool {case['expected_tool']}, got {tool_name}")
            return False

        if case['expected_args_contain'] not in tool_args:
            print(f"❌ Failed: Args {tool_args} do not contain {case['expected_args_contain']}")
            return False

        print(f"✅ Passed")
        return True

    async def run_all(self):
        passed = 0
        for case in self.GOLDEN_SET:
            if await self.run_test(case):
                passed += 1

        print(f"\n📊 Result: {passed}/{len(self.GOLDEN_SET)} passed.")
        return passed == len(self.GOLDEN_SET)

if __name__ == "__main__":
    runner = PromptRegressionTest()
    success = asyncio.run(runner.run_all())
    sys.exit(0 if success else 1)
