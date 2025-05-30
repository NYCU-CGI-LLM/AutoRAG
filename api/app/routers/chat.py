from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session

from app.core.database import get_session
from app.services.chat_service import ChatService
from app.schemas.chat import (
    Chat,
    ChatCreate,
    ChatDetail,
    ChatSummary,
    MessageCreate,
    MessageResponse,
    Message,
    ChatConfig
)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

# Initialize chat service
chat_service = ChatService()


@router.post("/", response_model=Chat, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_create: ChatCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new chat bound to a retriever config.
    
    Creates a new chat session associated with the specified retriever configuration.
    The chat will use the retriever for context-aware responses and store default
    LLM parameters that will be used for all messages in this chat unless overridden.
    
    **Configuration Parameters:**
    - `name`: Optional display name for the chat
    - `retriever_id`: UUID of the retriever to use for document retrieval
    - `llm_model`: Default LLM model (e.g., "gpt-4o-mini", "gpt-4o")
    - `temperature`: Default creativity/randomness (0.0-2.0, default 0.7)
    - `top_p`: Default nucleus sampling (0.0-1.0, default 1.0)  
    - `top_k`: Default number of documents to retrieve (1-20, default 5)
    """
    try:
        chat = chat_service.create_chat(
            session=session,
            user_id=None,  # Let the service handle test user creation
            retriever_id=chat_create.retriever_id,
            name=chat_create.name,
            llm_model=chat_create.llm_model,
            temperature=chat_create.temperature,
            top_p=chat_create.top_p,
            top_k=chat_create.top_k,
            metadata=chat_create.metadata
        )
        
        # Create chat configuration for response
        chat_config = ChatConfig(
            llm_model=chat_create.llm_model or "gpt-4o-mini",
            temperature=chat_create.temperature if chat_create.temperature is not None else 0.7,
            top_p=chat_create.top_p if chat_create.top_p is not None else 1.0,
            top_k=chat_create.top_k if chat_create.top_k is not None else 5
        )
        
        # Convert to response format with proper timestamps
        now = datetime.utcnow()
        response = Chat(
            id=chat.id,
            name=chat_create.name,
            retriever_id=chat.retriever_id,
            metadata=chat_create.metadata,
            message_count=0,
            last_activity=now,
            created_at=now,
            updated_at=now,
            config=chat_config
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")


@router.get("/", response_model=List[ChatSummary])
async def list_chats(session: Session = Depends(get_session)):
    """
    List all chats.
    
    Returns a list of all chat sessions for the test user,
    including basic metadata and activity information.
    """
    try:
        # Get or create test user to ensure we have a valid user_id
        test_user = chat_service.get_or_create_test_user(session)
        
        summaries = chat_service.get_chat_summaries(
            session=session,
            user_id=test_user.id
        )
        
        # Convert to response format
        chat_summaries = [
            ChatSummary(
                id=summary["id"],
                name=summary["name"],
                message_count=summary["message_count"],
                last_activity=datetime.utcnow(),  # Use current time as proxy
                retriever_config_name=summary["retriever_config_name"],
                config=ChatConfig(**summary["config"])
            )
            for summary in summaries
        ]
        
        return chat_summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list chats: {str(e)}")


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get full chat object (metadata + dialogs).
    
    Returns complete chat information including all messages, metadata,
    and associated retriever configuration details.
    """
    try:
        chat_details = chat_service.get_chat_with_details(
            session=session,
            chat_id=chat_id
        )
        
        # Convert messages to proper format
        now = datetime.utcnow()
        messages = [
            Message(
                id=msg["id"],
                chat_id=chat_id,
                role=msg["role"],
                content=msg["content"],
                metadata={"llm_model": msg["llm_model"]},
                created_at=now,
                updated_at=now
            )
            for msg in chat_details["messages"]
        ]
        
        chat_detail = ChatDetail(
            id=chat_details["id"],
            name=f"Chat with {chat_details['retriever_name']}",
            retriever_id=chat_details["retriever_id"],
            metadata={},
            message_count=chat_details["message_count"],
            last_activity=now,
            created_at=now,
            updated_at=now,
            config=ChatConfig(**chat_details["config"]),
            messages=messages,
            retriever_config_name=chat_details["retriever_name"]
        )
        
        return chat_detail
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat: {str(e)}")


@router.post("/{chat_id}", response_model=MessageResponse)
async def send_message(
    chat_id: UUID,
    message_create: MessageCreate,
    session: Session = Depends(get_session)
):
    """
    Append a dialog turn.
    
    Send a new message to the chat and receive an AI-generated response.
    The response will be context-aware based on the associated retriever configuration.
    
    **Message Parameters:**
    - `message`: The user's message content
    - `model`: Optional override for the LLM model (uses chat default if not provided)
    - `temperature`: Optional override for temperature (uses chat default if not provided) 
    - `top_p`: Optional override for top_p (uses chat default if not provided)
    - `top_k`: Optional override for retrieval count (uses chat default if not provided)
    - `stream`: Whether to stream the response (default false)
    - `context_config`: Additional context configuration (filters, system prompt, etc.)
    """
    try:
        result = await chat_service.send_message(
            session=session,
            chat_id=chat_id,
            message=message_create.message,
            model=message_create.model,
            temperature=message_create.temperature,
            top_p=message_create.top_p,
            top_k=message_create.top_k,
            stream=message_create.stream,
            context_config=message_create.context_config
        )
        
        response = MessageResponse(
            message_id=result["message_id"],
            response=result["response"],
            sources=result["sources"],
            model_used=result["model_used"],
            processing_time=result["processing_time"],
            token_usage=result.get("token_usage"),
            config_used=result.get("config_used", {})
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_chat(
    chat_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Delete a chat session.
    
    Permanently delete a chat session and all its associated messages.
    This operation cannot be undone.
    """
    try:
        success = chat_service.delete_chat(session=session, chat_id=chat_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete chat")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")


@router.delete("/{chat_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_message(
    chat_id: UUID,
    message_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Delete a specific message from the chat.
    
    Remove a single message from the chat history.
    This operation cannot be undone.
    """
    try:
        success = chat_service.delete_message(
            session=session,
            chat_id=chat_id,
            message_id=message_id
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete message")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")


@router.put("/{chat_id}/name", include_in_schema=False)
async def update_chat_name(
    chat_id: UUID,
    name: str,
    session: Session = Depends(get_session)
):
    """
    Update chat name.
    
    Update the display name of the chat session.
    """
    try:
        chat = chat_service.update_chat_name(
            session=session,
            chat_id=chat_id,
            name=name
        )
        
        return {"message": f"Chat name updated to: {name}", "chat_id": str(chat.id)}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chat name: {str(e)}") 