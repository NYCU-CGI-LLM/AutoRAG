from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .retriever import Retriever


class IndexerStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Indexer(SQLModel, table=True):
    __tablename__ = "indexer"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=100, unique=True)  # User-defined indexer name
    index_type: str = Field(..., max_length=50)  # vector, bm25, hybrid, etc.
    model: str = Field(..., max_length=200)  # For vector: embedding model name, for bm25: tokenizer name
    
    # Use SQLAlchemy for PostgreSQL JSONB type for flexible parameters
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    status: IndexerStatus = Field(default=IndexerStatus.ACTIVE)
    
    # Relationships
    retrievers: List["Retriever"] = Relationship(back_populates="indexer") 