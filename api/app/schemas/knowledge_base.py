from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from .common import IDModel, TimestampModel, OrmBase
from .variation import VariationSummary

class KnowledgeBaseBase(OrmBase):
    name: str
    description: Optional[str] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase, IDModel, TimestampModel):
    pass

class KnowledgeBaseDetail(KnowledgeBase):
    raw_file_count: int = 0
    variation_summaries: List[VariationSummary]
    pass

class FileInfo(OrmBase):
    name: str
    size: Optional[int] = None
    type: Optional[str] = None # e.g., 'file', 'directory' or MIME type
    uploaded_at: datetime = Field(default_factory=datetime.utcnow) 