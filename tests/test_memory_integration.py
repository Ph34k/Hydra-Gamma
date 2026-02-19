import pytest
import os
import shutil
import time
from app.memory.semantic import SemanticMemory
from app.memory.episodic import EpisodicStore, Episode, Action
from app.memory.working import WorkingMemory
from app.memory.state import StateMonitor, AtomicState
from app.metrics.performance import PerformanceMonitor
from app.schema import Message
from app.tool.memory import MemorySearchTool

# Setup temporary directory for tests
TEST_DIR = "tests/temp_workspace"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    os.makedirs(TEST_DIR, exist_ok=True)
    yield
    # Cleanup
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

def test_semantic_memory():
    # Initialize with test collection
    mem = SemanticMemory(collection_name="test_semantic", persist_directory=f"{TEST_DIR}/db")

    # Index document
    mem.index_document("The sky is blue.", metadata={"category": "nature"})
    mem.index_document("Apples are red.", metadata={"category": "fruit"})

    # Search
    results = mem.search("color of sky")
    assert len(results) > 0
    assert "blue" in results[0]['content']

def test_episodic_store():
    store = EpisodicStore(collection_name="test_episodes", persist_directory=f"{TEST_DIR}/db")

    # Create Episode
    action = Action(tool_name="test_tool", arguments={"arg": 1}, result_summary="Success")
    episode = Episode(
        goal="Test Goal",
        actions=[action],
        outcome="success",
        reflection="Test Reflection"
    )

    # Save
    store.save_episode(episode)

    # Find Similar
    similar = store.find_similar_episodes("Test Goal")
    assert len(similar) > 0
    # Note: We check if content is retrieved (which is reflection + goal)
    # The dummy reconstruction in find_similar_episodes puts content in reflection
    assert "Test Goal" in similar[0].reflection or "Test Goal" in similar[0].goal

def test_working_memory():
    wm = WorkingMemory()
    wm.set_subgoal("Analyze data")
    wm.update_state("USER", "test_user")
    wm.add_message(Message.user_message("Hello"))

    context = wm.get_active_context()
    assert "CURRENT GOAL: ANALYZE DATA" in context or "CURRENT GOAL (Active Subtask)" in context
    assert "USER: test_user" in context

def test_state_monitor():
    monitor = StateMonitor()
    snapshot = monitor.get_snapshot()
    assert "pwd" in snapshot
    assert "ls" in snapshot
    assert "env" in snapshot

def test_atomic_state():
    filepath = f"{TEST_DIR}/state.json"
    data = {"key": "value"}
    AtomicState.save(filepath, data)
    assert os.path.exists(filepath)

    import json
    with open(filepath, 'r') as f:
        loaded = json.load(f)
    assert loaded["key"] == "value"

def test_performance_monitor():
    pm = PerformanceMonitor()
    pm.record_tool_call("tool1", True, 0.5)
    pm.record_token_usage(100, 50)

    summary = pm.get_summary()
    assert summary["total_steps"] == 0 # No step recorded yet
    assert summary["total_tokens"] == 150
    assert summary["tool_failure_rate"] == 0.0

def test_memory_injection():
    mem = SemanticMemory(collection_name="test_injection", persist_directory=f"{TEST_DIR}/db")
    tool = MemorySearchTool()
    tool.set_memory(mem)
    assert tool.memory is mem
