from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import datetime
import json
from app.schema import Message

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
        # Simple sliding window for now as per Bible 4.2 (L2 Memory)
        if len(self.facts) > self.max_facts:
            # TODO: In future, use LLM to summarize older facts into L3 memory
            self.facts = self.facts[-self.max_facts:]

    def sync_with_environment(self, snapshot: Dict[str, Any]):
        self.environment_snapshot.update(snapshot)

    def get_summary(self) -> str:
        summary = "Current Beliefs:\n"
        # Show recent facts, but limit characters if needed
        for fact in self.facts[-10:]: # Show last 10 facts
            summary += f"- {fact.content[:200]}...\n" if len(fact.content) > 200 else f"- {fact.content}\n"
        if self.environment_snapshot:
            # Format environment snapshot nicely
            env_str = f"PWD: {self.environment_snapshot.get('pwd', 'unknown')}\n"
            if 'ls' in self.environment_snapshot:
                env_str += f"Files: {', '.join(str(x) for x in self.environment_snapshot.get('ls', []))}\n"
            summary += f"Environment: \n{env_str}\n"
        return summary

class Goal(BaseModel):
    description: str
    status: str = "pending" # pending, active, completed, failed
    priority: int = 1

    async def is_satisfied(self, beliefs: BeliefSet, llm: Any) -> bool:
        if self.status == "completed":
            return True

        # Use LLM to verify if goal is met
        prompt = f"""
        Goal: {self.description}

        Current Beliefs (Observations & State):
        {beliefs.get_summary()}

        Based on the current beliefs, has this goal been achieved?
        If yes, reply with 'YES'.
        If no, reply with 'NO'.
        """
        try:
            response = await llm.ask([Message.user_message(prompt)], stream=False)
            if "YES" in response.strip().upper():
                self.status = "completed"
                return True
        except Exception:
            pass # Default to False on error

        return False

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

    async def is_satisfied(self, beliefs: BeliefSet, llm: Any = None) -> bool:
        # Check if all active goals are satisfied
        if not self.active_goals:
            return False

        for goal in self.active_goals:
            if goal.status != "completed":
                # If LLM is provided, check dynamically
                if llm and await goal.is_satisfied(beliefs, llm):
                    continue # Goal is satisfied, check next
                return False # Found an unsatisfied goal

        return True

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

    async def generate_plan(self, goal: Goal, beliefs: BeliefSet, llm: Any) -> Optional[Plan]:
        """Generate a plan using the LLM based on the goal and beliefs."""
        prompt = f"""
        You are an expert planner. Create a step-by-step plan to achieve the following goal.

        Goal: {goal.description}

        Context:
        {beliefs.get_summary()}

        Return a JSON object with the following structure:
        {{
            "goal": "{goal.description}",
            "phases": [
                {{
                    "id": 1,
                    "title": "Phase Title",
                    "description": "Detailed description of what to do",
                    "status": "pending"
                }},
                ...
            ]
        }}
        """
        try:
            response = await llm.ask([Message.user_message(prompt)], stream=False)
            # Basic cleaning of markdown code blocks if present
            clean_response = response.replace("```json", "").replace("```", "").strip()
            plan_data = json.loads(clean_response)

            # Convert to Plan object
            plan = Plan(goal=plan_data["goal"], phases=[PlanStep(**p) for p in plan_data["phases"]])

            # Initialize first step
            if plan.phases:
                plan.current_phase_id = plan.phases[0].id
                plan.phases[0].status = "in_progress"

            self.current_plan = plan
            return plan
        except Exception as e:
            # Fallback or log error
            print(f"Plan generation failed: {e}")
            return None

    def refine_plan(self):
        # Placeholder for plan refinement logic
        pass
