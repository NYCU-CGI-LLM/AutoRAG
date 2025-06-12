from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.schemas.common import IDModel, TimestampModel, TaskStatusEnum


class RetrieverConfigBase(BaseModel):
    """Legacy RetrieverConfigBase - kept for backward compatibility"""
    name: str = Field(..., description="Retriever configuration name", max_length=100)
    description: Optional[str] = Field(None, description="Configuration description", max_length=500)
    library_id: UUID = Field(..., description="Associated library ID")
    config: Dict[str, Any] = Field(..., description="Retriever configuration parameters")


class RetrieverConfigCreate(RetrieverConfigBase):
    """Legacy RetrieverConfigCreate - kept for backward compatibility"""
    pass


class RetrieverConfig(RetrieverConfigBase, IDModel, TimestampModel):
    """Legacy RetrieverConfig - kept for backward compatibility"""
    indexing_status: TaskStatusEnum = Field(default=TaskStatusEnum.PENDING, description="Indexing status")
    indexing_progress: Optional[float] = Field(default=0.0, description="Indexing progress percentage")
    indexing_message: Optional[str] = Field(None, description="Indexing status message")
    document_count: int = Field(default=0, description="Number of indexed documents")
    
    class Config:
        from_attributes = True


class RetrieverConfigDetail(RetrieverConfig):
    """Legacy RetrieverConfigDetail - kept for backward compatibility"""
    library_name: Optional[str] = Field(None, description="Associated library name")
    performance_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Performance metrics")


class IndexingStatusUpdate(BaseModel):
    status: TaskStatusEnum = Field(..., description="Current indexing status")
    progress: Optional[float] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    document_count: Optional[int] = Field(None, description="Number of processed documents")


# New retriever service schemas
class RetrieverCreateRequest(BaseModel):
    """Request schema for creating a retriever using config-based approach"""
    name: str = Field(..., description="Retriever name", max_length=100)
    description: Optional[str] = Field(None, description="Retriever description", max_length=500)
    library_id: UUID = Field(..., description="Library ID to process")
    config_id: UUID = Field(..., description="Configuration ID")
    
    top_k: int = Field(default=10, description="Default number of results to return")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")
    collection_name: Optional[str] = Field(None, description="Custom collection name")


class RetrieverBuildRequest(BaseModel):
    """Request schema for building a retriever"""
    force_rebuild: bool = Field(default=False, description="Force rebuild even if already active")


class RetrieverQueryRequest(BaseModel):
    """Request schema for querying a retriever"""
    query: str = Field(..., description="Search query")
    top_k: Optional[int] = Field(None, description="Number of results to return (uses retriever default if not specified)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")


class RetrieverResponse(BaseModel):
    """Response schema for retriever information"""
    id: UUID = Field(..., description="Retriever ID")
    name: str = Field(..., description="Retriever name")
    description: Optional[str] = Field(None, description="Retriever description")
    status: str = Field(..., description="Retriever status")
    library_id: UUID = Field(..., description="Associated library ID")
    config_id: UUID = Field(..., description="Configuration ID")
    
    collection_name: Optional[str] = Field(None, description="Vector database collection name")
    top_k: int = Field(..., description="Default top-k value")
    total_chunks: Optional[int] = Field(None, description="Number of indexed chunks")
    indexed_at: Optional[datetime] = Field(None, description="Index creation timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        from_attributes = True


class RetrieverBuildResponse(BaseModel):
    """Response schema for retriever build operation"""
    retriever_id: str = Field(..., description="Retriever ID")
    status: str = Field(..., description="Build status")
    parse_results: int = Field(..., description="Number of parse results")
    chunk_results: int = Field(..., description="Number of chunk results")
    successful_chunks: int = Field(..., description="Number of successful chunks")
    collection_name: Optional[str] = Field(None, description="Created collection name")
    total_chunks: Optional[int] = Field(None, description="Total indexed chunks")
    index_result: Dict[str, Any] = Field(..., description="Indexing operation details")


class RetrieverQueryResponse(BaseModel):
    """Response schema for retriever query results"""
    query: str = Field(..., description="Original query")
    retriever_id: str = Field(..., description="Retriever ID")
    retriever_name: str = Field(..., description="Retriever name")
    total_results: int = Field(..., description="Number of results returned")
    results: List[Dict[str, Any]] = Field(..., description="Search results")


class RetrieverStatsResponse(BaseModel):
    """Response schema for retriever statistics"""
    retriever_id: str = Field(..., description="Retriever ID")
    name: str = Field(..., description="Retriever name")
    status: str = Field(..., description="Current status")
    collection_name: Optional[str] = Field(None, description="Collection name")
    indexed_at: Optional[str] = Field(None, description="Index creation timestamp")
    total_chunks: Optional[int] = Field(None, description="Total indexed chunks")
    error_message: Optional[str] = Field(None, description="Error message if any")
    configuration: Dict[str, Any] = Field(..., description="Component configurations")
    pipeline_stats: Dict[str, Any] = Field(..., description="Pipeline statistics")
    extra_meta: Dict[str, Any] = Field(..., description="Additional metadata")


class RetrieverListResponse(BaseModel):
    """Response schema for listing retrievers"""
    total: int = Field(..., description="Total number of retrievers")
    retrievers: List[RetrieverResponse] = Field(..., description="List of retrievers")


class RetrieverStatusUpdate(BaseModel):
    """Request schema for updating retriever status"""
    status: str = Field(..., description="New status")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ComponentInfo(BaseModel):
    """Schema for component information in retriever details"""
    id: str = Field(..., description="Component ID")
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type")
    params: Optional[Dict[str, Any]] = Field(None, description="Component parameters")


class RetrieverDetailResponse(RetrieverResponse):
    """Detailed response schema for retriever with component information"""
    library_name: Optional[str] = Field(None, description="Library name")
    
    # 新增：config 信息
    config_info: Optional[Dict[str, Any]] = Field(None, description="Configuration details")
    
    # 保持原有組件信息
    parser_info: Optional[ComponentInfo] = Field(None, description="Parser details")
    chunker_info: Optional[ComponentInfo] = Field(None, description="Chunker details")
    indexer_info: Optional[ComponentInfo] = Field(None, description="Indexer details")
    pipeline_stats: Optional[Dict[str, Any]] = Field(None, description="Pipeline statistics")
