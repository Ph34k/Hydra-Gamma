from typing import List, Optional
from app.llm import LLM
from app.schema import Message
from app.logger import logger

class ContextManager:
    def __init__(self, llm: LLM, max_tokens: int = 8000, summary_threshold: float = 0.8):
        self.llm = llm
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold

    def _count_tokens(self, messages: List[Message]) -> int:
        # Convert Message objects to dicts for the tokenizer if needed, or use LLM's counter
        return self.llm.count_message_tokens([m.model_dump() for m in messages])

    async def summarize_history(self, messages: List[Message]) -> List[Message]:
        """Summarize older messages to save tokens."""
        if not messages:
            return []

        # Heuristic: Summarize the first 50% of messages
        split_idx = len(messages) // 2
        to_summarize = messages[:split_idx]
        kept_messages = messages[split_idx:]

        summary_prompt = f"""
        Summarize the following conversation history concisely.
        Focus on actions taken, key discoveries, and current state.
        Ignore minor details.

        History:
        {json.dumps([m.model_dump() for m in to_summarize], default=str)}
        """

        try:
            summary = await self.llm.ask([Message.user_message(summary_prompt)], stream=False)
            logger.info("Context summarized.")
            return [Message.system_message(f"Previous interactions summary: {summary}")] + kept_messages
        except Exception as e:
            logger.error(f"Failed to summarize history: {e}")
            return messages # Fallback

    def prune_tool_outputs(self, messages: List[Message]) -> List[Message]:
        """Truncate large tool outputs (HTML, logs)."""
        pruned_messages = []
        for msg in messages:
            if msg.role == "tool" and msg.content and len(msg.content) > 2000:
                # Truncate content
                msg.content = msg.content[:2000] + "... [Content Truncated]"
            pruned_messages.append(msg)
        return pruned_messages

    async def manage_context(self, memory) -> None:
        """Monitor and optimize context usage."""
        current_tokens = self._count_tokens(memory.messages)
        if current_tokens > self.max_tokens * self.summary_threshold:
            logger.warning(f"Token usage {current_tokens} exceeds threshold. Optimizing context...")

            # 1. Prune verbose outputs first
            memory.messages = self.prune_tool_outputs(memory.messages)

            # 2. Re-check tokens
            current_tokens = self._count_tokens(memory.messages)
            if current_tokens > self.max_tokens * self.summary_threshold:
                # 3. Summarize if still too high
                memory.messages = await self.summarize_history(memory.messages)

import json
