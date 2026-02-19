import unittest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch
from app.agent.toolcall import ToolCallAgent, TOOL_REQUIRED_SECRETS
from app.schema import ToolCall, Function
from app.llm import LLM
from app.tool.base import BaseTool, ToolResult
import json

class MockLLM(LLM):
    def __init__(self, *args, **kwargs):
        pass
    async def ask_tool(self, *args, **kwargs):
        return MagicMock()

class TestSecretsInjection(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MockLLM()
        self.agent = ToolCallAgent(llm=self.mock_llm)

        # Inject a mock secret into the manager (via environment variable for simplicity in test)
        os.environ["SEARCH_API_KEY"] = "mock_search_key"

        # Mock the tool
        self.mock_tool = AsyncMock()
        self.mock_tool.name = "search_tool"
        self.mock_tool.return_value = ToolResult(output="Result")

        self.agent.available_tools.tool_map["search_tool"] = self.mock_tool

    def tearDown(self):
        if "SEARCH_API_KEY" in os.environ:
            del os.environ["SEARCH_API_KEY"]

    def test_secrets_injection(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define a side effect to check environ during execution
        async def check_environ(*args, **kwargs):
            # Assertions inside side_effect will raise exception which fails the test
            if os.environ.get("SEARCH_API_KEY") != "mock_search_key":
                raise AssertionError("Secret not injected!")
            return ToolResult(output="Success")

        self.mock_tool.side_effect = check_environ

        command = ToolCall(
            id="1",
            function=Function(name="search_tool", arguments=json.dumps({"query": "test"}))
        )

        # We need to temporarily unset the secret from env so we can verify it's injected by the agent logic
        # Wait, my SecretsManager reads from env as fallback.
        # If I unset it, SecretsManager won't find it.
        # SecretsManager.get_secret will return None.

        # So I need SecretsManager to have it, but os.environ to NOT have it before execution?
        # My implementation modifies os.environ.

        # In this test environment, SecretsManager reads from os.environ.
        # So I must have it in os.environ.
        # But wait, if it's already in os.environ, then injection updates it (overwrite or same).

        # To test injection, I should mock SecretsManager to return a key that is NOT in os.environ.

        self.agent._secrets.get_secret = MagicMock(return_value="injected_secret_value")
        # Ensure it's not in environ
        if "SEARCH_API_KEY" in os.environ:
            del os.environ["SEARCH_API_KEY"]

        async def check_environ_injected(*args, **kwargs):
            if os.environ.get("SEARCH_API_KEY") != "injected_secret_value":
                raise AssertionError(f"Secret not injected correctly. Got: {os.environ.get('SEARCH_API_KEY')}")
            return ToolResult(output="Success")

        self.mock_tool.side_effect = check_environ_injected

        # Run
        result = loop.run_until_complete(self.agent.execute_tool(command))

        self.assertIn("Success", result)
        # Verify it's cleaned up
        self.assertNotIn("SEARCH_API_KEY", os.environ)

        loop.close()

if __name__ == "__main__":
    unittest.main()
