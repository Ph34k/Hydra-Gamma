import asyncio
import json
import os
import time
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, List

from app.logger import logger
from app.tool.schedule_tool import ScheduleTool
from app.agent.manus import Manus
# We need a way to run the agent. Manus.run() is the entry point.

class SchedulerService:
    """
    A simple scheduler service that checks for due tasks and executes them using the Manus agent.
    Ref: Chapter 30 of the Technical Bible.
    """

    def __init__(self, schedule_file: str = os.path.expanduser("~/.manus_schedule.json")):
        self.schedule_file = schedule_file
        self.running = False
        self._tool = ScheduleTool() # To reuse loading logic

    async def start(self):
        """Start the scheduler loop."""
        self.running = True
        logger.info("Scheduler Service started.")
        while self.running:
            try:
                await self.check_and_run_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(10) # Check every 10 seconds

    def stop(self):
        self.running = False

    async def check_and_run_tasks(self):
        tasks = self._tool._load_tasks()
        now = datetime.now()

        updated = False
        for task_id, task in list(tasks.items()):
            if task.get("status") != "active":
                continue

            should_run = False
            if task["type"] == "interval":
                last_run = task.get("last_run", 0)
                interval = task["interval"]
                if time.time() - last_run >= interval:
                    should_run = True

            elif task["type"] == "cron":
                # Basic cron check (simplified for now, ideally use a library like croniter)
                # For this implementation, we will assume a simple check or use a library if available.
                # Since we don't have croniter in requirements, we will implement a placeholder or simple interval fallback.
                # In a real scenario, we would add croniter to requirements.
                # Let's try to import croniter, if not, skip cron tasks with a warning.
                try:
                    from croniter import croniter
                    cron = croniter(task["cron"], datetime.fromtimestamp(task.get("last_run", 0) or time.time()))
                    # Check if next run time has passed
                    # This logic is tricky without state.
                    # Correct way: get next scheduled time from last_run. If it's in the past relative to now, run.

                    last_run_dt = datetime.fromtimestamp(task.get("last_run", 0)) if task.get("last_run") else datetime.min
                    iter = croniter(task["cron"], last_run_dt)
                    next_run = iter.get_next(datetime)

                    if next_run <= now:
                        should_run = True
                except ImportError:
                    logger.warning("croniter not installed. Cron tasks will not run.")
                except Exception as e:
                    logger.error(f"Error checking cron task {task_id}: {e}")

            if should_run:
                logger.info(f"Executing scheduled task: {task['name']}")

                # Execute Task
                # We spawn a new agent instance
                try:
                    agent = await Manus.create()
                    # Inject Playbook if available (Chapter 30.4) - Not implemented yet

                    # Run the agent
                    # We need to wrap this in a way that doesn't block the scheduler forever,
                    # but for now we await it. Ideally, run in background task.
                    asyncio.create_task(self._run_agent_task(agent, task["prompt"]))

                    # Update task state
                    task["last_run"] = time.time()
                    if not task.get("repeat", True):
                        task["status"] = "completed"
                    updated = True
                except Exception as e:
                    logger.error(f"Failed to execute task {task['name']}: {e}")

        if updated:
            self._tool._save_tasks(tasks)

    async def _run_agent_task(self, agent: Manus, prompt: str):
        try:
             await agent.run(prompt)
        except Exception as e:
             logger.error(f"Agent execution failed for scheduled task: {e}")

if __name__ == "__main__":
    # Standalone runner
    scheduler = SchedulerService()
    try:
        asyncio.run(scheduler.start())
    except KeyboardInterrupt:
        pass
