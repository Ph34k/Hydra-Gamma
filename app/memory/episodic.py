import uuid
import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.logger import logger
from app.memory.semantic import SemanticMemory
from app.utils.sanitizer import Sanitizer

class Action(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result_summary: str

class Episode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    actions: List[Action]
    outcome: str = "unknown" # success, failure
    reflection: str = ""
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)

class EpisodicStore:
    def __init__(self, collection_name: str = "manus_episodes", persist_directory: str = "workspace/db"):
        # We reuse the semantic memory infrastructure but with a different collection
        self.memory = SemanticMemory(collection_name=collection_name, persist_directory=persist_directory)

    def save_episode(self, episode: Episode):
        """Save a complete episode to memory."""
        # We store the episode structure as JSON string in the document content
        # But for search, we index the 'goal' as the primary embedding source
        try:
            # Prepare metadata
            metadata = {
                "outcome": episode.outcome,
                "timestamp": str(episode.timestamp),
                "action_count": len(episode.actions)
            }

            # Sanitization (Chapter 10.6)
            sanitized_episode = Sanitizer.sanitize(episode.model_dump())

            # Let's format the content as a "story" or "log" which is good for LLM context.
            episode_text = f"Goal: {sanitized_episode['goal']}\n"
            for action in sanitized_episode['actions']:
                episode_text += f"- Action: {action['tool_name']}({str(action['arguments'])[:50]}...)\n"
                episode_text += f"  Result: {action['result_summary'][:100]}...\n"
            episode_text += f"Outcome: {sanitized_episode['outcome']}\nReflection: {sanitized_episode['reflection']}"

            self.memory.index_document(text=episode_text, metadata=metadata, source="episodic_store")
            logger.info(f"Episode saved: {episode.id}")

        except Exception as e:
            logger.error(f"Failed to save episode: {e}")

    def find_similar_episodes(self, current_goal: str, n_results: int = 3) -> List[Episode]:
        """Find past episodes similar to the current goal."""
        results = self.memory.search(current_goal, n_results=n_results)
        episodes = []
        for res in results:
            # We need to reconstruct the Episode object or at least return relevant text
            # Since we stored text, we can return the text directly for context injection
            # If we need the structured object, we'd need to parse it back or fetch from external storage.
            # For "Few-Shot Dynamic", the text representation is usually sufficient.

            # Creating a dummy episode object from the text for now
            # In a real system, we'd fetch the full JSON from a KV store using the ID.
            ep = Episode(
                id=res['id'],
                goal=current_goal, # approximate
                actions=[], # details in text
                outcome=res['metadata'].get('outcome', 'unknown'),
                reflection=res['content'], # crude mapping
                timestamp=datetime.datetime.now()
            )
            episodes.append(ep)
        return episodes

    def get_formatted_examples(self, current_goal: str) -> str:
        """Retrieve and format similar episodes for prompt injection."""
        results = self.memory.search(current_goal, n_results=2)
        if not results:
            return ""

        examples = "Here are similar tasks you have completed in the past:\n\n"
        for res in results:
            if res['metadata'].get('outcome') == 'success':
                 examples += f"---\n{res['content']}\n---\n"
        return examples
