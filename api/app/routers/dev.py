"""
Development API endpoints for testing parser and chunker functionality
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import get_session 
from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
from app.services.qdrant_index_service import QdrantIndexService
from app.services.minio_service import MinIOService
from app.models.file import File
from app.models.parser import Parser
from app.models.chunker import Chunker
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.schemas.dev import (
    ParseRequest,
    ParseResponse,
    FileInfo,
    ParserInfo,
    ParseResultInfo,
    ParsedDataResponse,
    DeleteResponse,
    HealthResponse,
    ChunkRequest,
    ChunkResponse,
    ChunkerInfo,
    ChunkResultInfo,
    ChunkedDataResponse,
    # Index-related schemas
    CreateIndexRequest,
    SearchRequest,
    IndexResponse,
    SearchResponse,
    StatsResponse,
    ConfigExampleResponse,
    RequestExampleResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])

# Initialize services
qdrant_service = QdrantIndexService()

# Parser endpoints
@router.get("/parser/files", response_model=List[FileInfo])
async def list_files(
    session: Session = Depends(get_session),
    limit: int = Query(10, description="Maximum number of files to return")
):
    """List available files for parsing"""
    try:
        files = session.exec(select(File).limit(limit)).all()
        
        file_infos = []
        for file in files:
            file_infos.append(FileInfo(
                id=file.id,
                file_name=file.file_name,
                mime_type=file.mime_type,
                size_bytes=file.size_bytes,
                bucket=file.bucket,
                object_key=file.object_key,
                status=file.status.value if file.status else "unknown"
            ))
        
        return file_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.get("/parser/parsers", response_model=List[ParserInfo])
async def list_parsers(
    session: Session = Depends(get_session),
    limit: int = Query(50, description="Maximum number of parsers to return")
):
    """List available parsers"""
    try:
        parsers = session.exec(select(Parser).limit(limit)).all()
        
        parser_infos = []
        for parser in parsers:
            parser_infos.append(ParserInfo(
                id=parser.id,
                name=parser.name,
                module_type=parser.module_type,
                supported_mime=parser.supported_mime,
                params=parser.params,
                status=parser.status.value if parser.status else "unknown"
            ))
        
        return parser_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing parsers: {str(e)}")


@router.post("/parser/parse", response_model=ParseResponse)
async def parse_file(
    request: ParseRequest,
    session: Session = Depends(get_session)
):
    """Parse a file using specified parser"""
    try:
        parser_service = ParserService()
        
        # Get file and parser
        file = session.get(File, request.file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        parser = parser_service.get_parser_by_id(session, request.parser_id)
        if not parser:
            raise HTTPException(status_code=404, detail="Parser not found")
        
        # Parse the file
        result = parser_service._parse_single_file(session, file, parser)
        
        return ParseResponse(
            success=True,
            message="File parsed successfully",
            result_id=result.id,
            status=result.status.value if result.status else "unknown",
            error_message=result.error_message,
            extra_meta=result.extra_meta
        )
    except Exception as e:
        return ParseResponse(
            success=False,
            message=f"Error parsing file: {str(e)}",
            error_message=str(e)
        )


@router.get("/parser/parse-results", response_model=List[ParseResultInfo])
async def list_parse_results(
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    """List parse results"""
    try:
        statement = select(FileParseResult)
        
        if status:
            statement = statement.where(FileParseResult.status == status)
        
        statement = statement.limit(limit)
        parse_results = session.exec(statement).all()
        
        result_infos = []
        for result in parse_results:
            # Get file and parser info
            file = session.get(File, result.file_id)
            parser = session.get(Parser, result.parser_id)
            
            result_infos.append(ParseResultInfo(
                id=result.id,
                file_id=result.file_id,
                file_name=file.file_name if file else "Unknown",
                parser_id=result.parser_id,
                parser_name=parser.name if parser else "Unknown",
                status=result.status.value if result.status else "unknown",
                bucket=result.bucket,
                object_key=result.object_key,
                parsed_at=result.parsed_at.isoformat() if result.parsed_at else None,
                error_message=result.error_message,
                extra_meta=result.extra_meta
            ))
        
        return result_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing parse results: {str(e)}")


@router.get("/parser/parse-results/{result_id}/data", response_model=ParsedDataResponse)
async def get_parsed_data_preview(
    result_id: UUID,
    session: Session = Depends(get_session),
    preview_rows: int = Query(5, description="Number of rows to preview")
):
    """Get preview of parsed data"""
    try:
        parser_service = ParserService()
        df = parser_service.get_parsed_data(session, result_id)
        
        # Convert preview data to list of dicts
        preview_df = df.head(preview_rows)
        preview_data = []
        for i in range(len(preview_df)):
            row_data = {}
            for col in df.columns:
                value = preview_df.iloc[i][col]
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                row_data[col] = value
            preview_data.append(row_data)
        
        return ParsedDataResponse(
            success=True,
            message="Parsed data retrieved successfully",
            total_rows=len(df),
            columns=list(df.columns),
            preview_data=preview_data
        )
    except Exception as e:
        return ParsedDataResponse(
            success=False,
            message=f"Error getting parsed data: {str(e)}"
        )


# Chunker endpoints
@router.get("/chunker/chunkers", response_model=List[ChunkerInfo])
async def list_chunkers(
    session: Session = Depends(get_session),
    limit: int = Query(50, description="Maximum number of chunkers to return")
):
    """List available chunkers"""
    try:
        chunker_service = ChunkerService()
        chunkers = chunker_service.get_active_chunkers(session)
        
        chunker_infos = []
        for chunker in chunkers[:limit]:
            chunker_infos.append(ChunkerInfo(
                id=chunker.id,
                name=chunker.name,
                module_type=chunker.module_type,
                chunk_method=chunker.chunk_method,
                chunk_size=chunker.chunk_size,
                chunk_overlap=chunker.chunk_overlap,
                params=chunker.params,
                status=chunker.status.value if chunker.status else "unknown"
            ))
        
        return chunker_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing chunkers: {str(e)}")


@router.post("/chunker/chunk", response_model=ChunkResponse)
async def chunk_parsed_results(
    request: ChunkRequest,
    session: Session = Depends(get_session)
):
    """Chunk parsed results using specified chunker"""
    try:
        chunker_service = ChunkerService()
        
        # Chunk the parsed results
        results = chunker_service.chunk_parsed_results(
            session=session,
            parse_result_ids=request.parse_result_ids,
            chunker_id=request.chunker_id
        )
        
        # Convert results to dict format
        result_dicts = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            result_dict = {
                "id": str(result.id),
                "file_id": str(result.file_id),
                "file_parse_result_id": str(result.file_parse_result_id),
                "chunker_id": str(result.chunker_id),
                "status": result.status.value if result.status else "unknown",
                "bucket": result.bucket,
                "object_key": result.object_key,
                "chunked_at": result.chunked_at.isoformat() if result.chunked_at else None,
                "error_message": result.error_message,
                "extra_meta": result.extra_meta
            }
            result_dicts.append(result_dict)
            
            if result.status and result.status.value == "success":
                successful_count += 1
            else:
                failed_count += 1
        
        return ChunkResponse(
            success=True,
            message=f"Chunking completed. {successful_count} successful, {failed_count} failed",
            results=result_dicts,
            total_processed=len(results),
            successful_count=successful_count,
            failed_count=failed_count
        )
    except Exception as e:
        return ChunkResponse(
            success=False,
            message=f"Error chunking parsed results: {str(e)}",
            results=[],
            total_processed=0,
            successful_count=0,
            failed_count=0
        )


@router.get("/chunker/chunk-results", response_model=List[ChunkResultInfo])
async def list_chunk_results(
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    """List chunk results"""
    try:
        statement = select(FileChunkResult)
        
        if status:
            statement = statement.where(FileChunkResult.status == status)
        
        statement = statement.limit(limit)
        chunk_results = session.exec(statement).all()
        
        result_infos = []
        for result in chunk_results:
            # Get file and chunker info
            file = session.get(File, result.file_id)
            chunker = session.get(Chunker, result.chunker_id)
            
            result_infos.append(ChunkResultInfo(
                id=result.id,
                file_id=result.file_id,
                file_name=file.file_name if file else "Unknown",
                file_parse_result_id=result.file_parse_result_id,
                chunker_id=result.chunker_id,
                chunker_name=chunker.name if chunker else "Unknown",
                status=result.status.value if result.status else "unknown",
                bucket=result.bucket,
                object_key=result.object_key,
                chunked_at=result.chunked_at.isoformat() if result.chunked_at else None,
                error_message=result.error_message,
                extra_meta=result.extra_meta
            ))
        
        return result_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing chunk results: {str(e)}")


@router.get("/chunker/chunk-results/{result_id}/data", response_model=ChunkedDataResponse)
async def get_chunked_data_preview(
    result_id: UUID,
    session: Session = Depends(get_session),
    preview_rows: int = Query(5, description="Number of chunks to preview")
):
    """Get preview of chunked data"""
    try:
        chunker_service = ChunkerService()
        df = chunker_service.get_chunked_data(session, result_id)
        
        # Convert preview data to list of dicts
        preview_df = df.head(preview_rows)
        preview_data = []
        for i in range(len(preview_df)):
            row_data = {}
            for col in df.columns:
                value = preview_df.iloc[i][col]
                if isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                row_data[col] = value
            preview_data.append(row_data)
        
        return ChunkedDataResponse(
            success=True,
            message="Chunked data retrieved successfully",
            chunk_result_id=result_id,
            total_chunks=len(df),
            columns=list(df.columns),
            preview_data=preview_data
        )
    except Exception as e:
        return ChunkedDataResponse(
            success=False,
            message=f"Error getting chunked data: {str(e)}",
            chunk_result_id=result_id
        )


# Index endpoints (moved from dev/index.py)
@router.post("/index", response_model=IndexResponse)
async def create_index(
    request: CreateIndexRequest,
    session: Session = Depends(get_session)
):
    """
    Create vector index from chunk results
    
    **Minimal Usage (recommended for single-server setup):**
    ```json
    {
        "chunk_result_ids": [
            "38a95a37-f359-43b8-bde0-bb6f7419f57d",
            "f8b2c1e4-5678-9abc-def0-123456789abc"
        ],
        "collection_name": "my_documents"
    }
    ```
    
    **Full Configuration:**
    ```json
    {
        "chunk_result_ids": [
            "38a95a37-f359-43b8-bde0-bb6f7419f57d",
            "f8b2c1e4-5678-9abc-def0-123456789abc"
        ],
        "collection_name": "my_documents",
        "embedding_model": "openai_embed_3_large",
        "qdrant_config": {
            "client_type": "docker",
            "url": "http://localhost:6333"
        },
        "metadata_config": {
            "project": "my_project",
            "version": "1.0"
        }
    }
    ```
    
    **Process:**
    1. Loads parquet files from specified chunk results
    2. Creates vector collection with payload support
    3. Indexes documents with rich metadata
    4. Returns indexing statistics
    
    **Defaults:**
    - embedding_model: "openai_embed_3_large"
    - qdrant_config: Local docker setup (localhost:6333)
    """
    
    try:
        result = await qdrant_service.create_qdrant_index(
            session=session,
            chunk_result_ids=request.chunk_result_ids,
            collection_name=request.collection_name,
            embedding_model=request.embedding_model,
            qdrant_config=request.qdrant_config,
            metadata_config=request.metadata_config
        )
        
        return IndexResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create index: {str(e)}"
        )

@router.post("/index/search/{collection_name}", response_model=SearchResponse)
async def search_collection(
    collection_name: str,
    request: SearchRequest
):
    """
    Search in vector collection with payload support
    
    Returns:
    - Ranked search results
    - Original document content
    - Rich metadata (source files, indexing info, etc.)
    - Similarity scores
    """
    
    try:
        results = await qdrant_service.search_qdrant_collection(
            collection_name=collection_name,
            query=request.query,
            top_k=request.top_k,
            embedding_model=request.embedding_model,
            qdrant_config=request.qdrant_config,
            filters=request.filters
        )
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query,
            collection_name=collection_name
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/index/stats/{collection_name}", response_model=StatsResponse)
async def get_collection_stats(
    collection_name: str,
    embedding_model: Optional[str] = None,
    qdrant_config: Optional[Dict[str, Any]] = None
):
    """
    Get statistics for vector collection
    
    Args:
        collection_name: Name of the Qdrant collection
        embedding_model: Embedding model name (optional, uses default: openai_embed_3_large)
        qdrant_config: Custom Qdrant configuration (optional, uses default local docker setup)
    
    Returns:
        Collection metadata, document count, vector dimensions, and status information
    
    Note:
        For single-server setup, you typically only need to provide collection_name.
        The service will use default configuration (local docker at localhost:6333).
    """
    
    try:
        stats = await qdrant_service.get_collection_stats(
            collection_name=collection_name,
            embedding_model=embedding_model,
            qdrant_config=qdrant_config
        )
        
        return StatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )

@router.get("/index/health", response_model=HealthResponse)
async def index_health_check():
    """Check indexing service health"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        message="Vector indexing service is running with features: auto_dimension_detection, payload_support, uuid_id_conversion, rich_metadata, parquet_loading",
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/index/config")
async def get_current_config():
    """Get current default configuration used by the indexing service"""
    return {
        "default_embedding_model": qdrant_service.get_default_embedding_model(),
        "default_qdrant_config": qdrant_service.get_default_config(),
        "description": "These are the default values used when embedding_model or qdrant_config are not specified in requests"
    }

@router.post("/index/validate-chunks")
async def validate_chunk_results(
    chunk_result_ids: List[UUID],
    session: Session = Depends(get_session)
):
    """
    Validate chunk results before indexing
    
    Checks:
    - Chunk results exist in database
    - Chunk results have SUCCESS status
    - Parquet files exist in MinIO storage
    """
    try:
        minio_service = MinIOService()
        
        # Get chunk results from database
        chunk_results = session.exec(
            select(FileChunkResult).where(FileChunkResult.id.in_(chunk_result_ids))
        ).all()
        
        validation_results = []
        for chunk_id in chunk_result_ids:
            result_info = {"chunk_result_id": str(chunk_id)}
            
            # Check if exists in database
            chunk_result = next((cr for cr in chunk_results if cr.id == chunk_id), None)
            if not chunk_result:
                result_info.update({
                    "exists_in_db": False,
                    "status": "not_found",
                    "file_exists": False,
                    "error": "Chunk result not found in database"
                })
            else:
                result_info.update({
                    "exists_in_db": True,
                    "status": chunk_result.status.value,
                    "bucket": chunk_result.bucket,
                    "object_key": chunk_result.object_key,
                    "file_name": chunk_result.file.file_name if chunk_result.file else "Unknown",
                    "chunked_at": chunk_result.chunked_at.isoformat() if chunk_result.chunked_at else None,
                    "error_message": chunk_result.error_message
                })
                
                # Check if file exists in MinIO
                try:
                    minio_service.client.stat_object(
                        bucket_name=chunk_result.bucket,
                        object_name=chunk_result.object_key
                    )
                    result_info["file_exists"] = True
                except Exception as e:
                    result_info["file_exists"] = False
                    result_info["file_error"] = str(e)
            
            validation_results.append(result_info)
        
        # Summary
        total_count = len(chunk_result_ids)
        valid_count = sum(1 for r in validation_results 
                         if r.get("exists_in_db") and r.get("status") == "success" and r.get("file_exists"))
        
        return {
            "total_chunks": total_count,
            "valid_chunks": valid_count,
            "invalid_chunks": total_count - valid_count,
            "can_proceed_with_indexing": valid_count == total_count,
            "validation_results": validation_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )

# Example usage endpoints for documentation
@router.get("/index/examples/config", response_model=ConfigExampleResponse)
async def get_example_config():
    """Get example vector database configuration"""
    return ConfigExampleResponse(
        local_docker={
            "client_type": "docker",
            "url": "http://localhost:6333",
            "similarity_metric": "cosine",
            "store_text": True,
            "use_uuid_ids": True,
            "embedding_batch": 50,
            "ingest_batch": 64
        },
        cloud={
            "client_type": "cloud",
            "host": "your-cluster.qdrant.cloud",
            "api_key": "${QDRANT_API_KEY}",
            "similarity_metric": "cosine",
            "store_text": True,
            "use_uuid_ids": True
        }
    )

@router.get("/index/examples/request", response_model=RequestExampleResponse)
async def get_example_request():
    """Get example index request"""
    return RequestExampleResponse(
        create_index={
            # Minimal request - only required fields
            "chunk_result_ids": [
                "38a95a37-f359-43b8-bde0-bb6f7419f57d",
                "f8b2c1e4-5678-9abc-def0-123456789abc"
            ],
            "collection_name": "my_documents",
            
            # Optional fields - uses defaults if not provided
            # "embedding_model": "openai_embed_3_large",  # default
            # "qdrant_config": {  # default: local docker
            #     "client_type": "docker",
            #     "url": "http://localhost:6333"
            # },
            # "metadata_config": {  # optional custom metadata
            #     "project": "rag_system",
            #     "version": "1.0",
            #     "category": "technical_docs"
            # }
        },
        search={
            # Minimal search request
            "query": "What is machine learning?",
            "top_k": 10,
            
            # Optional fields - uses defaults if not provided
            # "embedding_model": "openai_embed_3_large",  # default
            # "qdrant_config": {},  # default: local docker
            # "filters": {  # optional metadata filters
            #     "source_file": "ml_guide.pdf",
            #     "doc_type": "chunk"
            # }
        }
    )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        message="Development API is running",
        timestamp=datetime.utcnow().isoformat()
    )
