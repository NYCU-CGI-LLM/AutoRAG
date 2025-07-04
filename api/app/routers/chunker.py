from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session

from app.core.database import get_session
from app.services.chunker_service import ChunkerService
from app.schemas.chunker import ChunkerResponse, ChunkerListResponse, ChunkerDetailResponse

router = APIRouter(
    prefix="/chunker",
    tags=["Chunker"],
)

chunker_service = ChunkerService()


@router.get("/", response_model=ChunkerListResponse)
async def list_chunkers(
    session: Session = Depends(get_session),
    status: Optional[str] = None,
    module_type: Optional[str] = None,
    chunk_method: Optional[str] = None,
    limit: int = 50
):
    """
    List all available chunkers.
    
    Returns a list of chunker configurations with filtering options.
    
    **Parameters:**
    - `status`: Filter by chunker status (active/draft/deprecated)
    - `module_type`: Filter by module type (llama_index_chunk, langchain_chunk, etc.)
    - `chunk_method`: Filter by chunk method (Token, Sentence, Character, etc.)
    - `limit`: Maximum number of results to return
    """
    try:
        if status:
            chunkers = chunker_service.get_chunkers_by_status(session, status, limit)
        else:
            chunkers = chunker_service.get_active_chunkers(session)[:limit]
        
        chunker_responses = [
            ChunkerResponse(
                id=chunker.id,
                name=chunker.name,
                module_type=chunker.module_type,
                chunk_method=chunker.chunk_method,
                chunk_size=chunker.chunk_size,
                chunk_overlap=chunker.chunk_overlap,
                params=chunker.params,
                status=chunker.status.value
            )
            for chunker in chunkers
        ]
        
        return ChunkerListResponse(
            total=len(chunker_responses),
            chunkers=chunker_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list chunkers: {str(e)}")


@router.get("/{chunker_id}", response_model=ChunkerDetailResponse, include_in_schema=False)
async def get_chunker(
    chunker_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed information about a specific chunker.
    
    Returns comprehensive chunker information including configuration,
    chunking strategy, and usage statistics.
    """
    try:
        chunker = chunker_service.get_chunker_by_id(session, chunker_id)
        if not chunker:
            raise HTTPException(status_code=404, detail="Chunker not found")
        
        # Get usage statistics
        usage_stats = chunker_service.get_chunker_usage_stats(session, chunker_id)
        
        return ChunkerDetailResponse(
            id=chunker.id,
            name=chunker.name,
            module_type=chunker.module_type,
            chunk_method=chunker.chunk_method,
            chunk_size=chunker.chunk_size,
            chunk_overlap=chunker.chunk_overlap,
            params=chunker.params,
            status=chunker.status.value,
            usage_stats=usage_stats,
            description=f"{chunker.chunk_method} chunker using {chunker.module_type} with size {chunker.chunk_size}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunker: {str(e)}")


@router.get("/{chunker_id}/chunk-results", include_in_schema=False)
async def get_chunker_results(
    chunker_id: UUID,
    session: Session = Depends(get_session),
    status: Optional[str] = None,
    limit: int = 20
):
    """
    Get chunk results produced by this chunker.
    
    Returns a list of chunk results that were created using the specified chunker,
    with optional filtering by processing status.
    """
    try:
        chunker = chunker_service.get_chunker_by_id(session, chunker_id)
        if not chunker:
            raise HTTPException(status_code=404, detail="Chunker not found")
        
        chunk_results = chunker_service.get_chunk_results(
            session, chunker_id=chunker_id, status=status
        )[:limit]
        
        return {
            "chunker_id": str(chunker_id),
            "chunker_name": chunker.name,
            "chunk_results": [
                {
                    "result_id": str(result.id),
                    "file_id": str(result.file_id),
                    "file_parse_result_id": str(result.file_parse_result_id),
                    "status": result.status.value,
                    "chunked_at": result.chunked_at.isoformat() if result.chunked_at else None,
                    "error_message": result.error_message,
                    "bucket": result.bucket,
                    "object_key": result.object_key
                }
                for result in chunk_results
            ],
            "total_results": len(chunk_results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk results: {str(e)}") 