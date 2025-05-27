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
    mime_type: str = Field(..., description="MIME type of the file")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    bucket: str = Field(..., description="MinIO bucket name")
    object_key: str = Field(..., description="MinIO object key/path")
    status: str = Field(..., description="File status (active/deleted/archived)")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    uploader_id: Optional[UUID] = Field(None, description="ID of user who uploaded the file")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum for integrity verification")
    
    class Config:
        from_attributes = True


class LibraryDetail(Library):
    files: List[FileInfo] = Field(default_factory=list, description="List of files in the library")


class FileUploadResponse(BaseModel):
    file_id: UUID = Field(..., description="Uploaded file ID")
    file_name: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    bucket: str = Field(..., description="MinIO bucket name")
    object_key: str = Field(..., description="MinIO object key/path")
    status: str = Field(..., description="File status")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    message: str = Field(..., description="Upload status message")


class FileDownloadResponse(BaseModel):
    download_url: str = Field(..., description="Presigned download URL")
    file_name: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    expires_in: str = Field(..., description="URL expiration time")


class LibraryUpdateRequest(BaseModel):
    library_name: Optional[str] = Field(None, description="Updated library name", max_length=100)
    description: Optional[str] = Field(None, description="Updated library description", max_length=500)


# Forward reference resolution
LibraryDetail.model_rebuild() 
