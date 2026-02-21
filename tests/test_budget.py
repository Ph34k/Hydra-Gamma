import pytest
from app.agent.budget import BudgetManager, BudgetExceededError

class TestBudgetManager:
    def test_initialization(self):
        limits = {"user1": 100.0, "user2": 50.0}
        manager = BudgetManager(limits)
        assert manager.limits == limits
        assert manager.usage == {}

    def test_check_budget_success(self):
        manager = BudgetManager({"user1": 100.0})
        manager.check_budget("user1", 50.0)
        assert manager.usage["user1"] == 50.0
        manager.check_budget("user1", 40.0)
        assert manager.usage["user1"] == 90.0

    def test_check_budget_exceeded(self):
        manager = BudgetManager({"user1": 100.0})
        manager.check_budget("user1", 90.0)
        with pytest.raises(BudgetExceededError) as excinfo:
            manager.check_budget("user1", 20.0)
        assert "Budget exceeded for user user1" in str(excinfo.value)
        assert manager.usage["user1"] == 110.0

    def test_get_remaining(self):
        manager = BudgetManager({"user1": 100.0})
        assert manager.get_remaining("user1") == 100.0
        manager.check_budget("user1", 30.0)
        assert manager.get_remaining("user1") == 70.0

        # Test remaining after exceeding
        try:
            manager.check_budget("user1", 80.0)
        except BudgetExceededError:
            pass
        assert manager.get_remaining("user1") == 0.0

    def test_user_without_limit(self):
        manager = BudgetManager({})
        # Should default to infinity
        manager.check_budget("unknown_user", 1000.0)
        assert manager.usage["unknown_user"] == 1000.0
        assert manager.get_remaining("unknown_user") == float('inf')

    def test_record_cost(self):
        manager = BudgetManager({"user1": 100.0})
        manager.record_cost("user1", 50.0)
        assert manager.usage["user1"] == 50.0
        with pytest.raises(BudgetExceededError):
            manager.record_cost("user1", 60.0)

    def test_negative_cost(self):
        # Budget manager doesn't explicitly forbid negative cost (refunds?)
        # Let's verify behavior
        manager = BudgetManager({"user1": 100.0})
        manager.check_budget("user1", 50.0)
        manager.check_budget("user1", -20.0)
        assert manager.usage["user1"] == 30.0
