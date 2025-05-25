from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel, TaskStatusEnum


class RetrieverConfigBase(BaseModel):
    name: str = Field(..., description="Retriever configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
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


class RetrieverQueryRequest(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=10, description="Number of top results to return")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")


class RetrieverQueryResponse(BaseModel):
    query: str = Field(..., description="Original query")
    results: List[Dict[str, Any]] = Field(..., description="Retrieved documents")
    total_count: int = Field(..., description="Total number of results")
    processing_time: float = Field(..., description="Query processing time in seconds") 