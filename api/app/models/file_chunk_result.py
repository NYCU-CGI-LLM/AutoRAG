from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Dict, Any, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .file import File
    from .file_parse_result import FileParseResult
    from .chunker import Chunker


class ChunkStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success" 
    FAILED = "failed"


class FileChunkResult(SQLModel, table=True):
    __tablename__ = "file_chunk_result"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign keys with cascade delete
    file_id: UUID = Field(foreign_key="file.id", ondelete="CASCADE")
    file_parse_result_id: int = Field(foreign_key="file_parse_result.id", ondelete="CASCADE")
    chunker_id: int = Field(foreign_key="chunker.id", ondelete="CASCADE")
    
    # MinIO storage fields
    bucket: str = Field(default="rag-chunked-files", max_length=63)
    object_key: str = Field(...)  # e.g. chunked/<<file_id>>/<<parse_result_id>>/token_1024.parquet
    
    # Execution status
    status: ChunkStatus = Field(default=ChunkStatus.PENDING)
    chunked_at: Optional[datetime] = Field(None)  # Filled when success
    error_message: Optional[str] = Field(None)   # Reason when failed
    
    # Additional metadata in JSON format (needs SQLAlchemy JSONB for dict type)
    extra_meta: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Relationships
    file: "File" = Relationship(back_populates="chunk_results")
    file_parse_result: "FileParseResult" = Relationship(back_populates="chunk_results")
    chunker: "Chunker" = Relationship(back_populates="chunk_results")
    
    # Table constraints for data integrity and performance
    __table_args__ = (
        UniqueConstraint('file_parse_result_id', 'chunker_id', name='uniq_parse_result_chunker'),
        Index('fcr_file_idx', 'file_id'),
        Index('fcr_parse_result_idx', 'file_parse_result_id'), 
        Index('fcr_chunker_idx', 'chunker_id'),
        Index('fcr_status_idx', 'status'),
    ) 