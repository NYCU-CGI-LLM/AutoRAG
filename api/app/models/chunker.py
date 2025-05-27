from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .file_chunk_result import FileChunkResult
    from .retriever import Retriever


class ChunkerStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Chunker(SQLModel, table=True):
    __tablename__ = "chunker"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=100, unique=True)  # User-defined method name
    module_type: str = Field(..., max_length=50)  # llama_index_chunk, langchain_chunk, pipeline
    chunk_method: str = Field(..., max_length=50)  # Token, Sentence, Character, etc.
    chunk_size: Optional[int] = Field(default=None)  # Chunk size
    chunk_overlap: Optional[int] = Field(default=None)  # Chunk overlap
    
    # Use SQLAlchemy for PostgreSQL JSONB type for flexible parameters
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    status: ChunkerStatus = Field(default=ChunkerStatus.ACTIVE)
    
    # Relationships
    chunk_results: List["FileChunkResult"] = Relationship(back_populates="chunker")
    retrievers: List["Retriever"] = Relationship(back_populates="chunker") 