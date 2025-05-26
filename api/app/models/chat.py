from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .retriever import Retriever
    from .dialog import Dialog


class Chat(SQLModel, table=True):
    __tablename__ = "chat"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    retriever_id: UUID = Field(foreign_key="retriever.id", index=True)
    
    # Relationships
    retriever: "Retriever" = Relationship(back_populates="chats")
    dialogs: List["Dialog"] = Relationship(back_populates="chat")
