import asyncio
import datetime
import os
import time
import json
from typing import Dict, List, Optional, Any
from pydantic import Field, model_validator
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type
)

from app.agent.toolcall import ToolCallAgent
from app.agent.reasoning import ReasoningEngine
from app.agent.memory import ContextManager
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message
from app.agent.bdi import BeliefSet, GoalSet, IntentionPool, Plan, Phase, PlanStep

# New Memory Components
from app.memory.working import WorkingMemory
from app.memory.semantic import SemanticMemory
from app.memory.episodic import EpisodicStore, Episode, Action
from app.memory.state import StateMonitor, AtomicState
from app.metrics.performance import PerformanceMonitor
from app.tool.memory import MemorySearchTool

# New Intelligence & Architecture Components
from app.agent.router import Router, TaskPhase
from app.agent.budget import BudgetManager
from app.agent.recovery import RecoveryManager, RecoveryStrategy
from app.tool.planning import PlanningTool


class AgentCore(ToolCallAgent):
    """
    Implements the BDI (Belief-Desire-Intention) Agent Core architecture.
    Ref: Chapter 1.2 of the Technical Bible.
    """

    name: str = "AgentCore"
    description: str = "Core BDI Agent implementation"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # BDI Components (Chapter 1.1)
    beliefs: BeliefSet = Field(default_factory=BeliefSet)
    goals: GoalSet = Field(default_factory=GoalSet)
    intentions: IntentionPool = Field(default_factory=IntentionPool)

    # Memory Architecture (Chapter 4 & 8)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    semantic_memory: Optional[SemanticMemory] = None
    episodic_store: Optional[EpisodicStore] = None

    # Monitors (Chapter 11 & 12)
    state_monitor: Optional[StateMonitor] = None
    performance_monitor: Optional[PerformanceMonitor] = None

    # Intelligence Components (Chapter 13)
    router: Optional[Router] = None
    budget_manager: Optional[BudgetManager] = None
    recovery_manager: Optional[RecoveryManager] = None

    # Reasoning & Memory
    reasoning_engine: Optional[ReasoningEngine] = None
    context_manager: Optional[ContextManager] = None

    # Persistence
    session_id: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    )

    # Planning Tool Reference
    planning_tool: Optional[PlanningTool] = None

    # Current Episode Tracking
    current_episode_actions: List[Action] = Field(default_factory=list)

    @model_validator(mode="after")
    def initialize_core_components(self) -> "AgentCore":
        """Initialize BDI and Core components."""
        if hasattr(self, 'llm') and self.llm:
            self.reasoning_engine = ReasoningEngine(self.llm)
            self.context_manager = ContextManager(self.llm)

        # Initialize Monitors
        self.state_monitor = StateMonitor()
        self.performance_monitor = PerformanceMonitor()

        # Initialize Intelligence
        self.router = Router()
        self.budget_manager = BudgetManager(limits={"default": 100.0})
        self.recovery_manager = RecoveryManager()

        # Initialize Memories
        try:
            self.semantic_memory = SemanticMemory()
            self.episodic_store = EpisodicStore()

            # Inject Semantic Memory into MemorySearchTool if available
            if self.available_tools:
                mem_tool = self.available_tools.tool_map.get("memory_search")
                if mem_tool and isinstance(mem_tool, MemorySearchTool):
                    mem_tool.set_memory(self.semantic_memory)

                # Get reference to PlanningTool
                plan_tool = self.available_tools.tool_map.get("planning")
                if plan_tool and isinstance(plan_tool, PlanningTool):
                    self.planning_tool = plan_tool
        except Exception as e:
            logger.warning(f"Memory components failed to initialize: {e}")

        return self

    def _get_environment_snapshot(self) -> Dict[str, Any]:
        """Capture the current state of the environment."""
        if self.state_monitor:
            return self.state_monitor.get_snapshot()

        snapshot = {}
        try:
            snapshot["pwd"] = os.getcwd()
            snapshot["ls"] = os.listdir(os.getcwd())[:20]
            snapshot["env"] = {
                k: v for k, v in os.environ.items()
                if k in ["USER", "HOME", "PATH", "LANG"]
            }
        except Exception as e:
            logger.error(f"Failed to get environment snapshot: {e}")
        return snapshot

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((TimeoutError, Exception))
    )
    async def think_with_retry(self) -> bool:
        """Wrapper for think with retry logic."""
        return await super().think()

    async def think(self) -> bool:
        """
        Execute the BDI Reasoning Loop (Chapter 1.3).
        1. Perception
        2. Deliberation
        3. Planning
        4. Execution (Delegated to act())
        """
        start_time = time.time()

        # Ensure helper components are initialized
        if not self.reasoning_engine and self.llm:
            self.reasoning_engine = ReasoningEngine(self.llm)
        if not self.context_manager and self.llm:
            self.context_manager = ContextManager(self.llm)

        # 0. Context Management (Chapter 4)
        if self.context_manager:
            await self.context_manager.manage_context(self.memory)

        # 0.5 Budget Check (Chapter 13.5)
        if self.budget_manager:
            try:
                self.budget_manager.check_budget("default", 0.05)
            except Exception as e:
                logger.warning(f"Budget check failed: {e}")

        # 1. Perception: Sync Beliefs (Chapter 1.3.1)
        if self.state_monitor and self.state_monitor.check_heartbeat():
            snapshot = self.state_monitor.get_snapshot()
            self.beliefs.sync_with_environment(snapshot)
            for k, v in snapshot.items():
                self.working_memory.update_state(k, v)
        else:
            snapshot = self._get_environment_snapshot()
            self.beliefs.sync_with_environment(snapshot)
            for k, v in snapshot.items():
                self.working_memory.update_state(k, v)

        # Sync Plan from PlanningTool
        if self.planning_tool:
            plan_data = self.planning_tool.get_active_plan_data()
            if plan_data:
                phases = []
                for i, step_text in enumerate(plan_data['steps']):
                    statuses = plan_data.get('step_statuses', [])
                    status = statuses[i] if i < len(statuses) else "pending"
                    if status == "not_started":
                        status = "pending"

                    phases.append(PlanStep(
                        id=i + 1,
                        title=step_text[:50],
                        description=step_text,
                        status=status
                    ))

                new_plan = Plan(goal=plan_data['title'], phases=phases)
                for phase in phases:
                    if phase.status == "in_progress":
                        new_plan.current_phase_id = phase.id
                        break

                self.intentions.set_plan(new_plan)

        # 2. Deliberation: Decide on Desires (Goals)
        if not self.goals.active_goals and self.memory.messages:
            last_user_msg = next(
                (m for m in reversed(self.memory.messages) if m.role == "user"),
                None
            )
            if last_user_msg:
                self.goals.add_goal(last_user_msg.content)
                self.goals.get_active_goal()  # Activate it

        active_goal = self.goals.get_active_goal()
        if active_goal:
            self.working_memory.set_subgoal(active_goal.description)

            # Few-Shot Injection (Chapter 10)
            if self.episodic_store and not self.working_memory.scratchpad:
                examples = self.episodic_store.get_formatted_examples(
                    active_goal.description
                )
                if examples:
                    self.working_memory.scratchpad += (
                        f"\n\n[Memory Injection]\n{examples}"
                    )

        # 3. Planning: Generate/Refine Intentions
        current_plan_json = (
            self.intentions.current_plan.model_dump_json()
            if self.intentions.current_plan
            else "No active plan."
        )

        plan_notification = ""
        if not self.intentions.current_plan and self.goals.active_goals:
            plan_notification = (
                "\n\n[System Notification]\nYou have an active goal but no "
                "plan. You MUST use the `planning` tool (command: create) to "
                "create a plan before proceeding."
            )
        elif self.intentions.current_plan:
            await self.intentions.refine_plan(self.beliefs, self.llm)

        # Sync History to Working Memory
        self.working_memory.recent_history = self.memory.messages[-10:]

        # Construct Context
        working_memory_context = self.working_memory.get_active_context()
        bdi_context = f"""
{working_memory_context}

Current Plan:
{current_plan_json}
"""
        # Reasoning Engine (Chapter 3)
        reasoning_strategy_output = ""
        if self.reasoning_engine:
            context_for_reasoning = (
                f"{bdi_context}\n\nLast User Message: "
                f"{self.memory.messages[-1].content if self.memory.messages else ''}"
            )
            reasoning_result = await self.reasoning_engine.decide_strategy(
                context_for_reasoning
            )
            reasoning_strategy_output = (
                f"\n\nReasoning Engine Output:\n{reasoning_result}"
            )

        # Model Routing (Chapter 13)
        if self.router:
            phase = TaskPhase.PLANNING
            if self.intentions.current_phase == Phase.PERCEPTION:
                phase = TaskPhase.PLANNING
            elif self.intentions.current_phase == Phase.ACTION:
                phase = TaskPhase.CODING

            selected_tier = self.router.route(
                phase, len(bdi_context), self.session_id
            )
            logger.info(f"Router selected model tier: {selected_tier}")

            config_name = self.router.get_config_for_tier(selected_tier)
            try:
                from app.llm import LLM
                # Switch model config
                self.llm = LLM(config_name=config_name)
                # Update components
                if self.reasoning_engine:
                    self.reasoning_engine.llm = self.llm
                if self.context_manager:
                    self.context_manager.llm = self.llm
            except Exception as e:
                logger.warning(f"Failed to switch model to {config_name}: {e}")

        # Update Prompt
        original_prompt = self.next_step_prompt
        self.next_step_prompt = (
            f"{original_prompt}\n\n{bdi_context}"
            f"{reasoning_strategy_output}{plan_notification}"
        )

        try:
            # Delegate to ToolCallAgent.think
            result = await self.think_with_retry()

            if self.performance_monitor:
                self.performance_monitor.record_step_duration(
                    time.time() - start_time
                )

            return result
        finally:
            self.next_step_prompt = original_prompt

    async def act(self) -> str:
        """Execute actions and update beliefs (Chapter 1.3 step 4 & 5)."""
        start_time = time.time()
        current_calls = self.tool_calls

        try:
            result = await super().act()
            success = True
            error_msg = None
        except Exception as e:
            error_msg = str(e)
            success = False

            # Recovery Logic
            if self.recovery_manager and current_calls:
                # Analyze the first tool call that likely caused the error
                failed_tool = current_calls[0].function.name
                failed_args = json.loads(
                    current_calls[0].function.arguments or "{}"
                )

                recovery_plan = self.recovery_manager.analyze_error(
                    error_msg, failed_tool, failed_args
                )
                logger.warning(
                    f"Recovery Plan Triggered: {recovery_plan.category} "
                    f"-> {recovery_plan.strategy}"
                )

                if recovery_plan.strategy == RecoveryStrategy.RETRY:
                    result = (
                        f"Error: {error_msg}\n[System Advice]: "
                        f"{recovery_plan.reasoning}"
                    )

                elif recovery_plan.strategy == RecoveryStrategy.RETRY_WITH_DELAY:
                    await asyncio.sleep(5)  # Exponential backoff placeholder
                    result = (
                        f"Error: {error_msg}\n[System Advice]: Operation "
                        f"timed out. Paused for 5s. {recovery_plan.reasoning}"
                    )

                elif recovery_plan.strategy == RecoveryStrategy.MODIFY_ARGS:
                    result = (
                        f"Error: {error_msg}\n[System Advice]: "
                        f"{recovery_plan.reasoning}"
                    )

                elif recovery_plan.strategy == RecoveryStrategy.ASK_USER:
                    result = (
                        f"Error: {error_msg}\n[System Advice]: CRITICAL "
                        "FAILURE. Please ask the user for help."
                    )
                else:
                    result = f"Error: {error_msg}"
            else:
                result = f"Error: {error_msg}"

            if self.router:
                self.router.report_failure(self.session_id)

        duration = time.time() - start_time

        # Metrics & Episode Tracking
        if current_calls:
            for call in current_calls:
                if self.performance_monitor:
                    self.performance_monitor.record_tool_call(
                        tool_name=call.function.name,
                        success=success,
                        duration=duration,
                        error=error_msg
                    )
                action = Action(
                    tool_name=call.function.name,
                    arguments=json.loads(call.function.arguments or "{}"),
                    result_summary=str(result)[:200]
                )
                self.current_episode_actions.append(action)

        # 5. Observation
        await self.beliefs.update_from_observation(result, self.llm)
        self.working_memory.add_observation(result)

        # 6. Evaluate Progress
        is_satisfied = await self.goals.is_satisfied(self.beliefs, self.llm)
        if is_satisfied:
            logger.info("All active goals satisfied.")
            self.state = AgentState.FINISHED
            self.memory.add_message(Message.assistant_message("Task Completed"))

            if self.episodic_store and self.current_episode_actions:
                active_goal = self.goals.get_active_goal()
                goal_desc = (
                    active_goal.description if active_goal else "Unknown Goal"
                )
                episode = Episode(
                    goal=goal_desc,
                    actions=self.current_episode_actions,
                    outcome="success",
                    reflection="Task completed successfully.",
                    timestamp=datetime.datetime.now()
                )
                self.episodic_store.save_episode(episode)
                self.current_episode_actions = []

            return "Task Completed"

        await self.save_state()
        return result

    async def save_state(self, filepath: Optional[str] = None) -> None:
        """Serialize and save state (Chapter 11.5)."""
        if not filepath:
            filepath = f"session_{self.session_id}.json"

        state_data = {
            "session_id": self.session_id,
            "status": (
                self.state.value if hasattr(self.state, "value")
                else str(self.state)
            ),
            "history": [msg.model_dump() for msg in self.memory.messages],
            "plan": (
                self.intentions.current_plan.model_dump()
                if self.intentions.current_plan else None
            ),
            "beliefs": self.beliefs.model_dump(),
            "goals": self.goals.model_dump(),
            "working_memory": self.working_memory.model_dump(),
        }

        try:
            AtomicState.save(filepath, state_data)
            logger.info(f"Session state saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def load_state(self, filepath: Optional[str] = None) -> None:
        """Load state from file."""
        if not filepath:
            filepath = f"session_{self.session_id}.json"

        try:
            if not os.path.exists(filepath):
                return
            with open(filepath, 'r') as f:
                state_data = json.load(f)

            self.session_id = state_data.get("session_id", self.session_id)
            if "history" in state_data:
                self.memory.messages = [
                    Message(**msg) for msg in state_data["history"]
                ]
            if "beliefs" in state_data:
                self.beliefs = BeliefSet(**state_data["beliefs"])
            if "goals" in state_data:
                self.goals = GoalSet(**state_data["goals"])
            if "plan" in state_data and state_data["plan"]:
                self.intentions.set_plan(Plan(**state_data["plan"]))
            if "working_memory" in state_data:
                self.working_memory = WorkingMemory(
                    **state_data["working_memory"]
                )
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
