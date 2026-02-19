import time
from collections import defaultdict
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.logger import logger

class PerformanceMonitor:
    """
    Tracks and reports Key Performance Indicators (KPIs) for the agent.
    Chapter 12: Measuring Efficiency of Autonomy.
    """

    def __init__(self):
        self.start_time = time.time()
        self.metrics: Dict[str, Any] = defaultdict(int)
        self.tool_calls: List[Dict[str, Any]] = []
        self.step_durations: List[float] = []
        self.token_usage: Dict[str, int] = defaultdict(int)

    def record_tool_call(self, tool_name: str, success: bool, duration: float, error: Optional[str] = None):
        """Record a tool execution."""
        self.tool_calls.append({
            "tool": tool_name,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
            "error": error
        })
        self.metrics["total_tool_calls"] += 1
        if not success:
            self.metrics["failed_tool_calls"] += 1

    def record_step_duration(self, duration: float):
        """Record the duration of a think-act loop iteration."""
        self.step_durations.append(duration)
        self.metrics["total_steps"] += 1

    def record_token_usage(self, prompt_tokens: int, completion_tokens: int):
        """Record token usage."""
        self.token_usage["prompt_tokens"] += prompt_tokens
        self.token_usage["completion_tokens"] += completion_tokens
        self.metrics["total_tokens"] = self.token_usage["prompt_tokens"] + self.token_usage["completion_tokens"]

    def get_summary(self) -> Dict[str, Any]:
        """Generate a performance summary report."""
        total_calls = self.metrics["total_tool_calls"]
        failed_calls = self.metrics["failed_tool_calls"]
        tool_failure_rate = (failed_calls / total_calls) if total_calls > 0 else 0.0

        avg_step_duration = (sum(self.step_durations) / len(self.step_durations)) if self.step_durations else 0.0

        # Token Efficiency: Ratio of useful tokens (completion) vs total (prompt + completion)
        # This is a rough proxy as prompt includes context which is overhead.
        total_tokens = self.metrics.get("total_tokens", 0)
        token_efficiency = (self.token_usage["completion_tokens"] / total_tokens) if total_tokens > 0 else 0.0

        return {
            "uptime": time.time() - self.start_time,
            "total_steps": self.metrics["total_steps"],
            "avg_step_duration_sec": round(avg_step_duration, 2),
            "tool_failure_rate": round(tool_failure_rate, 2),
            "token_efficiency": round(token_efficiency, 2),
            "total_tokens": total_tokens
        }

    def log_metrics(self):
        """Log the current metrics."""
        summary = self.get_summary()
        logger.info(f"Performance Metrics: {summary}")
