import asyncio
import uuid
import time
from typing import Dict, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from app.api.models import TaskRequest, TaskResponse, TaskEvent, TaskType
from app.agent.orchestrator import Orchestrator

app = FastAPI()

# Global Orchestrator (singleton for this example)
orchestrator = Orchestrator()
# Simple task store
tasks: Dict[str, str] = {} # id -> status
event_queues: Dict[str, asyncio.Queue] = {}

@app.post("/v1/tasks", response_model=TaskResponse)
async def create_task(req: TaskRequest):
    """Starts a new autonomous task."""
    task_id = uuid.uuid4()
    tasks[str(task_id)] = "pending"
    event_queues[str(task_id)] = asyncio.Queue()

    # In a real system, we'd start a background task here
    # asyncio.create_task(run_agent(task_id, req.goal))

    # For now, just simulate
    tasks[str(task_id)] = "running"

    return TaskResponse(id=task_id, status="running")

@app.get("/v1/tasks/{task_id}/stream")
async def stream_task_events(task_id: str):
    """Streams events for a task using SSE."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator() -> AsyncGenerator[dict, None]:
        queue = event_queues.get(task_id)
        if not queue:
            return

        while True:
            # Check if task is finished
            if tasks.get(task_id) in ["completed", "failed"] and queue.empty():
                break

            try:
                # Wait for new event
                # Use timeout to send keep-alive
                event: TaskEvent = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield {
                    "event": event.type,
                    "data": event.model_dump_json()
                }
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": ""}
            except asyncio.CancelledError:
                break

    return EventSourceResponse(event_generator())

# Utility to simulate pushing events (for testing)
async def push_event(task_id: str, event_type: TaskType, content: str):
    if task_id in event_queues:
        event = TaskEvent(
            task_id=uuid.UUID(task_id),
            type=event_type,
            content=content,
            timestamp=time.time()
        )
        await event_queues[task_id].put(event)
