from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ParsingVariationBase(BaseModel):
    variation_name: Optional[str] = None
    description: Optional[str] = None
    # Changed from Dict[str, Any] to str, representing the filename of the parser config
    parser_config_filename: Optional[str] = Field(default=None, description="Filename of the parser configuration YAML (e.g., 'default.yaml') from the predefined parse config directory.")

class ParsingVariationCreate(ParsingVariationBase):
    pass

class ParsingVariation(ParsingVariationBase):
    id: UUID = Field(default_factory=uuid4)
    kb_id: UUID
    status: str = "pending" # e.g., pending, processing, completed, failed
    celery_task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    output_dir: Optional[str] = None # Path to the variation's output directory
    parsed_file_path: Optional[str] = None # Path to the final .parquet file from this variation
    # parser_config field is inherited from ParsingVariationBase and is now parser_config_filename

    class Config:
        orm_mode = True # if you plan to use this with an ORM
        # For FastAPI, this helps ensure that datetime objects are correctly handled
        # and UUIDs are converted to strings when generating JSON responses.
        # If you're using Pydantic v2, orm_mode is now from_attributes = True
        # from_attributes = True # For Pydantic V2
        # For Pydantic v1, orm_mode is fine.
        # FastAPI typically handles datetime serialization well by default.
        # json_encoders can be used for custom serialization if needed but often not necessary for datetime/UUID. 