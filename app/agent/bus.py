from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel
from enum import Enum
import asyncio

class AgentRole(Enum):
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"

class AgentMessage(BaseModel):
    sender: str
    recipient: str
    content: str
    message_type: str = "text" # text, code, plan, etc.
    metadata: Dict[str, Any] = {}

class MessageBus:
    """A simple in-memory message bus for agent communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        self._history: List[AgentMessage] = []

    def subscribe(self, agent_id: str, callback: Callable[[AgentMessage], None]):
        """Register a callback for messages addressed to agent_id."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    async def publish(self, message: AgentMessage):
        """Send a message to the recipient."""
        self._history.append(message)

        # Deliver to specific recipient
        if message.recipient in self._subscribers:
            for callback in self._subscribers[message.recipient]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)

        # Broadcast (optional, if recipient is "all")
        if message.recipient == "all":
            for agent_id, callbacks in self._subscribers.items():
                if agent_id != message.sender:
                    for callback in callbacks:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)

    def get_history(self) -> List[AgentMessage]:
        return self._history
