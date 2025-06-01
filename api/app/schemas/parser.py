from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.schemas.common import IDModel, TimestampModel


class ParserResponse(BaseModel):
    """Response schema for parser information"""
    id: UUID = Field(..., description="Parser ID")
    name: str = Field(..., description="Parser name")
    module_type: str = Field(..., description="Parser module type")
    supported_mime: List[str] = Field(..., description="Supported MIME types")
    params: Dict[str, Any] = Field(..., description="Parser parameters")
    status: str = Field(..., description="Parser status")
    
    class Config:
        from_attributes = True


class ParserListResponse(BaseModel):
    """Response schema for listing parsers"""
    total: int = Field(..., description="Total number of parsers")
    parsers: List[ParserResponse] = Field(..., description="List of parsers")


class ParserUsageStats(BaseModel):
    """Schema for parser usage statistics"""
    total_files_parsed: int = Field(default=0, description="Total files parsed")
    successful_parses: int = Field(default=0, description="Successful parses")
    failed_parses: int = Field(default=0, description="Failed parses")
    success_rate: float = Field(default=0.0, description="Success rate percentage")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    most_common_mime_types: List[str] = Field(default_factory=list, description="Most commonly parsed MIME types")


class ParserDetailResponse(ParserResponse):
    """Detailed response schema for parser with additional information"""
    usage_stats: Optional[ParserUsageStats] = Field(None, description="Usage statistics")
    description: Optional[str] = Field(None, description="Parser description")
    
    class Config:
        from_attributes = True 