import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

class AuditLogger:
    """
    Implements structured audit logging for agent actions.
    Chapter 35: Audit Log and Observability
    """

    def __init__(self, log_path: str = "audit.log"):
        self.log_path = Path(log_path)
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not self.log_path.exists():
            self.log_path.touch()

    def log_event(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        result_status: Optional[str] = None,
        duration_ms: Optional[float] = None,
        token_usage: Optional[Dict[str, int]] = None,
        payload: Optional[Any] = None
    ):
        """
        Logs an event to the audit log in JSON format.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "task_id": task_id or str(uuid.uuid4()), # Default if not provided
            "trace_id": trace_id or str(uuid.uuid4()), # Unique trace ID for request/session
            "user_id": user_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "result_status": result_status,
            "duration_ms": duration_ms,
            "token_usage": token_usage,
            "payload": payload
        }

        # Filter out None values to keep log clean (optional, but good for size)
        entry = {k: v for k, v in entry.items() if v is not None}

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Fallback to stderr if file write fails
            print(f"FAILED TO WRITE AUDIT LOG: {e}")

    def log_tool_call(self, task_id, user_id, tool_name, tool_args, trace_id=None):
        self.log_event("tool_call", task_id=task_id, trace_id=trace_id, user_id=user_id, tool_name=tool_name, tool_args=tool_args)

    def log_tool_result(self, task_id, user_id, tool_name, status, duration_ms, result, trace_id=None):
        # Truncate result in payload if too large
        payload = str(result)[:1000] if result else None
        self.log_event("tool_result", task_id=task_id, trace_id=trace_id, user_id=user_id, tool_name=tool_name,
                       result_status=status, duration_ms=duration_ms, payload=payload)
