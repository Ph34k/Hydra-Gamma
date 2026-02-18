import unittest
from unittest.mock import MagicMock
from app.agent.manus import Manus
from app.tool.planning import PlanningTool
from app.agent.bdi import IntentionPool
from app.llm import LLM

class MockLLM(LLM):
    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

class TestManusIntegration(unittest.TestCase):
    def test_planning_tool_integration(self):
        # Mock LLM
        mock_llm = MockLLM()

        # Initialize Manus
        agent = Manus(llm=mock_llm)

        # Check if PlanningTool is in available_tools
        planning_tool = None
        for tool in agent.available_tools.tools:
            if isinstance(tool, PlanningTool):
                planning_tool = tool
                break

        self.assertIsNotNone(planning_tool, "PlanningTool not found in Manus available_tools")

        # Check if intention_pool is injected
        self.assertIsNotNone(planning_tool.intention_pool, "PlanningTool.intention_pool is None")
        self.assertEqual(planning_tool.intention_pool, agent.intentions, "PlanningTool.intention_pool mismatch")

if __name__ == '__main__':
    unittest.main()
