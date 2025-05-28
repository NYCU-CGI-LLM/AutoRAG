from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class EmbeddingStats(SQLModel, table=True):
    """
    Track embedding statistics and collection metadata
    Links PostgreSQL metadata with ChromaDB collections
    """
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="library.id", index=True)
    indexer_id: Optional[UUID] = Field(default=None, foreign_key="indexer.id")
    
    # ChromaDB collection information
    collection_name: str = Field(max_length=255, index=True)
    embedding_model: str = Field(max_length=255)
    
    # Statistics
    total_documents: int = Field(default=0)
    vector_dimension: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = Field(default=None)
    
    # Usage statistics
    access_count: int = Field(default=0)
    
    # Status
    status: str = Field(default="active", max_length=50)  # active, inactive, error
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class EmbeddingStatsCreate(SQLModel):
    """Schema for creating embedding stats"""
    library_id: UUID
    indexer_id: Optional[UUID] = None
    collection_name: str
    embedding_model: str
    total_documents: int = 0
    vector_dimension: int = 0


class EmbeddingStatsUpdate(SQLModel):
    """Schema for updating embedding stats"""
    total_documents: Optional[int] = None
    vector_dimension: Optional[int] = None
    last_accessed: Optional[datetime] = None
    access_count: Optional[int] = None
    status: Optional[str] = None


class EmbeddingStatsResponse(SQLModel):
    """Schema for embedding stats response"""
    id: UUID
    library_id: UUID
    indexer_id: Optional[UUID]
    collection_name: str
    embedding_model: str
    total_documents: int
    vector_dimension: int
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    access_count: int
    status: str 