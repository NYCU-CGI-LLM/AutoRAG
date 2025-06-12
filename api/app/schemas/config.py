from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.schemas.common import IDModel, TimestampModel


class ConfigBase(BaseModel):
    """Base Configuration Schema"""
    parser_id: UUID = Field(..., description="Parser ID")
    chunker_id: UUID = Field(..., description="Chunker ID") 
    indexer_id: UUID = Field(..., description="Indexer ID")
    name: Optional[str] = Field(None, description="Configuration name", max_length=100)
    description: Optional[str] = Field(None, description="Configuration description", max_length=500)
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional configuration parameters")


class ConfigCreate(ConfigBase):
    """Configuration creation request schema"""
    pass


class ConfigUpdate(BaseModel):
    """Configuration update request schema"""
    name: Optional[str] = Field(None, description="Configuration name", max_length=100)
    description: Optional[str] = Field(None, description="Configuration description", max_length=500)
    params: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")
    status: Optional[str] = Field(None, description="Configuration status")


class ConfigResponse(ConfigBase, IDModel, TimestampModel):
    """Configuration response schema"""
    status: str = Field(..., description="Configuration status")
    
    class Config:
        from_attributes = True


class ComponentInfo(BaseModel):
    """Component information schema"""
    id: str = Field(..., description="Component ID")
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type")
    params: Optional[Dict[str, Any]] = Field(None, description="Component parameters")
    status: Optional[str] = Field(None, description="Component status")


class ConfigDetailResponse(ConfigResponse):
    """Detailed configuration response schema with component information"""
    parser_info: Optional[ComponentInfo] = Field(None, description="Parser details")
    chunker_info: Optional[ComponentInfo] = Field(None, description="Chunker details") 
    indexer_info: Optional[ComponentInfo] = Field(None, description="Indexer details")
    usage_stats: Optional[Dict[str, Any]] = Field(None, description="Usage statistics")
    retriever_count: Optional[int] = Field(None, description="Number of retrievers using this config")


class ConfigListResponse(BaseModel):
    """Configuration list response schema"""
    total: int = Field(..., description="Total number of configurations")
    configs: List[ConfigResponse] = Field(..., description="List of configurations")


class ConfigUsageStats(BaseModel):
    """Configuration usage statistics schema"""
    total_retrievers: int = Field(default=0, description="Total retrievers using this config")
    active_retrievers: int = Field(default=0, description="Active retrievers")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    success_rate: Optional[float] = Field(None, description="Success rate percentage")


class ConfigSummary(BaseModel):
    """Configuration summary information schema"""
    id: UUID = Field(..., description="Configuration ID")
    name: Optional[str] = Field(None, description="Configuration name")
    status: str = Field(..., description="Configuration status")
    created_at: datetime = Field(..., description="Creation timestamp")
    parser_name: Optional[str] = Field(None, description="Parser name")
    chunker_name: Optional[str] = Field(None, description="Chunker name")
    indexer_name: Optional[str] = Field(None, description="Indexer name")
    retriever_count: int = Field(default=0, description="Number of retrievers using this config") 