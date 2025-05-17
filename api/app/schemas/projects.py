from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict, Optional

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str
    created_at: datetime
    status: str
    metadata: Dict[str, Any]

    class Config:
        orm_mode = True 