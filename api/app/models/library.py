from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING:
    from .file import File
    from .retriever import Retriever


class LibraryTypeEnum(str):
    REGULAR = "regular"
    BENCH = "bench"


class Library(SQLModel, table=True):
    __tablename__ = "library"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None)
    type: str = Field(default=LibraryTypeEnum.REGULAR, max_length=50)  # ENUM
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    files: List["File"] = Relationship(back_populates="library")
    retrievers: List["Retriever"] = Relationship(back_populates="library") 