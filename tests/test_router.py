import pytest
from app.agent.router import Router, TaskPhase, ModelTier

class TestRouter:
    def test_initialization(self):
        router = Router()
        assert router.error_history == {}

    def test_route_planning(self):
        router = Router()
        tier = router.route(TaskPhase.PLANNING, context_size=1000, task_id="task1")
        assert tier == ModelTier.TIER_1

    def test_route_coding(self):
        router = Router()
        tier = router.route(TaskPhase.CODING, context_size=1000, task_id="task1")
        assert tier == ModelTier.TIER_1

    def test_route_testing(self):
        router = Router()
        tier = router.route(TaskPhase.TESTING, context_size=1000, task_id="task1")
        assert tier == ModelTier.TIER_2

    def test_error_escalation(self):
        router = Router()
        task_id = "failing_task"

        # First attempt (should be Tier 2 for TESTING)
        tier1 = router.route(TaskPhase.TESTING, context_size=1000, task_id=task_id)
        assert tier1 == ModelTier.TIER_2

        # Report failure
        router.report_failure(task_id)
        tier2 = router.route(TaskPhase.TESTING, context_size=1000, task_id=task_id)
        # Still Tier 2 because logic is > 1 failure
        assert tier2 == ModelTier.TIER_2

        # Report another failure
        router.report_failure(task_id)
        tier3 = router.route(TaskPhase.TESTING, context_size=1000, task_id=task_id)
        # Now should escalate to Tier 1
        assert tier3 == ModelTier.TIER_1

    def test_reset_history(self):
        router = Router()
        task_id = "task1"
        router.report_failure(task_id)
        router.report_failure(task_id)

        assert router.error_history[task_id] == 2
        router.reset_history(task_id)
        assert task_id not in router.error_history

    def test_get_config_for_tier(self):
        router = Router()
        assert router.get_config_for_tier(ModelTier.TIER_1) == "default"
        assert router.get_config_for_tier(ModelTier.TIER_2) == "fast"
        assert router.get_config_for_tier(ModelTier.TIER_3) == "local"
