from uuid import UUID, uuid4
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class IndexingVariationBase(BaseModel):
    variation_name: Optional[str] = Field(default=None, description="A custom name for this indexing variation.")
    description: Optional[str] = Field(default=None, description="A description for this indexing variation.")
    index_config_filename: Optional[str] = Field(
        default=None,
        description="Name of the vectordb configuration key (e.g., 'chroma_openai') to use for indexing."
    )

class IndexingVariationCreate(IndexingVariationBase):
    pass

class IndexingVariation(IndexingVariationBase):
    id: UUID = Field(default_factory=uuid4, description="UUID of this indexing variation")
    kb_id: UUID = Field(..., description="Knowledge Base ID this variation belongs to")
    parse_variation_id: UUID = Field(..., description="Parsing variation ID this indexing is derived from")
    chunk_variation_id: UUID = Field(..., description="Chunking variation ID this indexing is derived from")
    status: str = Field(default="pending", description="Status of the indexing variation")
    celery_task_id: Optional[str] = Field(default=None, description="Celery task ID for asynchronous indexing")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    output_dir: Optional[str] = Field(default=None, description="Directory path where indexing outputs are stored")
    indexed_file_path: Optional[str] = Field(default=None, description="Path to the final indexed file (if any)")

    class Config:
        orm_mode = True 