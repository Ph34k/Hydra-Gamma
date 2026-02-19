from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import json
import datetime
from app.schema import Message
from app.logger import logger

class WorkingMemory(BaseModel):
    """
    Manages short-term memory (Working Memory) for the agent.
    Includes Recent History, Current State, Active Subgoal, and Attention Mechanisms.
    """
    recent_history: List[Message] = Field(default_factory=list)
    current_state: Dict[str, Any] = Field(default_factory=dict)
    active_subgoal: Optional[str] = None
    scratchpad: str = "" # Chapter 8.5 Scratchpad

    # Configuration
    max_history_tokens: int = 4000

    def add_message(self, message: Message):
        self.recent_history.append(message)
        self.prune_old_data()

    def add_observation(self, observation: str):
        """Add an observation from the environment or tool output."""
        # Typically this would be added as a tool message to history
        msg = Message.tool_message(content=observation, tool_call_id="observation", name="environment")
        self.add_message(msg)

    def update_state(self, key: str, value: Any):
        self.current_state[key] = value

    def set_subgoal(self, subgoal: str):
        self.active_subgoal = subgoal

    def get_active_context(self) -> str:
        """
        Constructs the Active Context Prompt for the LLM.
        Implements Attention Mechanism (Pinning, Highlighting).
        """
        context_parts = []

        # 1. Pinning: Main Goal / Active Subgoal always at top
        if self.active_subgoal:
            context_parts.append(f"### CURRENT GOAL (Active Subtask)\n{self.active_subgoal.upper()}\n")

        # 2. Context Injection: Environment State
        if self.current_state:
            env_str = "### ENVIRONMENT STATE\n"
            for k, v in self.current_state.items():
                env_str += f"- {k}: {v}\n"
            context_parts.append(env_str)

        # 3. Scratchpad
        if self.scratchpad:
            context_parts.append(f"### SCRATCHPAD\n{self.scratchpad}\n")

        # 4. Recent Results (Output of last tool calls) - Highlighting
        # We find the last few tool outputs in history
        recent_tool_outputs = [m for m in self.recent_history if m.role == 'tool'][-3:]
        if recent_tool_outputs:
             context_parts.append("### RECENT RESULTS (Attention Mechanism)")
             for m in recent_tool_outputs:
                 content = m.content or ""
                 # Highlighting: Bold for errors
                 if "error" in content.lower() or "exception" in content.lower() or "fail" in content.lower():
                     context_parts.append(f"**ERROR DETECTED**: {content[:500]}...")
                 else:
                     context_parts.append(f"Result: {content[:300]}...")

        return "\n\n".join(context_parts)

    def prune_old_data(self, token_limit: int = None):
        """
        Prunes history to keep within token limits.
        Simple FIFO pruning for now.
        """
        if token_limit is None:
            token_limit = self.max_history_tokens

        # Placeholder for real token counting. Assuming approx 4 chars per token.
        current_len = sum(len(m.content or "") for m in self.recent_history)
        while current_len > token_limit * 4 and len(self.recent_history) > 1:
            removed = self.recent_history.pop(0)
            current_len -= len(removed.content or "")

    def clear_logs(self):
        """Chapter 8.6: Clear intermediate logs after sub-task completion."""
        # Keep only the last few messages or summarize
        pass
