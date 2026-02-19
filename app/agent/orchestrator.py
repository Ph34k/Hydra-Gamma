import asyncio
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from app.agent.bus import MessageBus, AgentMessage, AgentRole

class TaskStatus(BaseModel):
    id: str
    status: str # pending, running, completed, failed
    result: Optional[str] = None

class Orchestrator:
    """Manages the lifecycle of multiple agents and their communication."""

    def __init__(self):
        self.message_bus = MessageBus()
        self.agents: Dict[str, Any] = {} # agent_id -> agent_instance
        self.tasks: Dict[str, TaskStatus] = {}

    def register_agent(self, agent_id: str, role: AgentRole, agent_instance: Any):
        """Register an agent with the orchestrator."""
        self.agents[agent_id] = agent_instance
        # Register a callback for this agent to receive messages
        # In a real implementation, the agent_instance would have a method like `receive_message`
        # For now, we simulate this callback

        async def message_handler(message: AgentMessage):
             if hasattr(agent_instance, 'receive_message'):
                 await agent_instance.receive_message(message)

        self.message_bus.subscribe(agent_id, message_handler)

    async def dispatch_task(self, task_description: str):
        """Assigns a task to the Architect agent to start the workflow."""
        # This is a simplified flow: Architect -> Developer -> Reviewer

        architect_id = self._find_agent_by_role(AgentRole.ARCHITECT)
        if not architect_id:
            raise RuntimeError("No Architect agent available.")

        initial_message = AgentMessage(
            sender="orchestrator",
            recipient=architect_id,
            content=task_description,
            message_type="task_assignment"
        )
        await self.message_bus.publish(initial_message)

    def _find_agent_by_role(self, role: AgentRole) -> Optional[str]:
        # This assumes we store role in agent instance or separately.
        # For simplicity, let's assume agent_id implies role or we pass metadata
        for agent_id, agent in self.agents.items():
            if getattr(agent, 'role', None) == role:
                return agent_id
        return None
