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
    TIER_1 = "smart" # High Intelligence (e.g. GPT-4o, Claude 3.5 Sonnet)
    TIER_2 = "fast"  # Fast/Cheap (e.g. GPT-4o-mini, Haiku)
    TIER_3 = "local" # Local/Budget (e.g. Llama 3)

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

    def get_config_for_tier(self, tier: ModelTier) -> str:
        """Map ModelTier to LLM config name."""
        if tier == ModelTier.TIER_1:
            return "default" # Usually the best model is default
        elif tier == ModelTier.TIER_2:
            return "fast" # Configure 'fast' in config.toml
        elif tier == ModelTier.TIER_3:
            return "local"
        return "default"
