from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_session
from app.services.vectordb_service import VectorDBService
from app.models.embedding_stats import (
    EmbeddingStats, 
    EmbeddingStatsCreate, 
    EmbeddingStatsUpdate, 
    EmbeddingStatsResponse
)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

# Dependency to get VectorDB service
def get_vectordb_service() -> VectorDBService:
    return VectorDBService()

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    embedding_model: str = "openai_embed_3_large"
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    query: str
    library_id: UUID
    total_results: int
    results: List[Dict[str, Any]]

class StoreEmbeddingsRequest(BaseModel):
    doc_ids: List[str]
    contents: List[str]
    embedding_model: str = "openai_embed_3_large"
    metadata_list: Optional[List[Dict[str, Any]]] = None

class StoreEmbeddingsResponse(BaseModel):
    collection_name: str
    total_documents: int
    embedding_model: str
    library_id: str
    vector_dimension: int
    status: str


@router.post("/v1/library/{library_id}/embeddings/store", response_model=StoreEmbeddingsResponse)
async def store_embeddings(
    library_id: UUID,
    request: StoreEmbeddingsRequest,
    session: Session = Depends(get_session),
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """Store embeddings for a library"""
    try:
        # Store embeddings in ChromaDB
        result = vectordb_service.store_embeddings(
            library_id=library_id,
            doc_ids=request.doc_ids,
            contents=request.contents,
            embedding_model=request.embedding_model,
            metadata_list=request.metadata_list
        )
        
        # Update or create embedding stats in PostgreSQL
        stats_data = EmbeddingStatsCreate(
            library_id=library_id,
            collection_name=result["collection_name"],
            embedding_model=result["embedding_model"],
            total_documents=result["total_documents"],
            vector_dimension=result["vector_dimension"]
        )
        
        # Check if stats already exist
        existing_stats = session.exec(
            select(EmbeddingStats).where(
                EmbeddingStats.library_id == library_id,
                EmbeddingStats.embedding_model == request.embedding_model
            )
        ).first()
        
        if existing_stats:
            # Update existing stats
            existing_stats.total_documents = result["total_documents"]
            existing_stats.vector_dimension = result["vector_dimension"]
            existing_stats.updated_at = datetime.utcnow()
            session.add(existing_stats)
        else:
            # Create new stats
            new_stats = EmbeddingStats(**stats_data.model_dump())
            session.add(new_stats)
        
        session.commit()
        
        return StoreEmbeddingsResponse(**result)
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {str(e)}")


@router.post("/v1/library/{library_id}/embeddings/search", response_model=SearchResponse)
async def search_embeddings(
    library_id: UUID,
    request: SearchRequest,
    session: Session = Depends(get_session),
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """Search for similar embeddings in a library"""
    try:
        # Perform similarity search
        results = vectordb_service.similarity_search(
            library_id=library_id,
            query=request.query,
            top_k=request.top_k,
            embedding_model=request.embedding_model,
            filters=request.filters
        )
        
        # Update access statistics
        stats = session.exec(
            select(EmbeddingStats).where(
                EmbeddingStats.library_id == library_id,
                EmbeddingStats.embedding_model == request.embedding_model
            )
        ).first()
        
        if stats:
            stats.access_count += 1
            stats.last_accessed = datetime.utcnow()
            session.add(stats)
            session.commit()
        
        return SearchResponse(
            query=request.query,
            library_id=library_id,
            total_results=len(results),
            results=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/v1/library/{library_id}/embeddings/stats", response_model=List[EmbeddingStatsResponse])
async def get_embedding_stats(
    library_id: UUID,
    session: Session = Depends(get_session)
):
    """Get embedding statistics for a library"""
    try:
        stats = session.exec(
            select(EmbeddingStats).where(EmbeddingStats.library_id == library_id)
        ).all()
        
        return [EmbeddingStatsResponse.model_validate(stat) for stat in stats]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/v1/library/{library_id}/embeddings/collection/{embedding_model}/stats")
async def get_collection_stats(
    library_id: UUID,
    embedding_model: str,
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """Get real-time statistics for a specific collection"""
    try:
        stats = vectordb_service.get_collection_stats(library_id, embedding_model)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection stats: {str(e)}")


@router.delete("/v1/library/{library_id}/embeddings/collection/{embedding_model}")
async def delete_collection(
    library_id: UUID,
    embedding_model: str,
    session: Session = Depends(get_session),
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """Delete a collection and all its embeddings"""
    try:
        # Delete from ChromaDB
        result = vectordb_service.delete_collection(library_id, embedding_model)
        
        # Delete from PostgreSQL stats
        stats = session.exec(
            select(EmbeddingStats).where(
                EmbeddingStats.library_id == library_id,
                EmbeddingStats.embedding_model == embedding_model
            )
        ).first()
        
        if stats:
            session.delete(stats)
            session.commit()
        
        return result
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


@router.get("/v1/embeddings/collections")
async def list_all_collections(
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """List all collections in ChromaDB"""
    try:
        collections = vectordb_service.list_collections()
        return {"collections": collections}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/v1/embeddings/health")
async def health_check(
    vectordb_service: VectorDBService = Depends(get_vectordb_service)
):
    """Check VectorDB service health"""
    try:
        health = vectordb_service.health_check()
        return health
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") 