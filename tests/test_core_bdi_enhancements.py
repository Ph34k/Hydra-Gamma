import pytest
import datetime
import json
from unittest.mock import AsyncMock, MagicMock
from app.agent.bdi import BeliefSet, IntentionPool, Plan, PlanStep, Goal, Fact
from app.agent.reasoning import ReasoningEngine
from app.schema import Message

# Mock LLM
class MockLLM:
    def __init__(self):
        self.ask = AsyncMock()

@pytest.mark.asyncio
async def test_tree_of_thought_simulation():
    llm = MockLLM()
    engine = ReasoningEngine(llm)

    # Setup mock responses
    # 1. Generate Candidates
    # 2. Simulate & Evaluate
    llm.ask.side_effect = [
        "Option 1: Do A\nOption 2: Do B",
        "Option 1"
    ]

    context = "Goal: Fix a bug."
    best_option = await engine.tree_of_thought(context)

    assert best_option == "Option 1"
    assert llm.ask.call_count == 2

    # Verify the second call prompt contains "Simulate"
    call_args = llm.ask.call_args_list[1]
    prompt = call_args[0][0][0].content
    assert "Simulate the likely outcome" in prompt
    assert "Assign a feasibility score" in prompt

@pytest.mark.asyncio
async def test_refine_plan():
    llm = MockLLM()
    beliefs = BeliefSet()
    pool = IntentionPool()

    # Setup Plan
    plan = Plan(
        goal="Build App",
        phases=[
            PlanStep(id=1, title="Phase 1", description="Init", status="in_progress"),
            PlanStep(id=2, title="Phase 2", description="Code", status="pending")
        ],
        current_phase_id=1
    )
    pool.set_plan(plan)

    # Setup Mock Response for Refine
    # Expects JSON list of updates
    llm.ask.return_value = '[{"id": 2, "title": "Phase 2 Refined", "description": "Code with detail"}]'

    await pool.refine_plan(beliefs, llm)

    assert pool.current_plan.phases[1].title == "Phase 2 Refined"
    assert pool.current_plan.phases[1].description == "Code with detail"
    assert pool.current_plan.phases[0].title == "Phase 1" # Unchanged

@pytest.mark.asyncio
async def test_belief_summarization():
    llm = MockLLM()
    beliefs = BeliefSet(max_facts=3)

    # Add 3 facts
    await beliefs.add_fact("Fact 1", llm)
    await beliefs.add_fact("Fact 2", llm)
    await beliefs.add_fact("Fact 3", llm)

    assert len(beliefs.facts) == 3
    assert llm.ask.call_count == 0 # No summarization yet

    # Add 4th fact -> Trigger Summarization
    # Logic: num_to_summarize = 4 - 3 + 5 = 6. capped at 4//2 = 2.
    # So summarize first 2 facts.
    llm.ask.return_value = "Summary of 1 and 2"

    await beliefs.add_fact("Fact 4", llm)

    # Expected: [SummaryFact, Fact 3, Fact 4] -> Length 3
    assert len(beliefs.facts) == 3
    assert beliefs.facts[0].source == "summary"
    assert "Summary of 1 and 2" in beliefs.facts[0].content
    assert beliefs.facts[1].content == "Fact 3"
    assert beliefs.facts[2].content == "Fact 4"
    assert llm.ask.call_count == 1
