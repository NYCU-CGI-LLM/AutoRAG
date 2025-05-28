"""
Development API endpoints for testing parser and chunker functionality
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.database import get_session 
from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])

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
    result_id: int,
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
                "id": result.id,
                "file_id": str(result.file_id),
                "file_parse_result_id": result.file_parse_result_id,
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
    result_id: int,
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


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        message="Development API is running",
        timestamp=datetime.utcnow().isoformat()
    )
