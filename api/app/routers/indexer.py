from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session

from app.core.database import get_session
from app.services.index_service import IndexService
from app.schemas.indexer import IndexerResponse, IndexerListResponse, IndexerDetailResponse

router = APIRouter(
    prefix="/indexer",
    tags=["Indexer"],
)

index_service = IndexService()


@router.get("/", response_model=IndexerListResponse)
async def list_indexers(
    session: Session = Depends(get_session),
    status: Optional[str] = None,
    index_type: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 50
):
    """
    List all available indexers.
    
    Returns a list of indexer configurations with filtering options.
    
    **Parameters:**
    - `status`: Filter by indexer status (active/draft/deprecated)
    - `index_type`: Filter by index type (vector, bm25, hybrid, etc.)
    - `model`: Filter by model name (for vector indexers: embedding model, for bm25: tokenizer)
    - `limit`: Maximum number of results to return
    """
    try:
        if status:
            indexers = index_service.get_indexers_by_status(session, status, limit)
        else:
            indexers = index_service.get_active_indexers(session)[:limit]
        
        indexer_responses = [
            IndexerResponse(
                id=indexer.id,
                name=indexer.name,
                index_type=indexer.index_type,
                model=indexer.model,
                params=indexer.params,
                status=indexer.status.value
            )
            for indexer in indexers
        ]
        
        return IndexerListResponse(
            total=len(indexer_responses),
            indexers=indexer_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list indexers: {str(e)}")


@router.get("/{indexer_id}", response_model=IndexerDetailResponse, include_in_schema=False)
async def get_indexer(
    indexer_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed information about a specific indexer.
    
    Returns comprehensive indexer information including configuration,
    index type details, and usage statistics.
    """
    try:
        indexer = index_service.get_indexer_by_id(session, indexer_id)
        if not indexer:
            raise HTTPException(status_code=404, detail="Indexer not found")
        
        # Get usage statistics
        usage_stats = index_service.get_indexer_usage_stats(session, indexer_id)
        
        return IndexerDetailResponse(
            id=indexer.id,
            name=indexer.name,
            index_type=indexer.index_type,
            model=indexer.model,
            params=indexer.params,
            status=indexer.status.value,
            usage_stats=usage_stats,
            description=f"{indexer.index_type} indexer using {indexer.model} model"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get indexer: {str(e)}")


@router.get("/{indexer_id}/collections", include_in_schema=False)
async def get_indexer_collections(
    indexer_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get collections created by this indexer.
    
    Returns a list of vector database collections or indexes that were
    created using the specified indexer configuration.
    """
    try:
        indexer = index_service.get_indexer_by_id(session, indexer_id)
        if not indexer:
            raise HTTPException(status_code=404, detail="Indexer not found")
        
        collections = index_service.get_indexer_collections(session, indexer_id)
        
        return {
            "indexer_id": str(indexer_id),
            "indexer_name": indexer.name,
            "index_type": indexer.index_type,
            "model": indexer.model,
            "collections": [
                {
                    "collection_name": collection["name"],
                    "retriever_id": str(collection["retriever_id"]),
                    "document_count": collection["document_count"],
                    "created_at": collection["created_at"],
                    "status": collection["status"]
                }
                for collection in collections
            ],
            "total_collections": len(collections)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get indexer collections: {str(e)}")


@router.get("/{indexer_id}/compatible-models", include_in_schema=False)
async def get_compatible_models(
    indexer_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get models compatible with this indexer type.
    
    Returns a list of models that can be used with the specified indexer
    based on the index type (embedding models for vector, tokenizers for BM25, etc.).
    """
    try:
        indexer = index_service.get_indexer_by_id(session, indexer_id)
        if not indexer:
            raise HTTPException(status_code=404, detail="Indexer not found")
        
        compatible_models = index_service.get_compatible_models(indexer.index_type)
        
        return {
            "indexer_id": str(indexer_id),
            "indexer_name": indexer.name,
            "index_type": indexer.index_type,
            "current_model": indexer.model,
            "compatible_models": compatible_models,
            "recommendations": index_service.get_model_recommendations(indexer.index_type)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compatible models: {str(e)}") 