from enum import Enum, auto
from typing import Dict, Any, Optional

class TaskPhase(Enum):
    PLANNING = auto()
    ARCHITECTURE = auto()
    CODING = auto()
    TESTING = auto()
    REVIEW = auto()
    EXTRACTION = auto()

class ModelTier(Enum):
    TIER_1 = "gpt-4-opus" # High Intelligence
    TIER_2 = "gpt-4o-mini" # Fast/Cheap
    TIER_3 = "llama-3" # Local/Budget

class Router:
    """Decides which model to use based on task complexity and phase."""

    def __init__(self):
        self.error_history: Dict[str, int] = {} # task_id -> error_count

    def route(self, task_phase: TaskPhase, context_size: int, task_id: str) -> ModelTier:
        """
        Determines the optimal model tier.

        Logic:
        1. Architecture/Planning -> Tier 1
        2. Testing/Extraction -> Tier 2 or 3
        3. High Context -> Tier with large context window (implied TIER_2/3 usually cheaper for bulk)
        4. Error History -> Escalate to Tier 1 on failure
        """

        # Check Error History Escalation
        if self.error_history.get(task_id, 0) > 1:
            return ModelTier.TIER_1

        if task_phase in [TaskPhase.ARCHITECTURE, TaskPhase.PLANNING, TaskPhase.REVIEW]:
            return ModelTier.TIER_1

        if task_phase == TaskPhase.CODING:
             # Heuristic: Coding complex logic needs Tier 1, simple snippets Tier 2
             # For now, default to Tier 1 for safety, or Tier 2 if we are aggressive on cost
             return ModelTier.TIER_1

        if task_phase in [TaskPhase.TESTING, TaskPhase.EXTRACTION]:
            return ModelTier.TIER_2

        return ModelTier.TIER_2

    def report_failure(self, task_id: str):
        """Record a failure to trigger escalation next time."""
        self.error_history[task_id] = self.error_history.get(task_id, 0) + 1

    def reset_history(self, task_id: str):
        if task_id in self.error_history:
            del self.error_history[task_id]
