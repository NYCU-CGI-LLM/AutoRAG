from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .library import Library
    from .file_parse_result import FileParseResult
    from .file_chunk_result import FileChunkResult


class FileStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"
    ARCHIVED = "archived"


class File(SQLModel, table=True):
    __tablename__ = "file"
    
    # Primary key and foreign key
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="library.id", ondelete="CASCADE", index=True)
    
    # MinIO related fields
    bucket: str = Field(default="rag-files", max_length=63)
    object_key: str = Field(...)  # e.g. original/uuid/xxx.pdf
    
    # Basic properties
    file_name: str = Field(..., max_length=255)  # User uploaded filename
    mime_type: str = Field(..., max_length=64)   # application/pdf, image/jpeg, etc.
    size_bytes: Optional[int] = Field(None)      # File size for billing or display
    checksum_md5: Optional[str] = Field(None, max_length=32)  # Upload verification checksum
    
    # Status and time fields
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    uploader_id: Optional[UUID] = Field(None)    # For multi-user shared library
    status: FileStatus = Field(default=FileStatus.ACTIVE)  # active / deleted / archived
    
    # Relationships
    library: "Library" = Relationship(back_populates="files")
    parse_results: List["FileParseResult"] = Relationship(back_populates="file")
    chunk_results: List["FileChunkResult"] = Relationship(back_populates="file") 