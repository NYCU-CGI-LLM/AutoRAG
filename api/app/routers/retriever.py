from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session

from app.core.database import get_session
from app.services.retriever_service import RetrieverService
from app.schemas.retriever import (
    RetrieverCreateRequest,
    RetrieverBuildRequest, 
    RetrieverQueryRequest,
    RetrieverResponse,
    RetrieverBuildResponse,
    RetrieverQueryResponse,
    RetrieverStatsResponse,
    RetrieverListResponse,
    RetrieverStatusUpdate,
    RetrieverDetailResponse
)
from app.models.retriever import RetrieverStatus

router = APIRouter(
    prefix="/retriever",
    tags=["retriever"],
)

# Initialize service
retriever_service = RetrieverService()

@router.post("/", response_model=RetrieverBuildResponse, status_code=status.HTTP_201_CREATED)
async def create_retriever(
    request: RetrieverCreateRequest,
    session: Session = Depends(get_session)
):
    """
    Create a new retriever configuration and automatically build it
    
    This endpoint creates a retriever configuration and automatically executes:
    1. Parse files from the specified library
    2. Chunk the parsed content using the specified chunker  
    3. Create a vector index using the specified indexer
    
    The complete pipeline runs automatically after creation.
    """
    try:
        # Step 1: Create the retriever configuration
        retriever = retriever_service.create_retriever(
            session=session,
            name=request.name,
            library_id=request.library_id,
            parser_id=request.parser_id,
            chunker_id=request.chunker_id,
            indexer_id=request.indexer_id,
            description=request.description,
            top_k=request.top_k,
            params=request.params,
            collection_name=request.collection_name
        )
        
        # Step 2: Automatically build the retriever (parse → chunk → index)
        build_result = await retriever_service.build_retriever(
            session=session,
            retriever_id=retriever.id,
            force_rebuild=False
        )
        
        # Return the build result which includes creation and build information
        return RetrieverBuildResponse(
            retriever_id=str(retriever.id),
            status="success",
            parse_results=build_result["parse_results"],
            chunk_results=build_result["chunk_results"], 
            successful_chunks=build_result["successful_chunks"],
            collection_name=build_result["collection_name"],
            total_chunks=build_result["total_chunks"],
            index_result=build_result["index_result"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create and build retriever: {str(e)}")

@router.post("/create-only", response_model=RetrieverResponse, status_code=status.HTTP_201_CREATED)
async def create_retriever_only(
    request: RetrieverCreateRequest,
    session: Session = Depends(get_session)
):
    """
    Create a new retriever configuration without building it
    
    This endpoint only creates the retriever configuration without executing
    the parse → chunk → index pipeline. The retriever will be in PENDING status
    and needs to be built manually using the /build endpoint.
    """
    try:
        retriever = retriever_service.create_retriever(
            session=session,
            name=request.name,
            library_id=request.library_id,
            parser_id=request.parser_id,
            chunker_id=request.chunker_id,
            indexer_id=request.indexer_id,
            description=request.description,
            top_k=request.top_k,
            params=request.params,
            collection_name=request.collection_name
        )
        
        return RetrieverResponse(
            id=retriever.id,
            name=retriever.name,
            description=retriever.description,
            status=retriever.status.value,
            library_id=retriever.library_id,
            parser_id=retriever.parser_id,
            chunker_id=retriever.chunker_id,
            indexer_id=retriever.indexer_id,
            collection_name=retriever.collection_name,
            top_k=retriever.top_k,
            total_chunks=retriever.total_chunks,
            indexed_at=retriever.indexed_at,
            error_message=retriever.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create retriever: {str(e)}")

@router.get("/", response_model=RetrieverListResponse)
async def list_retrievers(
    library_id: Optional[UUID] = None,
    session: Session = Depends(get_session)
):
    """
    List all retrievers or filter by library
    
    Returns all retrievers with their current status and basic information.
    """
    try:
        if library_id:
            retrievers = retriever_service.get_retrievers_by_library(session, library_id)
        else:
            retrievers = retriever_service.get_active_retrievers(session)
        
        retriever_responses = []
        for retriever in retrievers:
            retriever_responses.append(RetrieverResponse(
                id=retriever.id,
                name=retriever.name,
                description=retriever.description,
                status=retriever.status.value,
                library_id=retriever.library_id,
                parser_id=retriever.parser_id,
                chunker_id=retriever.chunker_id,
                indexer_id=retriever.indexer_id,
                collection_name=retriever.collection_name,
                top_k=retriever.top_k,
                total_chunks=retriever.total_chunks,
                indexed_at=retriever.indexed_at,
                error_message=retriever.error_message
            ))
        
        return RetrieverListResponse(
            total=len(retriever_responses),
            retrievers=retriever_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list retrievers: {str(e)}")

@router.get("/{retriever_id}", response_model=RetrieverDetailResponse)
async def get_retriever(
    retriever_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed information about a specific retriever
    
    Returns complete retriever information including component details and statistics.
    """
    try:
        retriever = retriever_service.get_retriever_by_id(session, retriever_id)
        if not retriever:
            raise HTTPException(status_code=404, detail="Retriever not found")
        
        # Get stats for additional details
        stats = retriever_service.get_retriever_stats(session, retriever_id)
        
        return RetrieverDetailResponse(
            id=retriever.id,
            name=retriever.name,
            description=retriever.description,
            status=retriever.status.value,
            library_id=retriever.library_id,
            parser_id=retriever.parser_id,
            chunker_id=retriever.chunker_id,
            indexer_id=retriever.indexer_id,
            collection_name=retriever.collection_name,
            top_k=retriever.top_k,
            total_chunks=retriever.total_chunks,
            indexed_at=retriever.indexed_at,
            error_message=retriever.error_message,
            library_name=stats["configuration"]["library"]["name"] if stats["configuration"]["library"] else None,
            parser_info=stats["configuration"]["parser"],
            chunker_info=stats["configuration"]["chunker"],
            indexer_info=stats["configuration"]["indexer"],
            pipeline_stats=stats["pipeline_stats"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get retriever: {str(e)}")

@router.post("/{retriever_id}/build", response_model=RetrieverBuildResponse)
async def build_retriever(
    retriever_id: UUID,
    request: RetrieverBuildRequest = RetrieverBuildRequest(),
    session: Session = Depends(get_session)
):
    """
    Build a retriever by executing the complete pipeline
    
    This will:
    1. Parse all files in the associated library
    2. Chunk the parsed content using the specified chunker
    3. Create a vector index using the specified indexer
    
    The process may take some time depending on the number of files.
    """
    try:
        result = await retriever_service.build_retriever(
            session=session,
            retriever_id=retriever_id,
            force_rebuild=request.force_rebuild
        )
        
        return RetrieverBuildResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build retriever: {str(e)}")

@router.post("/{retriever_id}/query", response_model=RetrieverQueryResponse)
async def query_retriever(
    retriever_id: UUID,
    request: RetrieverQueryRequest,
    session: Session = Depends(get_session)
):
    """
    Query a retriever for similar content
    
    The retriever must be in ACTIVE status to be queried.
    Returns ranked search results with content and metadata.
    """
    try:
        results = await retriever_service.query_retriever(
            session=session,
            retriever_id=retriever_id,
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )
        
        return RetrieverQueryResponse(
            query=request.query,
            retriever_id=str(retriever_id),
            retriever_name=results[0]["retriever_name"] if results else "",
            total_results=len(results),
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query retriever: {str(e)}")

@router.get("/{retriever_id}/stats", response_model=RetrieverStatsResponse)
async def get_retriever_stats(
    retriever_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed statistics for a retriever
    
    Returns comprehensive information about the retriever including:
    - Configuration details
    - Pipeline statistics (files, parse results, chunks)
    - Index information
    """
    try:
        stats = retriever_service.get_retriever_stats(session, retriever_id)
        return RetrieverStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.put("/{retriever_id}/status", response_model=RetrieverResponse)
async def update_retriever_status(
    retriever_id: UUID,
    request: RetrieverStatusUpdate,
    session: Session = Depends(get_session)
):
    """
    Update retriever status (admin endpoint)
    
    This is primarily for administrative purposes or error recovery.
    """
    try:
        # Convert string status to enum
        status_enum = RetrieverStatus(request.status)
        
        retriever = retriever_service.update_retriever_status(
            session=session,
            retriever_id=retriever_id,
            status=status_enum,
            error_message=request.error_message
        )
        
        return RetrieverResponse(
            id=retriever.id,
            name=retriever.name,
            description=retriever.description,
            status=retriever.status.value,
            library_id=retriever.library_id,
            parser_id=retriever.parser_id,
            chunker_id=retriever.chunker_id,
            indexer_id=retriever.indexer_id,
            collection_name=retriever.collection_name,
            top_k=retriever.top_k,
            total_chunks=retriever.total_chunks,
            indexed_at=retriever.indexed_at,
            error_message=retriever.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")

@router.delete("/{retriever_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retriever(
    retriever_id: UUID,
    delete_collection: bool = True,
    session: Session = Depends(get_session)
):
    """
    Delete a retriever and optionally its vector collection
    
    Warning: This operation cannot be undone.
    Set delete_collection=False to keep the vector data.
    """
    try:
        success = retriever_service.delete_retriever(
            session=session,
            retriever_id=retriever_id,
            delete_collection=delete_collection
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete retriever")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete retriever: {str(e)}") 