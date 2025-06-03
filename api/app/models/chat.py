from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .retriever import Retriever
    from .dialog import Dialog


class Chat(SQLModel, table=True):
    __tablename__ = "chat"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    retriever_id: UUID = Field(foreign_key="retriever.id", index=True)
    
    # Add extra_data field to store chat name and configuration
    extra_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'"))
    )
    
    # Relationships
    retriever: "Retriever" = Relationship(back_populates="chats")
    dialogs: List["Dialog"] = Relationship(back_populates="chat")
