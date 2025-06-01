from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.schemas.common import IDModel, TimestampModel


class ChunkerResponse(BaseModel):
    """Response schema for chunker information"""
    id: UUID = Field(..., description="Chunker ID")
    name: str = Field(..., description="Chunker name")
    module_type: str = Field(..., description="Chunker module type")
    chunk_method: str = Field(..., description="Chunking method")
    chunk_size: Optional[int] = Field(None, description="Chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap")
    params: Dict[str, Any] = Field(..., description="Chunker parameters")
    status: str = Field(..., description="Chunker status")
    
    class Config:
        from_attributes = True


class ChunkerListResponse(BaseModel):
    """Response schema for listing chunkers"""
    total: int = Field(..., description="Total number of chunkers")
    chunkers: List[ChunkerResponse] = Field(..., description="List of chunkers")


class ChunkerUsageStats(BaseModel):
    """Schema for chunker usage statistics"""
    total_chunks_created: int = Field(default=0, description="Total chunks created")
    successful_chunks: int = Field(default=0, description="Successful chunks")
    failed_chunks: int = Field(default=0, description="Failed chunks")
    success_rate: float = Field(default=0.0, description="Success rate percentage")
    average_chunk_size: Optional[float] = Field(None, description="Average chunk size in characters")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    total_files_processed: int = Field(default=0, description="Total files processed")


class ChunkerDetailResponse(ChunkerResponse):
    """Detailed response schema for chunker with additional information"""
    usage_stats: Optional[ChunkerUsageStats] = Field(None, description="Usage statistics")
    description: Optional[str] = Field(None, description="Chunker description")
    
    class Config:
        from_attributes = True 