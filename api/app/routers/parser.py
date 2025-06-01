from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session

from app.core.database import get_session
from app.services.parser_service import ParserService
from app.schemas.parser import ParserResponse, ParserListResponse, ParserDetailResponse

router = APIRouter(
    prefix="/parser",
    tags=["Parser"],
)

parser_service = ParserService()


@router.get("/", response_model=ParserListResponse)
async def list_parsers(
    session: Session = Depends(get_session),
    status: Optional[str] = None,
    module_type: Optional[str] = None,
    limit: int = 50
):
    """
    List all available parsers.
    
    Returns a list of parser configurations with filtering options.
    
    **Parameters:**
    - `status`: Filter by parser status (active/draft/deprecated)
    - `module_type`: Filter by module type (langchain, llama_parse, etc.)
    - `limit`: Maximum number of results to return
    """
    try:
        if status:
            # Filter by status if provided
            parsers = parser_service.get_parsers_by_status(session, status, limit)
        else:
            parsers = parser_service.get_active_parsers(session)[:limit]
        
        parser_responses = [
            ParserResponse(
                id=parser.id,
                name=parser.name,
                module_type=parser.module_type,
                supported_mime=parser.supported_mime,
                params=parser.params,
                status=parser.status.value
            )
            for parser in parsers
        ]
        
        return ParserListResponse(
            total=len(parser_responses),
            parsers=parser_responses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list parsers: {str(e)}")


@router.get("/{parser_id}", response_model=ParserDetailResponse)
async def get_parser(
    parser_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed information about a specific parser.
    
    Returns comprehensive parser information including configuration,
    supported file types, and usage statistics.
    """
    try:
        parser = parser_service.get_parser_by_id(session, parser_id)
        if not parser:
            raise HTTPException(status_code=404, detail="Parser not found")
        
        # Get usage statistics
        usage_stats = parser_service.get_parser_usage_stats(session, parser_id)
        
        return ParserDetailResponse(
            id=parser.id,
            name=parser.name,
            module_type=parser.module_type,
            supported_mime=parser.supported_mime,
            params=parser.params,
            status=parser.status.value,
            usage_stats=usage_stats,
            description=f"Parser for {', '.join(parser.supported_mime)} files using {parser.module_type}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get parser: {str(e)}")


@router.get("/{parser_id}/compatible-files")
async def get_compatible_files(
    parser_id: UUID,
    library_id: Optional[UUID] = None,
    session: Session = Depends(get_session)
):
    """
    Get files that are compatible with this parser.
    
    Returns a list of files that can be processed by the specified parser
    based on MIME type compatibility.
    """
    try:
        parser = parser_service.get_parser_by_id(session, parser_id)
        if not parser:
            raise HTTPException(status_code=404, detail="Parser not found")
        
        compatible_files = parser_service.get_compatible_files(
            session, parser_id, library_id
        )
        
        return {
            "parser_id": str(parser_id),
            "parser_name": parser.name,
            "supported_mime_types": parser.supported_mime,
            "compatible_files": [
                {
                    "file_id": str(file.id),
                    "file_name": file.file_name,
                    "mime_type": file.mime_type,
                    "library_id": str(file.library_id)
                }
                for file in compatible_files
            ],
            "total_compatible": len(compatible_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compatible files: {str(e)}") 