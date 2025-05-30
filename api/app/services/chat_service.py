import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.chat import Chat
from app.models.dialog import Dialog, SpeakerEnum
from app.models.retriever import Retriever, RetrieverStatus
from app.services.retriever_service import RetrieverService

import openai
import os

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for managing chat sessions and generating AI responses
    with retrieval-augmented generation (RAG)
    """
    
    def __init__(self):
        self.retriever_service = RetrieverService()
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
    
    def create_chat(
        self,
        session: Session,
        user_id: UUID,
        retriever_id: UUID,
        name: Optional[str] = None
    ) -> Chat:
        """
        Create a new chat session associated with a retriever
        """
        try:
            # Validate retriever exists and is active
            retriever = self.retriever_service.get_retriever_by_id(session, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            if retriever.status != RetrieverStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Retriever is not active. Status: {retriever.status.value}"
                )
            
            # Generate chat name if not provided
            if not name:
                name = f"Chat with {retriever.name}"
            
            chat = Chat(
                user_id=user_id,
                retriever_id=retriever_id
            )
            
            session.add(chat)
            session.commit()
            session.refresh(chat)
            
            logger.info(f"Created chat {chat.id} for user {user_id} with retriever {retriever_id}")
            return chat
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create chat: {e}")
            raise HTTPException(status_code=500, detail="Failed to create chat")
    
    def get_chat_by_id(self, session: Session, chat_id: UUID) -> Optional[Chat]:
        """Get chat by ID"""
        return session.get(Chat, chat_id)
    
    def get_user_chats(self, session: Session, user_id: UUID) -> List[Chat]:
        """Get all chats for a user"""
        statement = select(Chat).where(Chat.user_id == user_id)
        return session.exec(statement).all()
    
    def get_chat_dialogs(self, session: Session, chat_id: UUID) -> List[Dialog]:
        """Get all dialogs in a chat, ordered by creation time"""
        statement = (
            select(Dialog)
            .where(Dialog.chat_id == chat_id)
            .order_by(Dialog.id)  # Assuming chronological order by ID
        )
        return session.exec(statement).all()
    
    async def send_message(
        self,
        session: Session,
        chat_id: UUID,
        message: str,
        model: str = "gpt-3.5-turbo",
        stream: bool = False,
        context_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message and generate AI response using RAG
        
        Returns:
            Dict containing response, sources, processing time, etc.
        """
        start_time = time.time()
        
        try:
            # Get chat and validate
            chat = session.get(Chat, chat_id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
            
            # Save user message
            user_dialog = Dialog(
                chat_id=chat_id,
                speaker=SpeakerEnum.ME,
                content=message,
                llm_model=model
            )
            session.add(user_dialog)
            session.commit()
            session.refresh(user_dialog)
            
            # Get retriever context
            context_config = context_config or {}
            top_k = context_config.get("top_k", 5)
            filters = context_config.get("filters")
            
            retrieval_results = await self.retriever_service.query_retriever(
                session=session,
                retriever_id=chat.retriever_id,
                query=message,
                top_k=top_k,
                filters=filters
            )
            
            # Get conversation history
            conversation_history = self.get_chat_dialogs(session, chat_id)
            
            # Format prompt with context and history
            formatted_prompt = self._format_rag_prompt(
                user_message=message,
                retrieval_results=retrieval_results,
                conversation_history=conversation_history[-10:],  # Last 10 exchanges
                context_config=context_config
            )
            
            # Generate AI response
            ai_response, token_usage = await self._generate_openai_response(
                prompt=formatted_prompt,
                model=model,
                stream=stream
            )
            
            # Save AI response
            ai_dialog = Dialog(
                chat_id=chat_id,
                speaker=SpeakerEnum.BOT,
                content=ai_response,
                llm_model=model
            )
            session.add(ai_dialog)
            session.commit()
            session.refresh(ai_dialog)
            
            processing_time = time.time() - start_time
            
            # Format sources from retrieval results
            sources = [
                {
                    "content": result.get("content", "")[:200] + "...",  # Truncate for preview
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                    "doc_id": result.get("doc_id", ""),
                }
                for result in retrieval_results[:3]  # Top 3 sources
            ]
            
            logger.info(f"Generated response for chat {chat_id} in {processing_time:.2f}s")
            
            return {
                "message_id": ai_dialog.id,
                "response": ai_response,
                "sources": sources,
                "model_used": model,
                "processing_time": processing_time,
                "token_usage": token_usage,
                "retrieval_context": {
                    "total_sources": len(retrieval_results),
                    "query": message,
                    "top_k": top_k
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to send message: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")
    
    def _format_rag_prompt(
        self,
        user_message: str,
        retrieval_results: List[Dict[str, Any]],
        conversation_history: List[Dialog],
        context_config: Dict[str, Any]
    ) -> str:
        """
        Format the RAG prompt with retrieved context and conversation history
        """
        # System instruction
        system_prompt = context_config.get(
            "system_prompt",
            "You are a helpful AI assistant. Use the provided context to answer questions accurately. "
            "If the context doesn't contain relevant information, say so clearly."
        )
        
        # Format retrieved context
        context_text = ""
        if retrieval_results:
            context_text = "\n--- RELEVANT CONTEXT ---\n"
            for i, result in enumerate(retrieval_results[:5], 1):  # Top 5 results
                content = result.get("content", "")
                score = result.get("score", 0.0)
                context_text += f"[Source {i}] (Relevance: {score:.3f})\n{content}\n\n"
            context_text += "--- END CONTEXT ---\n"
        
        # Format conversation history
        history_text = ""
        if conversation_history:
            history_text = "\n--- CONVERSATION HISTORY ---\n"
            for dialog in conversation_history:
                speaker = "You" if dialog.speaker == SpeakerEnum.BOT else "User"
                history_text += f"{speaker}: {dialog.content}\n"
            history_text += "--- END HISTORY ---\n"
        
        # Combine everything
        full_prompt = f"""
{system_prompt}

{context_text}
{history_text}

User: {user_message}
"""
        return full_prompt
    
    async def _generate_openai_response(
        self,
        prompt: str,
        model: str,
        stream: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate AI response using OpenAI
        
        Returns:
            Tuple containing response and token usage
        """
        try:
            # Use the newer OpenAI client approach
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            if stream:
                # Handle streaming response
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                
                # Note: Streaming doesn't provide token usage, so we estimate
                token_usage = {
                    "prompt_tokens": len(prompt.split()) * 1.3,  # Rough estimate
                    "completion_tokens": len(full_response.split()) * 1.3,
                    "total_tokens": 0
                }
                token_usage["total_tokens"] = token_usage["prompt_tokens"] + token_usage["completion_tokens"]
                
                return full_response, token_usage
            else:
                # Handle regular response
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                ai_response = response.choices[0].message.content
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
                return ai_response, token_usage
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback response
            return f"I apologize, but I encountered an error generating a response: {str(e)}", {}
    
    def delete_chat(self, session: Session, chat_id: UUID) -> bool:
        """
        Delete a chat and all its dialogs
        """
        try:
            chat = session.get(Chat, chat_id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
            
            # Delete all dialogs first (if not handled by cascade)
            dialogs_statement = select(Dialog).where(Dialog.chat_id == chat_id)
            dialogs = session.exec(dialogs_statement).all()
            for dialog in dialogs:
                session.delete(dialog)
            
            # Delete chat
            session.delete(chat)
            session.commit()
            
            logger.info(f"Deleted chat {chat_id} and {len(dialogs)} dialogs")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete chat {chat_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete chat")
    
    def delete_message(self, session: Session, chat_id: UUID, message_id: UUID) -> bool:
        """
        Delete a specific message from a chat
        """
        try:
            dialog = session.get(Dialog, message_id)
            if not dialog:
                raise HTTPException(status_code=404, detail="Message not found")
            
            if dialog.chat_id != chat_id:
                raise HTTPException(status_code=400, detail="Message does not belong to this chat")
            
            session.delete(dialog)
            session.commit()
            
            logger.info(f"Deleted message {message_id} from chat {chat_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete message {message_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete message")
    
    def update_chat_name(self, session: Session, chat_id: UUID, name: str) -> Chat:
        """
        Update chat name (if we add a name field to Chat model)
        Note: Current Chat model doesn't have a name field, but this is for future use
        """
        try:
            chat = session.get(Chat, chat_id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
            
            # TODO: Add name field to Chat model
            # chat.name = name
            session.add(chat)
            session.commit()
            session.refresh(chat)
            
            logger.info(f"Updated chat {chat_id} name to: {name}")
            return chat
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update chat name: {e}")
            raise HTTPException(status_code=500, detail="Failed to update chat name")
    
    def get_chat_with_details(self, session: Session, chat_id: UUID) -> Dict[str, Any]:
        """
        Get chat with full details including dialogs and retriever info
        """
        try:
            chat = session.get(Chat, chat_id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
            
            # Get retriever info
            retriever = self.retriever_service.get_retriever_by_id(session, chat.retriever_id)
            
            # Get dialogs
            dialogs = self.get_chat_dialogs(session, chat_id)
            
            # Format response
            chat_detail = {
                "id": chat.id,
                "user_id": chat.user_id,
                "retriever_id": chat.retriever_id,
                "retriever_name": retriever.name if retriever else "Unknown",
                "message_count": len(dialogs),
                "last_activity": dialogs[-1].id if dialogs else None,  # Use last dialog ID as proxy
                "messages": [
                    {
                        "id": dialog.id,
                        "role": "user" if dialog.speaker == SpeakerEnum.ME else "assistant",
                        "content": dialog.content,
                        "llm_model": dialog.llm_model,
                        "created_at": dialog.id  # Proxy for timestamp since Dialog model might not have it
                    }
                    for dialog in dialogs
                ]
            }
            
            return chat_detail
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get chat details for {chat_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get chat details")
    
    def get_chat_summaries(self, session: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get chat summaries for a user
        """
        try:
            chats = self.get_user_chats(session, user_id)
            summaries = []
            
            for chat in chats:
                # Get retriever info
                retriever = self.retriever_service.get_retriever_by_id(session, chat.retriever_id)
                
                # Get dialog count
                dialogs = self.get_chat_dialogs(session, chat.id)
                
                summary = {
                    "id": chat.id,
                    "name": f"Chat with {retriever.name}" if retriever else "Chat",
                    "message_count": len(dialogs),
                    "last_activity": dialogs[-1].id if dialogs else None,  # Proxy
                    "retriever_config_name": retriever.name if retriever else "Unknown"
                }
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get chat summaries for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get chat summaries") 