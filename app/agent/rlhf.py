import json
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Feedback(BaseModel):
    session_id: str
    task_id: str
    user_input: str
    agent_output: str
    rating: int = Field(..., ge=1, le=5) # 1-5 stars
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class FeedbackCollector:
    """
    Implements the Data Collection part of the RLHF loop (Chapter 47).
    Saves feedback for future model fine-tuning.
    """
    def __init__(self, storage_path: str = "feedback_data.jsonl"):
        self.storage_path = storage_path

    def collect(self, session_id: str, task_id: str, user_input: str, agent_output: str, rating: int, comment: str = None):
        feedback = Feedback(
            session_id=session_id,
            task_id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            rating=rating,
            comment=comment
        )
        self._save(feedback)
        return feedback

    def _save(self, feedback: Feedback):
        with open(self.storage_path, "a") as f:
            f.write(feedback.model_dump_json() + "\n")

    def get_stats(self):
        # Simple stats for monitoring
        count = 0
        avg_rating = 0.0
        if not os.path.exists(self.storage_path):
            return {"count": 0, "avg_rating": 0.0}

        try:
            total_rating = 0
            with open(self.storage_path, "r") as f:
                for line in f:
                    data = json.loads(line)
                    total_rating += data["rating"]
                    count += 1
            if count > 0:
                avg_rating = total_rating / count
        except Exception:
            pass

        return {"count": count, "avg_rating": avg_rating}
