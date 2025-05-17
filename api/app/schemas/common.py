from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

class OrmBase(BaseModel):
    class Config:
        from_attributes = True

class IDModel(OrmBase):
    id: UUID = Field(default_factory=uuid4)

class TimestampModel(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"

class TaskStatus(OrmBase):
    task_id: str
    status: TaskStatusEnum
    progress: Optional[float] = 0.0
    message: Optional[str] = None
    result: Optional[Any] = None 