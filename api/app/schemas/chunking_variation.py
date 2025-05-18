from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ChunkingVariationBase(BaseModel):
    variation_name: Optional[str] = Field(default=None, description="A custom name for this chunking variation.")
    description: Optional[str] = Field(default=None, description="A description for this chunking variation.")
    chunker_config_filename: Optional[str] = Field(
        default=None, 
        description="Filename of the chunker configuration YAML (e.g., 'default_chunk.yaml') from the predefined chunker config directory."
    )

class ChunkingVariationCreate(ChunkingVariationBase):
    pass

class ChunkingVariation(ChunkingVariationBase):
    id: UUID = Field(default_factory=uuid4)
    kb_id: UUID # Belongs to this Knowledge Base
    parse_variation_id: UUID # Created from this Parsing Variation
    status: str = Field(default="pending", description="Status of the chunking variation (e.g., pending, processing, completed, failed).")
    celery_task_id: Optional[str] = Field(default=None, description="The Celery task ID for the chunking process.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    output_dir: Optional[str] = Field(default=None, description="Path to the directory where chunked outputs for this variation are stored.")
    # Typically, chunking might result in multiple files or a structured output.
    # For now, let's assume a primary output file path, similar to parsing.
    # This might need adjustment based on how AutoRAG chunker saves its output.
    chunked_file_path: Optional[str] = Field(default=None, description="Path to the primary output file from this chunking variation (e.g., a .parquet file or a manifest).")

    class Config:
        # For Pydantic V2, use from_attributes = True. For V1, orm_mode = True.
        # Assuming Pydantic v1 or FastAPI handling this correctly.
        orm_mode = True
        # If using Pydantic v2, uncomment the line below and comment out orm_mode
        # from_attributes = True 