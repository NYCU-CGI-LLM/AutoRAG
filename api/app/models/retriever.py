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
    from .parser import Parser
    from .chunker import Chunker
    from .indexer import Indexer


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
    name: str = Field(..., max_length=100, unique=True)
    description: Optional[str] = Field(None)
    
    # Index combination - what makes this retriever unique
    library_id: UUID = Field(foreign_key="library.id", ondelete="CASCADE")
    parser_id: UUID = Field(foreign_key="parser.id", ondelete="CASCADE")
    chunker_id: UUID = Field(foreign_key="chunker.id", ondelete="CASCADE")
    indexer_id: UUID = Field(foreign_key="indexer.id", ondelete="CASCADE")
    
    # Retrieval configuration
    top_k: int = Field(default=10)
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Storage and indexing information
    storage_path: str = Field(...)  # Path where the indexed database is stored
    collection_name: Optional[str] = Field(None, max_length=255)  # ChromaDB collection name
    
    # Status tracking
    status: RetrieverStatus = Field(default=RetrieverStatus.PENDING)
    indexed_at: Optional[datetime] = Field(None)  # When indexing completed
    error_message: Optional[str] = Field(None)  # Error if failed
    
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
    parser: "Parser" = Relationship(back_populates="retrievers")
    chunker: "Chunker" = Relationship(back_populates="retrievers")
    indexer: "Indexer" = Relationship(back_populates="retrievers")
    chats: List["Chat"] = Relationship(back_populates="retriever")
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('library_id', 'parser_id', 'chunker_id', 'indexer_id', 
                        name='uniq_library_parser_chunker_indexer'),
        Index('retriever_library_idx', 'library_id'),
        Index('retriever_parser_idx', 'parser_id'),
        Index('retriever_chunker_idx', 'chunker_id'),
        Index('retriever_indexer_idx', 'indexer_id'),
        Index('retriever_status_idx', 'status'),
    )