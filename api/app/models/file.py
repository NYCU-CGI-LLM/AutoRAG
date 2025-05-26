from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .library import Library


class File(SQLModel, table=True):
    __tablename__ = "file"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    library_id: UUID = Field(foreign_key="library.id", index=True)
    file_name: str = Field(..., max_length=255)
    
    # Relationships
    library: "Library" = Relationship(back_populates="files") 