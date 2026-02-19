from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

class TaskType(str, Enum):
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    RESULT = "result"

class TaskRequest(BaseModel):
    goal: str
    sandbox_config: Dict[str, Any] = Field(default_factory=lambda: {"memory": "1Gi", "timeout": 3600})

class TaskResponse(BaseModel):
    id: UUID
    status: str

class TaskEvent(BaseModel):
    task_id: UUID
    type: TaskType
    content: str
    timestamp: float
    metadata: Dict[str, Any] = {}
