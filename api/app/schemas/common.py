from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
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

# Standard Error Response Schemas
class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

class ValidationErrorResponse(BaseModel):
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(..., description="Validation error message")
    details: List[ErrorDetail] = Field(..., description="Field-specific validation errors")

class NotFoundErrorResponse(BaseModel):
    error: str = Field(default="not_found", description="Error type")
    message: str = Field(..., description="Resource not found message")
    resource_type: str = Field(..., description="Type of resource that was not found")
    resource_id: Optional[str] = Field(None, description="ID of the resource that was not found")

class ConflictErrorResponse(BaseModel):
    error: str = Field(default="conflict", description="Error type")
    message: str = Field(..., description="Conflict error message")
    conflicting_field: Optional[str] = Field(None, description="Field that caused the conflict")

class ServerErrorResponse(BaseModel):
    error: str = Field(default="internal_server_error", description="Error type")
    message: str = Field(default="An internal server error occurred", description="Server error message")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")