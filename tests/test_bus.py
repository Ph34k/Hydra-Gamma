import pytest
import asyncio
from app.agent.bus import MessageBus, AgentMessage, AgentRole

class TestMessageBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish_direct(self):
        bus = MessageBus()
        received_messages = []

        def callback(message: AgentMessage):
            received_messages.append(message)

        bus.subscribe("agent1", callback)

        msg = AgentMessage(sender="agent2", recipient="agent1", content="hello")
        await bus.publish(msg)

        assert len(received_messages) == 1
        assert received_messages[0] == msg
        assert received_messages[0].content == "hello"

    @pytest.mark.asyncio
    async def test_subscribe_and_publish_broadcast(self):
        bus = MessageBus()
        received_agent1 = []
        received_agent2 = []

        bus.subscribe("agent1", lambda m: received_agent1.append(m))
        bus.subscribe("agent2", lambda m: received_agent2.append(m))

        msg = AgentMessage(sender="agent3", recipient="all", content="broadcast")
        await bus.publish(msg)

        assert len(received_agent1) == 1
        assert len(received_agent2) == 1
        assert received_agent1[0].content == "broadcast"
        assert received_agent2[0].content == "broadcast"

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self):
        bus = MessageBus()
        received_agent1 = []

        bus.subscribe("agent1", lambda m: received_agent1.append(m))

        msg = AgentMessage(sender="agent1", recipient="all", content="broadcast")
        await bus.publish(msg)

        assert len(received_agent1) == 0

    @pytest.mark.asyncio
    async def test_async_callback(self):
        bus = MessageBus()
        received_messages = []

        async def async_callback(message: AgentMessage):
            await asyncio.sleep(0.01)
            received_messages.append(message)

        bus.subscribe("agent1", async_callback)

        msg = AgentMessage(sender="agent2", recipient="agent1", content="hello")
        await bus.publish(msg)

        assert len(received_messages) == 1

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_id(self):
        bus = MessageBus()
        count = 0

        def callback1(m): nonlocal count; count += 1
        def callback2(m): nonlocal count; count += 1

        bus.subscribe("agent1", callback1)
        bus.subscribe("agent1", callback2)

        msg = AgentMessage(sender="agent2", recipient="agent1", content="hello")
        await bus.publish(msg)

        assert count == 2

    @pytest.mark.asyncio
    async def test_get_history(self):
        bus = MessageBus()
        msg1 = AgentMessage(sender="a", recipient="b", content="1")
        msg2 = AgentMessage(sender="b", recipient="a", content="2")

        await bus.publish(msg1)
        await bus.publish(msg2)

        history = bus.get_history()
        assert len(history) == 2
        assert history[0] == msg1
        assert history[1] == msg2
