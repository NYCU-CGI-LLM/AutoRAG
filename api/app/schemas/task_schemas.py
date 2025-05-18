from pydantic import BaseModel
from typing import Any, Optional

class ReverseRequest(BaseModel):
    text: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None 