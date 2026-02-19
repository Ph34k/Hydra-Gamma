import unittest
import asyncio
import sys
from typing import List
from unittest.mock import MagicMock

# Mock app.agent.browser to avoid importing Daytona
sys.modules['app.agent.browser'] = MagicMock()
sys.modules['app.daytona'] = MagicMock()
sys.modules['app.daytona.sandbox'] = MagicMock()

from app.agent.bus import AgentMessage, AgentRole, MessageBus

class MockAgent:
    """Mock agent for testing inter-agent communication."""
    def __init__(self, agent_id: str, role: AgentRole, message_bus: MessageBus):
        self.id = agent_id
        self.role = role
        self.bus = message_bus
        self.inbox: List[AgentMessage] = []
        self.bus.subscribe(agent_id, self.receive_message)

    async def receive_message(self, message: AgentMessage):
        """Simulate receiving a message."""
        self.inbox.append(message)

        # Simple Reactive Logic
        if message.sender == "orchestrator" and "task_assignment" in message.message_type:
            # Architect receives task, delegates to Developer
            if self.role == AgentRole.ARCHITECT:
                response = AgentMessage(
                    sender=self.id,
                    recipient="dev_1",
                    content=f"Please implement: {message.content}",
                    message_type="delegation"
                )
                await self.bus.publish(response)

        elif message.sender == "architect_1" and self.role == AgentRole.DEVELOPER:
             # Developer receives task, reports completion
             response = AgentMessage(
                 sender=self.id,
                 recipient="architect_1",
                 content="Implemented!",
                 message_type="completion"
             )
             await self.bus.publish(response)

class TestMultiAgent(unittest.TestCase):

    def test_message_flow(self):
        async def run_flow():
            bus = MessageBus()

            architect = MockAgent("architect_1", AgentRole.ARCHITECT, bus)
            developer = MockAgent("dev_1", AgentRole.DEVELOPER, bus)

            # 1. Orchestrator sends task to Architect
            initial_msg = AgentMessage(
                sender="orchestrator",
                recipient="architect_1",
                content="Build a login page",
                message_type="task_assignment"
            )
            await bus.publish(initial_msg)

            # In a fully synchronous callback loop (because await is used inside publish),
            # by the time publish returns, all cascading messages might have been processed.

            # Check Architect received task + completion (because completion happens after delegation)
            # The order of execution:
            # 1. Orchestrator calls publish(msg1)
            # 2. Architect receives msg1 -> calls publish(msg2)
            # 3. Developer receives msg2 -> calls publish(msg3)
            # 4. Architect receives msg3
            # All this happens before the first `await bus.publish(initial_msg)` returns!

            self.assertEqual(len(architect.inbox), 2)
            self.assertEqual(architect.inbox[0].content, "Build a login page")
            self.assertEqual(architect.inbox[1].content, "Implemented!")

            # Check Developer received delegation
            self.assertEqual(len(developer.inbox), 1)
            self.assertEqual(developer.inbox[0].content, "Please implement: Build a login page")

        asyncio.run(run_flow())

if __name__ == '__main__':
    unittest.main()
