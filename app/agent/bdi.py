from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import datetime

class Fact(BaseModel):
    content: str
    source: str = "observation"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class BeliefSet(BaseModel):
    facts: List[Fact] = Field(default_factory=list)
    environment_snapshot: Dict[str, Any] = Field(default_factory=dict)
    max_facts: int = 50 # Limit number of facts to store

    def update_from_observation(self, observation: str):
        self.add_fact(Fact(content=observation))

    def add_fact(self, fact: Union[str, Fact]):
        if isinstance(fact, str):
            fact_obj = Fact(content=fact)
        else:
            fact_obj = fact

        self.facts.append(fact_obj)
        self.prune_facts()

    def prune_facts(self):
        """Keep only the most recent facts to avoid context overflow."""
        if len(self.facts) > self.max_facts:
            self.facts = self.facts[-self.max_facts:]

    def sync_with_environment(self, snapshot: Dict[str, Any]):
        self.environment_snapshot.update(snapshot)

    def get_summary(self) -> str:
        # Simple summary for now, can be enhanced with LLM summarization later
        summary = "Current Beliefs:\n"
        # Show recent facts, but limit characters if needed
        for fact in self.facts[-10:]: # Show last 10 facts
            summary += f"- {fact.content[:200]}...\n" if len(fact.content) > 200 else f"- {fact.content}\n"
        if self.environment_snapshot:
            # Format environment snapshot nicely
            env_str = f"PWD: {self.environment_snapshot.get('pwd', 'unknown')}\n"
            if 'ls' in self.environment_snapshot:
                env_str += f"Files: {', '.join(self.environment_snapshot['ls'])}\n"
            summary += f"Environment: \n{env_str}\n"
        return summary

class Goal(BaseModel):
    description: str
    status: str = "pending" # pending, active, completed, failed
    priority: int = 1

    def is_satisfied(self, beliefs: BeliefSet) -> bool:
        # Logic to check if goal is satisfied based on beliefs
        # This is a placeholder. Real implementation would likely involve LLM checking.
        return self.status == "completed"

class GoalSet(BaseModel):
    active_goals: List[Goal] = Field(default_factory=list)

    def add_goal(self, description: str, priority: int = 1):
        self.active_goals.append(Goal(description=description, priority=priority))

    def prioritize(self):
        self.active_goals.sort(key=lambda g: g.priority, reverse=True)

    def get_active_goal(self) -> Optional[Goal]:
        active = [g for g in self.active_goals if g.status == "active"]
        if active:
            return active[0]

        pending = [g for g in self.active_goals if g.status == "pending"]
        if pending:
            pending[0].status = "active"
            return pending[0]
        return None

    def is_satisfied(self, beliefs: BeliefSet) -> bool:
        # Check if all active goals are satisfied
        # If no active goals, it's NOT satisfied yet (waiting for goals)
        if not self.active_goals:
            return False
        return all(g.status == "completed" for g in self.active_goals)

class Phase(str, Enum):
    PERCEPTION = "PERCEPTION"
    ACTION = "ACTION"
    PLANNING = "PLANNING"
    DELIBERATION = "DELIBERATION"

class PlanStep(BaseModel):
    id: int
    title: str
    description: str
    status: str = "pending" # pending, in_progress, completed

class Plan(BaseModel):
    goal: str
    phases: List[PlanStep] = Field(default_factory=list)
    current_phase_id: Optional[int] = None

    def update(self, new_plan: "Plan"):
        self.goal = new_plan.goal
        self.phases = new_plan.phases
        self.current_phase_id = new_plan.current_phase_id

    def advance(self):
        if self.current_phase_id is None:
            if self.phases:
                self.current_phase_id = self.phases[0].id
                self.phases[0].status = "in_progress"
            return

        for i, phase in enumerate(self.phases):
            if phase.id == self.current_phase_id:
                phase.status = "completed"
                if i + 1 < len(self.phases):
                    self.current_phase_id = self.phases[i+1].id
                    self.phases[i+1].status = "in_progress"
                else:
                    self.current_phase_id = None # Plan completed
                return

class IntentionPool(BaseModel):
    current_plan: Optional[Plan] = None
    current_phase: Phase = Phase.PERCEPTION

    def set_plan(self, plan: Plan):
        self.current_plan = plan

    def generate_plan(self, goal: Goal, beliefs: BeliefSet):
        # Placeholder for plan generation logic
        pass

    def refine_plan(self):
        # Placeholder for plan refinement logic
        pass
