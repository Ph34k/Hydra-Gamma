import json
import os
import uuid
from typing import Optional

from pydantic import PrivateAttr

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class ScheduleTool(BaseTool):
    name: str = "schedule_tool"
    description: str = "Schedule tasks for future execution (Cron or Interval)."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["schedule_cron", "schedule_interval", "cancel_task", "list_tasks"],
                "description": "Action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Name of the task.",
            },
            "cron_expression": {
                "type": "string",
                "description": "Cron expression (e.g., '0 0 * * *').",
            },
            "interval_seconds": {
                "type": "integer",
                "description": "Interval in seconds.",
            },
            "prompt": {
                "type": "string",
                "description": "Prompt to execute.",
            },
            "repeat": {
                "type": "boolean",
                "default": True,
                "description": "Whether to repeat the task.",
            },
            "task_id": {
                "type": "string",
                "description": "UUID of the task to cancel.",
            },
        },
        "required": ["action"],
    }

    _schedule_file: str = PrivateAttr(default=os.path.expanduser("~/.manus_schedule.json"))

    async def execute(
        self,
        action: str,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        prompt: Optional[str] = None,
        repeat: bool = True,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "schedule_cron":
                if not name or not cron_expression or not prompt:
                    return ToolResult(error="Name, cron_expression, and prompt required")
                return self._schedule_cron(name, cron_expression, prompt, repeat)
            elif action == "schedule_interval":
                if not name or not interval_seconds or not prompt:
                    return ToolResult(error="Name, interval_seconds, and prompt required")
                return self._schedule_interval(name, interval_seconds, prompt, repeat)
            elif action == "cancel_task":
                if not task_id:
                    return ToolResult(error="Task ID required")
                return self._cancel_task(task_id)
            elif action == "list_tasks":
                return self._list_tasks()
            else:
                return ToolResult(error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"ScheduleTool error: {e}")
            return ToolResult(error=str(e))

    def _load_tasks(self) -> dict:
        if os.path.exists(self._schedule_file):
            try:
                with open(self._schedule_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_tasks(self, tasks: dict):
        with open(self._schedule_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def _schedule_cron(self, name: str, cron: str, prompt: str, repeat: bool) -> ToolResult:
        tasks = self._load_tasks()
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "type": "cron",
            "name": name,
            "cron": cron,
            "prompt": prompt,
            "repeat": repeat,
            "status": "active"
        }
        self._save_tasks(tasks)
        return ToolResult(output=f"Scheduled Cron Task {task_id}")

    def _schedule_interval(self, name: str, interval: int, prompt: str, repeat: bool) -> ToolResult:
        tasks = self._load_tasks()
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "type": "interval",
            "name": name,
            "interval": interval,
            "prompt": prompt,
            "repeat": repeat,
            "status": "active"
        }
        self._save_tasks(tasks)
        return ToolResult(output=f"Scheduled Interval Task {task_id}")

    def _cancel_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        if task_id in tasks:
            del tasks[task_id]
            self._save_tasks(tasks)
            return ToolResult(output=f"Cancelled Task {task_id}")
        return ToolResult(error=f"Task {task_id} not found")

    def _list_tasks(self) -> ToolResult:
        tasks = self._load_tasks()
        return ToolResult(output=json.dumps(tasks, indent=2))
