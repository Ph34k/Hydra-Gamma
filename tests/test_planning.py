import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from app.tool.planning import PlanningTool
from app.agent.bdi import IntentionPool, Plan

class TestPlanningSystem(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tool = PlanningTool()
        self.intention_pool = IntentionPool()
        self.tool.intention_pool = self.intention_pool

    async def test_update_plan(self):
        result = await self.tool.execute(
            action="update",
            goal="Build a website",
            phases=[
                {"title": "Design", "description": "Create mockups"},
                {"title": "Develop", "description": "Write code"}
            ]
        )
        self.assertIn("Plan updated", result)
        self.assertIsNotNone(self.intention_pool.current_plan)
        self.assertEqual(self.intention_pool.current_plan.goal, "Build a website")
        self.assertEqual(len(self.intention_pool.current_plan.phases), 2)
        self.assertEqual(self.intention_pool.current_plan.current_phase_id, 1)

    async def test_advance_phase(self):
        # Setup initial plan
        await self.tool.execute(
            action="update",
            goal="Test",
            phases=[{"title": "P1"}, {"title": "P2"}]
        )

        # Advance
        result = await self.tool.execute(action="advance")
        self.assertIn("Advanced to phase 2", result)
        self.assertEqual(self.intention_pool.current_plan.current_phase_id, 2)

        # Advance to completion
        result = await self.tool.execute(action="advance")
        self.assertIn("Plan completed", result)
        self.assertIsNone(self.intention_pool.current_plan.current_phase_id)

    async def test_refine_phase(self):
        # Setup initial plan
        await self.tool.execute(
            action="update",
            goal="Test",
            phases=[{"title": "P1", "description": "Original"}]
        )

        # Refine
        result = await self.tool.execute(
            action="refine",
            phase_id=1,
            description="Refined description"
        )

        self.assertIn("Phase 1 refined", result)
        self.assertEqual(self.intention_pool.current_plan.phases[0].description, "Refined description")

if __name__ == '__main__':
    unittest.main()
