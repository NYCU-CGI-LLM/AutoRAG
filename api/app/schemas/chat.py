from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel
from enum import Enum


class ChatBase(BaseModel):
    name: Optional[str] = Field(None, description="Chat session name")
    retriever_id: UUID = Field(..., description="Associated retriever ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Chat metadata")


class ChatCreate(ChatBase):
    # LLM Configuration
    llm_model: Optional[str] = Field(default="gpt-3.5-turbo", description="LLM model to use for this chat")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature (0.0-2.0)")
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="LLM top_p parameter (0.0-1.0)")
    
    # Retrieval Configuration
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of documents to retrieve (1-20)")


class ChatConfig(BaseModel):
    """Chat configuration settings that can be stored and reused"""
    llm_model: str = Field(default="gpt-3.5-turbo", description="Default LLM model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Default top_p")
    top_k: int = Field(default=5, ge=1, le=20, description="Default top_k for retrieval")


class Chat(ChatBase, IDModel, TimestampModel):
    message_count: int = Field(default=0, description="Number of messages in the chat")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    
    # Store chat-specific configuration
    config: ChatConfig = Field(default_factory=ChatConfig, description="Chat configuration settings")
    
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
    
    # Optional overrides for this specific message
    model: Optional[str] = Field(None, description="Override LLM model for this message")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Override temperature for this message")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Override top_p for this message") 
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Override top_k for this message")
    
    stream: bool = Field(default=False, description="Whether to stream the response")
    context_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context configuration")


class MessageResponse(BaseModel):
    message_id: UUID = Field(..., description="Message ID")
    response: str = Field(..., description="Assistant response")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved sources")
    model_used: str = Field(..., description="AI model used")
    processing_time: float = Field(..., description="Processing time in seconds")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="Token usage statistics")
    
    # Configuration used for this response
    config_used: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters used")


class ChatDetail(Chat):
    messages: List[Message] = Field(default_factory=list, description="Chat messages")
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name")


class ChatSummary(BaseModel):
    id: UUID = Field(..., description="Chat ID")
    name: Optional[str] = Field(None, description="Chat name")
    message_count: int = Field(..., description="Number of messages")
    last_activity: datetime = Field(..., description="Last activity timestamp")
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name")
    config: ChatConfig = Field(..., description="Chat configuration settings") 