import pytest
import os
from app.agent.rlhf import FeedbackCollector
from app.agent.immunity import DigitalImmunitySystem
from app.agent.toolcall import ToolCallAgent
from app.agent.swarm import SwarmOrchestrator
from app.tool.delegate_tool import DelegateTool

def test_feedback_collector():
    collector = FeedbackCollector(storage_path="test_feedback.jsonl")
    if os.path.exists("test_feedback.jsonl"):
        os.remove("test_feedback.jsonl")

    feedback = collector.collect(
        session_id="123",
        task_id="abc",
        user_input="hello",
        agent_output="world",
        rating=5
    )

    assert feedback.rating == 5
    assert os.path.exists("test_feedback.jsonl")

    stats = collector.get_stats()
    assert stats["count"] == 1
    assert stats["avg_rating"] == 5.0

    os.remove("test_feedback.jsonl")

def test_digital_immunity_system():
    immunity = DigitalImmunitySystem()

    # Test normal call
    assert immunity.monitor_tool_call("test_tool", {"arg": 1}) == True

    # Test repetitive calls (history management)
    # We call it 3 times, history size becomes 3
    # If we call it a 4th time, it checks the last 3.
    # Wait, implementation:
    # call_signature = ...
    # history.append(call_signature)
    # if len > 3: check last 3.
    # So if we have 4 identical calls: [A, A, A, A]. Last 3 are [A, A, A]. All equal? Yes. Block.

    # Reset
    immunity = DigitalImmunitySystem()

    immunity.monitor_tool_call("repeat_tool", {"arg": 1}) # 1
    immunity.monitor_tool_call("repeat_tool", {"arg": 1}) # 2
    immunity.monitor_tool_call("repeat_tool", {"arg": 1}) # 3

    # 4th call should be blocked
    # History: [A, A, A, A] -> last 3: [A, A, A] -> Blocked.
    assert immunity.monitor_tool_call("repeat_tool", {"arg": 1}) == False

    # Test failure blocking
    immunity = DigitalImmunitySystem()
    for _ in range(6):
        immunity.record_failure("fail_tool")

    assert "fail_tool" in immunity.blocked_tools
    assert immunity.monitor_tool_call("fail_tool", {}) == False

@pytest.mark.asyncio
async def test_swarm_orchestrator_initialization():
    orchestrator = SwarmOrchestrator()
    assert orchestrator.name == "swarm_orchestrator"
    assert "delegate_task" in orchestrator.available_tools.tool_map

@pytest.mark.asyncio
async def test_delegate_tool():
    tool = DelegateTool()
    assert tool.name == "delegate_task"
