from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel


class LibraryBase(BaseModel):
    library_name: str = Field(..., description="Library name")
    description: Optional[str] = Field(None, description="Library description")


class LibraryCreate(LibraryBase):
    pass


class Library(LibraryBase, IDModel, TimestampModel):
    class Config:
        from_attributes = True


class LibraryDetail(Library):
    files: List["FileInfo"] = Field(default_factory=list, description="List of files in the library")


class FileInfo(BaseModel):
    id: UUID = Field(..., description="File ID")
    file_name: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    upload_time: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    file_id: UUID = Field(..., description="Uploaded file ID")
    file_name: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    message: str = Field(..., description="Upload status message")


# Forward reference resolution
LibraryDetail.model_rebuild() 