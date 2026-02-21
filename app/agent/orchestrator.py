import asyncio
import uuid
import os
import json
from typing import Dict, Optional, Any
from pydantic import BaseModel

from app.agent.bus import MessageBus, AgentMessage, AgentRole
from app.agent.manus import Manus
from app.logger import logger

class SessionState(BaseModel):
    session_id: str
    status: str
    agent_state_path: str

class Orchestrator:
    """
    Central Orchestrator (Chapter 2) responsible for:
    - Managing agent sessions
    - Dispatching tasks/commands to the active agent
    - Managing state persistence and recovery
    - Coordinating multi-agent communication (via MessageBus)
    """

    def __init__(self):
        self.message_bus = MessageBus()
        self.active_sessions: Dict[str, Manus] = {}
        self.session_states: Dict[str, SessionState] = {}
        self.storage_path = "workspace/sessions"
        os.makedirs(self.storage_path, exist_factory=True)

    async def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new agent session."""
        if not session_id:
            session_id = str(uuid.uuid4())

        # Initialize a new Manus agent
        agent = await Manus.create(session_id=session_id)
        self.active_sessions[session_id] = agent

        self.session_states[session_id] = SessionState(
            session_id=session_id,
            status="active",
            agent_state_path=os.path.join(self.storage_path, f"session_{session_id}.json")
        )
        logger.info(f"Created new session: {session_id}")
        return session_id

    async def restore_session(self, session_id: str) -> bool:
        """Restore an existing session from disk."""
        filepath = os.path.join(self.storage_path, f"session_{session_id}.json")
        if not os.path.exists(filepath):
            logger.warning(f"Session file {filepath} not found.")
            return False

        agent = await Manus.create(session_id=session_id)
        await agent.load_state(filepath)
        self.active_sessions[session_id] = agent

        self.session_states[session_id] = SessionState(
            session_id=session_id,
            status="restored",
            agent_state_path=filepath
        )
        logger.info(f"Restored session: {session_id}")
        return True

    async def run_step(self, session_id: str, user_input: Optional[str] = None) -> str:
        """Execute a single step (or run until completion) for the given session."""
        agent = self.active_sessions.get(session_id)
        if not agent:
            raise ValueError(f"Session {session_id} not found or not active.")

        try:
            # Delegate execution to the agent's run loop
            # Note: agent.run() runs until completion or max_steps.
            # Ideally, Orchestrator should control the loop step-by-step for finer control,
            # but reusing agent.run() is simpler for now.
            if user_input:
                result = await agent.run(user_input)
            else:
                # Resume execution without new input (e.g., after tool output)
                result = await agent.run()

            return result
        except Exception as e:
            logger.error(f"Error in session {session_id}: {e}")
            raise e
        finally:
            # Ensure state is saved after execution
            await agent.save_state(self.session_states[session_id].agent_state_path)

    async def terminate_session(self, session_id: str):
        """Clean up and terminate a session."""
        agent = self.active_sessions.get(session_id)
        if agent:
            await agent.cleanup()
            del self.active_sessions[session_id]
            if session_id in self.session_states:
                self.session_states[session_id].status = "terminated"
            logger.info(f"Terminated session: {session_id}")

    # Legacy Multi-Agent Support (kept for compatibility)
    def register_agent(self, agent_id: str, role: AgentRole, agent_instance: Any):
        # Implementation for multi-agent swarm registration
        pass

    async def dispatch_task(self, task_description: str):
        # Implementation for multi-agent task dispatch
        pass
