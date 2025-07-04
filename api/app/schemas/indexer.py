from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.schemas.common import IDModel, TimestampModel


class IndexerResponse(BaseModel):
    """Response schema for indexer information"""
    id: UUID = Field(..., description="Indexer ID")
    name: str = Field(..., description="Indexer name")
    index_type: str = Field(..., description="Index type (vector, bm25, hybrid, etc.)")
    model: str = Field(..., description="Model name (embedding model for vector, tokenizer for bm25)")
    params: Dict[str, Any] = Field(..., description="Indexer parameters")
    status: str = Field(..., description="Indexer status")
    
    class Config:
        from_attributes = True


class IndexerListResponse(BaseModel):
    """Response schema for listing indexers"""
    total: int = Field(..., description="Total number of indexers")
    indexers: List[IndexerResponse] = Field(..., description="List of indexers")


class IndexerUsageStats(BaseModel):
    """Schema for indexer usage statistics"""
    total_documents_indexed: int = Field(default=0, description="Total documents indexed")
    active_collections: int = Field(default=0, description="Number of active collections")
    total_collections_created: int = Field(default=0, description="Total collections created")
    average_collection_size: Optional[float] = Field(None, description="Average collection size")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    index_performance_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Performance metrics")


class IndexerDetailResponse(IndexerResponse):
    """Detailed response schema for indexer with additional information"""
    usage_stats: Optional[IndexerUsageStats] = Field(None, description="Usage statistics")
    description: Optional[str] = Field(None, description="Indexer description")
    
    class Config:
        from_attributes = True 