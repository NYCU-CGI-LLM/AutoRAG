from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel
from enum import Enum


class ChatBase(BaseModel):
    name: Optional[str] = Field(None, description="Chat session name")
    retriever_config_id: UUID = Field(..., description="Associated retriever configuration ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Chat metadata")


class ChatCreate(ChatBase):
    pass


class Chat(ChatBase, IDModel, TimestampModel):
    message_count: int = Field(default=0, description="Number of messages in the chat")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    
    class Config:
        from_attributes = True


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageBase(BaseModel):
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Message metadata")


class Message(MessageBase, IDModel, TimestampModel):
    chat_id: UUID = Field(..., description="Associated chat ID")
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    message: str = Field(..., description="User message content")
    model: Optional[str] = Field(default="gpt-3.5-turbo", description="AI model to use")
    stream: bool = Field(default=False, description="Whether to stream the response")
    context_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Context configuration")


class MessageResponse(BaseModel):
    message_id: UUID = Field(..., description="Message ID")
    response: str = Field(..., description="Assistant response")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved sources")
    model_used: str = Field(..., description="AI model used")
    processing_time: float = Field(..., description="Processing time in seconds")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="Token usage statistics")


class ChatDetail(Chat):
    messages: List[Message] = Field(default_factory=list, description="Chat messages")
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name")


class ChatSummary(BaseModel):
    id: UUID = Field(..., description="Chat ID")
    name: Optional[str] = Field(None, description="Chat name")
    message_count: int = Field(..., description="Number of messages")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name") 