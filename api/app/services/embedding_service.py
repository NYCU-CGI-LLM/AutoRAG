import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from sqlmodel import Session
from fastapi import HTTPException

from app.services.vectordb_service import VectorDBService
from app.models.embedding_stats import EmbeddingStats, EmbeddingStatsCreate

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Simplified embedding service using ChromaDB
    
    Architecture:
    - ChromaDB: Store embeddings + metadata + documents
    - PostgreSQL: Store collection metadata and statistics
    """
    
    def __init__(self):
        self.vectordb_service = VectorDBService()
        
    def store_embeddings(
        self,
        session: Session,
        library_id: UUID,
        doc_ids: List[str],
        contents: List[str],
        embedding_model: str = "openai_embed_3_large",
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Store embeddings using simplified ChromaDB architecture
        
        Args:
            session: Database session
            library_id: Library UUID
            doc_ids: Document IDs
            contents: Document contents
            embedding_model: Model used for embeddings
            metadata_list: Optional metadata for each document
            
        Returns:
            Storage metadata
        """
        try:
            # Store in ChromaDB
            result = self.vectordb_service.store_embeddings(
                library_id=library_id,
                doc_ids=doc_ids,
                contents=contents,
                embedding_model=embedding_model,
                metadata_list=metadata_list
            )
            
            # Update PostgreSQL metadata
            self._update_embedding_stats(session, library_id, result)
            
            logger.info(f"Successfully stored {len(doc_ids)} embeddings for library {library_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {str(e)}")
    
    def similarity_search(
        self,
        session: Session,
        library_id: UUID,
        query: str,
        top_k: int = 10,
        embedding_model: str = "openai_embed_3_large",
        filters: Optional[Dict] = None
    ) -> Tuple[List[str], List[float]]:
        """
        Perform similarity search using ChromaDB
        
        Returns:
            Tuple of (doc_ids, scores)
        """
        try:
            # Perform search
            search_results = self.vectordb_service.similarity_search(
                library_id=library_id,
                query=query,
                top_k=top_k,
                embedding_model=embedding_model,
                filters=filters
            )
            
            # Update access statistics
            self._update_access_stats(session, library_id, embedding_model)
            
            # Extract doc_ids and scores
            doc_ids = [result["doc_id"] for result in search_results]
            scores = [result["score"] for result in search_results]
            
            return doc_ids, scores
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    def get_storage_stats(self, session: Session, library_id: UUID) -> Dict[str, Any]:
        """Get storage statistics for a library"""
        try:
            # Get PostgreSQL stats
            from sqlmodel import select
            stats = session.exec(
                select(EmbeddingStats).where(EmbeddingStats.library_id == library_id)
            ).all()
            
            # Get ChromaDB collections
            collections = self.vectordb_service.list_collections()
            library_collections = [
                c for c in collections 
                if c.get("library_id") == str(library_id)
            ]
            
            return {
                "library_id": str(library_id),
                "postgresql_stats": [
                    {
                        "collection_name": stat.collection_name,
                        "embedding_model": stat.embedding_model,
                        "total_documents": stat.total_documents,
                        "access_count": stat.access_count,
                        "last_accessed": stat.last_accessed,
                        "status": stat.status
                    }
                    for stat in stats
                ],
                "chromadb_collections": library_collections,
                "total_collections": len(library_collections),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}
    
    def _update_embedding_stats(
        self, 
        session: Session, 
        library_id: UUID, 
        storage_result: Dict[str, Any]
    ):
        """Update embedding statistics in PostgreSQL"""
        try:
            from sqlmodel import select
            
            # Check if stats already exist
            existing_stats = session.exec(
                select(EmbeddingStats).where(
                    EmbeddingStats.library_id == library_id,
                    EmbeddingStats.embedding_model == storage_result["embedding_model"]
                )
            ).first()
            
            if existing_stats:
                # Update existing stats
                existing_stats.total_documents = storage_result["total_documents"]
                existing_stats.vector_dimension = storage_result["vector_dimension"]
                existing_stats.updated_at = datetime.utcnow()
                session.add(existing_stats)
            else:
                # Create new stats
                stats_data = EmbeddingStatsCreate(
                    library_id=library_id,
                    collection_name=storage_result["collection_name"],
                    embedding_model=storage_result["embedding_model"],
                    total_documents=storage_result["total_documents"],
                    vector_dimension=storage_result["vector_dimension"]
                )
                new_stats = EmbeddingStats(**stats_data.model_dump())
                session.add(new_stats)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error updating embedding stats: {str(e)}")
            session.rollback()
    
    def _update_access_stats(
        self, 
        session: Session, 
        library_id: UUID, 
        embedding_model: str
    ):
        """Update access statistics"""
        try:
            from sqlmodel import select
            
            stats = session.exec(
                select(EmbeddingStats).where(
                    EmbeddingStats.library_id == library_id,
                    EmbeddingStats.embedding_model == embedding_model
                )
            ).first()
            
            if stats:
                stats.access_count += 1
                stats.last_accessed = datetime.utcnow()
                session.add(stats)
                session.commit()
                
        except Exception as e:
            logger.warning(f"Failed to update access stats: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return self.vectordb_service.health_check() 