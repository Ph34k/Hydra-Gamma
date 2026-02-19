from typing import Dict, Optional

class BudgetExceededError(Exception):
    pass

class BudgetManager:
    """Manages budgets and quotas for agents."""

    def __init__(self, limits: Dict[str, float]):
        self.limits = limits # user_id -> budget_limit
        self.usage: Dict[str, float] = {} # user_id -> current_usage

    def check_budget(self, user_id: str, current_cost: float):
        """Raises BudgetExceededError if limit is reached."""
        limit = self.limits.get(user_id, float('inf'))

        # Accumulate usage
        self.usage[user_id] = self.usage.get(user_id, 0.0) + current_cost

        if self.usage[user_id] > limit:
            raise BudgetExceededError(f"Budget exceeded for user {user_id}. Usage: {self.usage[user_id]}")

    def get_remaining(self, user_id: str) -> float:
        """Returns remaining budget."""
        limit = self.limits.get(user_id, float('inf'))
        used = self.usage.get(user_id, 0.0)
        return max(0.0, limit - used)

    def record_cost(self, user_id: str, cost: float):
        self.check_budget(user_id, cost)
