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

class SupportLanguageEnum(str, Enum):
    ENGLISH = "en"
    CHINESE = "zh"
    KOREAN = "ko"
    JAPANESE = "ja"

class EnvVariableRequest(BaseModel):
    key: str
    value: str

class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    TERMINATED = "terminated"

class TaskType(str, Enum):
    PARSE = "parse"
    CHUNK = "chunk"
    QA = "qa"
    VALIDATE = "validate"
    EVALUATE = "evaluate"
    REPORT = "report"
    CHAT = "chat"

class TaskStatus(OrmBase):
    task_id: str
    status: TaskStatusEnum
    progress: Optional[float] = 0.0
    message: Optional[str] = None
    result: Optional[Any] = None

class VersionResponse(BaseModel):
    version: str