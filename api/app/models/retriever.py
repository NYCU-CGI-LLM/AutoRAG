from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text, Index, UniqueConstraint
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .chat import Chat
    from .library import Library
    from .config import Config


class RetrieverStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    ACTIVE = "active"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class Retriever(SQLModel, table=True):
    __tablename__ = "retriever"
    
    # Primary key
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None)
    
    # Core relationships - library and configuration
    library_id: UUID = Field(foreign_key="library.id", ondelete="CASCADE")
    config_id: UUID = Field(foreign_key="config.id", ondelete="CASCADE")
    
    # Retrieval configuration
    top_k: int = Field(default=10)
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Storage and indexing information
    storage_path: str = Field(...)  # Path where the indexed database is stored
    collection_name: Optional[str] = Field(None, max_length=255)  # Vector database collection name
    
    # Status tracking
    status: RetrieverStatus = Field(default=RetrieverStatus.PENDING)
    indexed_at: Optional[datetime] = Field(None)  # When indexing completed
    error_message: Optional[str] = Field(None)  # Error message if failed
    
    # Statistics
    total_chunks: Optional[int] = Field(None)  # Number of chunks indexed
    index_size_bytes: Optional[int] = Field(None)  # Size of the index
    
    # Additional metadata
    extra_meta: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Relationships
    library: "Library" = Relationship(back_populates="retrievers")
    config: "Config" = Relationship(back_populates="retrievers")
    chats: List["Chat"] = Relationship(back_populates="retriever")
    
    # Table constraints - unique combination of library and config
    __table_args__ = (
        UniqueConstraint('library_id', 'config_id', name='uniq_library_config'),
        Index('retriever_library_idx', 'library_id'),
        Index('retriever_config_idx', 'config_id'),
        Index('retriever_status_idx', 'status'),
    )