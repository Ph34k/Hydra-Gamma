from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.tool.base import BaseTool
from app.agent.bdi import IntentionPool, Plan, Phase

class PlanningTool(BaseTool):
    name: str = "planning"
    description: str = """
    Manage the agent's plan.
    Actions:
    - 'update': Create a new plan or replace the existing one. Requires 'goal' and 'phases' (list of dicts with 'title', 'description').
    - 'advance': Mark current phase as completed and move to the next.
    - 'refine': Update details of a specific phase. Requires 'phase_id' and 'description'.
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["update", "advance", "refine"],
                "description": "The action to perform on the plan."
            },
            "goal": {
                "type": "string",
                "description": "The main goal of the plan (required for 'update')."
            },
            "phases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["title"]
                },
                "description": "List of phases for the plan (required for 'update')."
            },
            "phase_id": {
                "type": "integer",
                "description": "The ID of the phase to refine (required for 'refine')."
            },
            "description": {
                "type": "string",
                "description": "The new description for the phase (required for 'refine')."
            }
        },
        "required": ["action"]
    }

    # We need access to the agent's intention pool.
    # Since tools are stateless, we will need to inject this dependency.
    # A common pattern is to pass it during initialization or have the agent inject it before execution.
    # For now, we'll assume the agent sets a reference to itself or the intention pool on the tool instance.
    intention_pool: Optional[IntentionPool] = None

    async def execute(self, action: str, goal: str = "", phases: List[Dict[str, Any]] = [], phase_id: int = -1, description: str = "") -> str:
        if not self.intention_pool:
            return "Error: Intention pool not initialized."

        if action == "update":
            if not goal or not phases:
                return "Error: 'update' requires 'goal' and 'phases'."

            new_phases = []
            for i, p in enumerate(phases):
                new_phases.append(Phase(
                    id=i+1,
                    title=p.get("title", f"Phase {i+1}"),
                    description=p.get("description", ""),
                    status="pending"
                ))

            new_plan = Plan(goal=goal, phases=new_phases)
            new_plan.current_phase_id = new_phases[0].id if new_phases else None
            if new_phases:
                new_phases[0].status = "in_progress"

            self.intention_pool.set_plan(new_plan)
            return f"Plan updated. Goal: {goal}. Phases: {len(new_phases)}."

        elif action == "advance":
            if not self.intention_pool.current_plan:
                return "Error: No active plan."

            self.intention_pool.current_plan.advance()
            current = self.intention_pool.current_plan.current_phase_id
            if current:
                return f"Advanced to phase {current}."
            else:
                return "Plan completed."

        elif action == "refine":
            if not self.intention_pool.current_plan:
                return "Error: No active plan."

            found = False
            for phase in self.intention_pool.current_plan.phases:
                if phase.id == phase_id:
                    phase.description = description
                    found = True
                    break

            if found:
                return f"Phase {phase_id} refined."
            else:
                return f"Error: Phase {phase_id} not found."

        else:
            return f"Error: Unknown action '{action}'."
