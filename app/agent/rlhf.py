import json
import os
import uuid
import random
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.logger import logger

class Feedback(BaseModel):
    session_id: str
    task_id: str
    user_input: str
    agent_output: str
    rating: int = Field(..., ge=1, le=5) # 1-5 stars
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class RewardModel:
    """
    Simulates a Reward Model (Chapter 47.2).
    In a real system, this would be a trained transformer model.
    """
    def __init__(self, model_path: str = "reward_model.pt"):
        self.model_path = model_path
        self.version = "1.0.0"

    def predict_reward(self, user_input: str, agent_output: str) -> float:
        """
        Predict reward score for a given input-output pair.
        Returns a float between -1.0 and 1.0.
        """
        # Mock implementation: random score based on length heuristic + noise
        heuristic = min(len(agent_output) / 500.0, 1.0) # Prefer slightly longer detailed answers
        noise = random.uniform(-0.1, 0.1)
        return max(-1.0, min(1.0, heuristic + noise))

    def train(self, feedbacks: list[Feedback]):
        """Update the reward model based on human feedback."""
        logger.info(f"RewardModel: Training on {len(feedbacks)} feedback samples.")
        # Simulate training delay
        pass

class RLHFOptimizer:
    """
    Simulates the Policy Optimization step (e.g., PPO).
    """
    def __init__(self, learning_rate: float = 1e-5):
        self.learning_rate = learning_rate

    def step(self, policy_model: Any, reward_model: RewardModel, samples: list[tuple[str, str]]):
        """
        Perform a single optimization step.
        samples: list of (user_input, agent_output) tuples.
        """
        rewards = [reward_model.predict_reward(inp, out) for inp, out in samples]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        logger.info(f"RLHFOptimizer: Step complete. Average Reward: {avg_reward:.4f}")
        # In a real implementation, this would update the policy_model weights.
        return avg_reward

class FeedbackCollector:
    """
    Implements the full RLHF loop (Chapter 47).
    Includes Data Collection, Reward Modeling, and Optimization.
    """
    def __init__(self, storage_path: str = "feedback_data.jsonl"):
        self.storage_path = storage_path
        self.reward_model = RewardModel()
        self.optimizer = RLHFOptimizer()
        self.pending_feedback = []

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
        self.pending_feedback.append(feedback)

        # Trigger online learning if enough samples
        if len(self.pending_feedback) >= 5:
            self.fine_tune()

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

    def fine_tune(self):
        """
        Execute the RLHF fine-tuning loop (Chapter 47.2).
        """
        if not self.pending_feedback:
            return

        logger.info("RLHF: Starting fine-tuning cycle...")

        # 1. Update Reward Model
        self.reward_model.train(self.pending_feedback)

        # 2. Optimize Policy (Simulated)
        # In a real scenario, we'd sample trajectories from the current policy
        # and use the updated RM to score them.
        samples = [(f.user_input, f.agent_output) for f in self.pending_feedback]
        avg_reward = self.optimizer.step(None, self.reward_model, samples) # Policy model is None for mock

        logger.info(f"RLHF: Cycle complete. Batch Size: {len(self.pending_feedback)}, Avg Reward: {avg_reward:.2f}")
        self.pending_feedback = []
