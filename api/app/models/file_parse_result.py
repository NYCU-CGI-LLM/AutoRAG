from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .file import File
    from .parser import Parser
    from .file_chunk_result import FileChunkResult


class ParseStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success" 
    FAILED = "failed"


class FileParseResult(SQLModel, table=True):
    __tablename__ = "file_parse_result"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Foreign keys with cascade delete
    file_id: UUID = Field(foreign_key="file.id", ondelete="CASCADE")
    parser_id: UUID = Field(foreign_key="parser.id", ondelete="CASCADE")
    
    # MinIO storage fields
    bucket: str = Field(default="rag-parsed-files", max_length=63)
    object_key: str = Field(...)  # e.g. parsed/<<file_id>>/pdf_pymupdf_v1.parquet
    
    # Execution status
    status: ParseStatus = Field(default=ParseStatus.PENDING)
    parsed_at: Optional[datetime] = Field(None)  # Filled when success
    error_message: Optional[str] = Field(None)   # Reason when failed
    
    # Additional metadata in JSON format (needs SQLAlchemy JSONB for dict type)
    extra_meta: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Relationships
    file: "File" = Relationship(back_populates="parse_results")
    parser: "Parser" = Relationship(back_populates="parse_results")
    chunk_results: List["FileChunkResult"] = Relationship(back_populates="file_parse_result")
    
    # Table constraints for data integrity and performance
    __table_args__ = (
        UniqueConstraint('file_id', 'parser_id', name='uniq_file_parser'),
        Index('fpr_file_idx', 'file_id'),
        Index('fpr_parser_idx', 'parser_id'), 
        Index('fpr_status_idx', 'status'),
    ) 