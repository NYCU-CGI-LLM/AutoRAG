from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel, TaskStatusEnum


class RetrieverConfigBase(BaseModel):
    name: str = Field(..., description="Retriever configuration name", max_length=100)
    description: Optional[str] = Field(None, description="Configuration description", max_length=500)
    library_id: UUID = Field(..., description="Associated library ID")
    config: Dict[str, Any] = Field(..., description="Retriever configuration parameters")


class RetrieverConfigCreate(RetrieverConfigBase):
    pass


class RetrieverConfig(RetrieverConfigBase, IDModel, TimestampModel):
    indexing_status: TaskStatusEnum = Field(default=TaskStatusEnum.PENDING, description="Indexing status")
    indexing_progress: Optional[float] = Field(default=0.0, description="Indexing progress percentage")
    indexing_message: Optional[str] = Field(None, description="Indexing status message")
    document_count: int = Field(default=0, description="Number of indexed documents")
    
    class Config:
        from_attributes = True


class RetrieverConfigDetail(RetrieverConfig):
    library_name: Optional[str] = Field(None, description="Associated library name")
    performance_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Performance metrics")


class IndexingStatusUpdate(BaseModel):
    status: TaskStatusEnum = Field(..., description="Current indexing status")
    progress: Optional[float] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    document_count: Optional[int] = Field(None, description="Number of processed documents")
