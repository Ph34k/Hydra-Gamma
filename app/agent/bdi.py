from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import datetime

class Fact(BaseModel):
    content: str
    source: str = "observation"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class BeliefSet(BaseModel):
    facts: List[Fact] = Field(default_factory=list)
    environment_snapshot: Dict[str, Any] = Field(default_factory=dict)

    def update_from_observation(self, observation: str):
        self.facts.append(Fact(content=observation))

    def sync_with_environment(self, snapshot: Dict[str, Any]):
        self.environment_snapshot.update(snapshot)

    def get_summary(self) -> str:
        # Simple summary for now, can be enhanced with LLM summarization later
        summary = "Current Beliefs:\n"
        for fact in self.facts[-5:]: # Show last 5 facts
            summary += f"- {fact.content}\n"
        if self.environment_snapshot:
            summary += f"Environment: {self.environment_snapshot}\n"
        return summary

class Goal(BaseModel):
    description: str
    status: str = "pending" # pending, active, completed, failed
    priority: int = 1

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

class Phase(BaseModel):
    id: int
    title: str
    description: str
    status: str = "pending" # pending, in_progress, completed

class Plan(BaseModel):
    goal: str
    phases: List[Phase] = Field(default_factory=list)
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

    def set_plan(self, plan: Plan):
        self.current_plan = plan
