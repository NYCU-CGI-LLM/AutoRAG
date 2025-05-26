from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel


class LibraryBase(BaseModel):
    library_name: str = Field(..., description="Library name", max_length=100)
    description: Optional[str] = Field(None, description="Library description", max_length=500)


class LibraryCreate(LibraryBase):
    pass


class LibraryStats(BaseModel):
    file_count: int = Field(0, description="Total number of files")
    total_size: int = Field(0, description="Total size in bytes")


class Library(LibraryBase, IDModel, TimestampModel):
    stats: LibraryStats = Field(default_factory=LibraryStats, description="Library statistics")
    
    class Config:
        from_attributes = True


class FileInfo(BaseModel):
    id: UUID = Field(..., description="File ID")
    file_name: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        from_attributes = True


class LibraryDetail(Library):
    files: List[FileInfo] = Field(default_factory=list, description="List of files in the library")


class FileUploadResponse(BaseModel):
    file_id: UUID = Field(..., description="Uploaded file ID")
    file_name: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    message: str = Field(..., description="Upload status message")


class LibraryUpdateRequest(BaseModel):
    library_name: Optional[str] = Field(None, description="Updated library name", max_length=100)
    description: Optional[str] = Field(None, description="Updated library description", max_length=500)


# Forward reference resolution
LibraryDetail.model_rebuild() 
