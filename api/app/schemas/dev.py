"""
Development API schemas for parser and chunker testing functionality
"""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class ParseRequest(BaseModel):
    """Request schema for parsing a file with a specific parser"""
    file_id: UUID
    parser_id: UUID


class ParseResponse(BaseModel):
    """Response schema for parse operation results"""
    success: bool
    message: str
    result_id: Optional[UUID] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    extra_meta: Optional[dict] = None


class FileInfo(BaseModel):
    """Schema for file information in dev API responses"""
    id: Optional[UUID] = None
    file_name: str
    mime_type: str
    size_bytes: Optional[int] = None
    bucket: str
    object_key: str
    status: str


class ParserInfo(BaseModel):
    """Schema for parser information in dev API responses"""
    id: Optional[UUID] = None
    name: str
    module_type: str
    supported_mime: List[str]
    params: dict
    status: str


class ParseResultInfo(BaseModel):
    """Schema for parse result information"""
    id: UUID
    file_id: UUID
    file_name: str
    parser_id: UUID
    parser_name: str
    status: str
    bucket: str
    object_key: str
    parsed_at: Optional[str] = None
    error_message: Optional[str] = None
    extra_meta: Optional[dict] = None


class ParsedDataResponse(BaseModel):
    """Response schema for parsed data preview"""
    success: bool
    message: str
    total_rows: Optional[int] = None
    columns: Optional[List[str]] = None
    preview_data: Optional[List[dict]] = None


class DeleteResponse(BaseModel):
    """Response schema for delete operations"""
    success: bool
    message: str
    deleted_count: Optional[int] = None


class HealthResponse(BaseModel):
    """Response schema for health check"""
    status: str
    message: str
    timestamp: str


# Chunker related schemas
class ChunkRequest(BaseModel):
    """Request schema for chunking parsed results with a specific chunker"""
    parse_result_ids: List[UUID]
    chunker_id: UUID


class ChunkResponse(BaseModel):
    """Response schema for chunk operation results"""
    success: bool
    message: str
    results: List[dict]
    total_processed: int
    successful_count: int
    failed_count: int


class ChunkerInfo(BaseModel):
    """Schema for chunker information in dev API responses"""
    id: Optional[UUID] = None
    name: str
    module_type: str
    chunk_method: str
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    params: dict
    status: str


class ChunkResultInfo(BaseModel):
    """Schema for chunk result information"""
    id: UUID
    file_id: UUID
    file_name: str
    file_parse_result_id: UUID
    chunker_id: UUID
    chunker_name: str
    status: str
    bucket: str
    object_key: str
    chunked_at: Optional[str] = None
    error_message: Optional[str] = None
    extra_meta: Optional[dict] = None


class ChunkedDataResponse(BaseModel):
    """Response schema for chunked data preview"""
    success: bool
    message: str
    chunk_result_id: UUID
    total_chunks: Optional[int] = None
    columns: Optional[List[str]] = None
    preview_data: Optional[List[dict]] = None 