from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import ARRAY, String, text
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from enum import Enum

if TYPE_CHECKING:
    from .file_parse_result import FileParseResult


class EngineType(str, Enum):
    LANGCHAIN = "langchain"
    LLAMA_PARSE = "llama_parse"
    TESSERACT_OCR = "tesseract_ocr"
    PIPELINE = "pipeline"


class ParserStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Parser(SQLModel, table=True):
    __tablename__ = "parser"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=100, unique=True)  # e.g. pdf_pymupdf_v1
    engine_type: EngineType = Field(...)
    
    # Use SQLAlchemy for PostgreSQL ARRAY type
    supported_mime: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, server_default=text("'{}'"))
    )
    
    # Use SQLAlchemy for PostgreSQL JSONB type
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    status: ParserStatus = Field(default=ParserStatus.ACTIVE)
    
    # Relationships
    parse_results: List["FileParseResult"] = Relationship(back_populates="parser") 