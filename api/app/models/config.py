from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .parser import Parser
    from .chunker import Chunker
    from .indexer import Indexer
    from .retriever import Retriever


class ConfigStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Config(SQLModel, table=True):
    __tablename__ = "config"
    
    # Primary key
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    
    # Component references - what makes this config unique
    parser_id: UUID = Field(foreign_key="parser.id", ondelete="CASCADE")
    chunker_id: UUID = Field(foreign_key="chunker.id", ondelete="CASCADE") 
    indexer_id: UUID = Field(foreign_key="indexer.id", ondelete="CASCADE")
    
    # Configuration metadata
    name: Optional[str] = Field(None, max_length=100, description="Configuration name")
    description: Optional[str] = Field(None, max_length=500, description="Configuration description")
    status: ConfigStatus = Field(default=ConfigStatus.ACTIVE, description="Configuration status")
    
    # Additional configuration parameters stored as JSON
    params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    parser: "Parser" = Relationship(back_populates="configs")
    chunker: "Chunker" = Relationship(back_populates="configs")
    indexer: "Indexer" = Relationship(back_populates="configs")
    retrievers: List["Retriever"] = Relationship(back_populates="config", cascade_delete=True)
    
    # Table constraints and indexes
    __table_args__ = (
        # Ensure unique combination of parser, chunker, indexer for active configs
        UniqueConstraint('parser_id', 'chunker_id', 'indexer_id', 'status',
                        name='uniq_parser_chunker_indexer_status'),
        Index('config_parser_idx', 'parser_id'),
        Index('config_chunker_idx', 'chunker_id'),
        Index('config_indexer_idx', 'indexer_id'),
        Index('config_status_idx', 'status'),
        Index('config_created_at_idx', 'created_at'),
    ) 