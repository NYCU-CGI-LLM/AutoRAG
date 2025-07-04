from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .chat import Chat


class SpeakerEnum(str, Enum):
    BOT = "BOT"
    ME = "ME"


class Dialog(SQLModel, table=True):
    __tablename__ = "dialog"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    chat_id: UUID = Field(foreign_key="chat.id", index=True)
    speaker: str = Field(..., max_length=10)  # ENUM: BOT, ME
    content: str = Field(...)
    llm_model: str = Field(..., max_length=100)
    
    # Timestamp fields for proper message tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat: "Chat" = Relationship(back_populates="dialogs") 