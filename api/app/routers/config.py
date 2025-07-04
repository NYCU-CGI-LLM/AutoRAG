from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session

from app.core.database import get_session
from app.services.config_service import ConfigService
from app.models.config import ConfigStatus
from app.schemas.config import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigDetailResponse,
    ConfigListResponse,
    ConfigSummary
)

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)

config_service = ConfigService()


@router.post("/", response_model=ConfigResponse, status_code=201)
async def create_config(
    request: ConfigCreate,
    session: Session = Depends(get_session)
):
    """
    Create a new configuration.
    
    Creates a new configuration that combines a parser, chunker, and indexer.
    This configuration can then be reused by multiple retrievers.
    
    **Parameters:**
    - `parser_id`: ID of the parser to use
    - `chunker_id`: ID of the chunker to use  
    - `indexer_id`: ID of the indexer to use
    - `name`: Optional name for the configuration
    - `description`: Optional description
    - `params`: Optional additional parameters
    """
    try:
        config = config_service.create_config(
            session=session,
            parser_id=request.parser_id,
            chunker_id=request.chunker_id,
            indexer_id=request.indexer_id,
            name=request.name,
            description=request.description,
            params=request.params
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create config: {str(e)}")


@router.get("/", response_model=ConfigListResponse)
async def list_configs(
    status: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """
    List all configurations with optional filtering.
    
    Args:
        status: Filter by status (active, draft, deprecated)
        limit: Maximum number of results to return
    """
    try:
        config_status = None
        if status:
            try:
                config_status = ConfigStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        configs = config_service.list_configs(
            session=session,
            status=config_status,
            limit=limit
        )
        
        return ConfigListResponse(
            total=len(configs),
            configs=configs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list configs: {str(e)}")


@router.get("/summaries", response_model=List[ConfigSummary])
async def get_config_summaries(session: Session = Depends(get_session)):
    """
    Get configuration summaries with component names and usage statistics.
    
    Returns a simplified view of all active configurations including
    component names and retriever usage counts.
    """
    try:
        summaries = config_service.get_config_summaries(session)
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config summaries: {str(e)}")


@router.get("/{config_id}", response_model=ConfigDetailResponse)
async def get_config(
    config_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Get detailed configuration information.
    
    Returns detailed information about a configuration including
    component details and usage statistics.
    """
    try:
        config_detail = config_service.get_config_detail(session, config_id)
        return config_detail
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config details: {str(e)}")


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config(
    config_id: UUID,
    request: ConfigUpdate,
    session: Session = Depends(get_session)
):
    """
    Update configuration metadata.
    
    Note: Component references (parser_id, chunker_id, indexer_id) cannot be changed
    after creation. Only name, description, params, and status can be updated.
    """
    try:
        status = None
        if request.status:
            try:
                status = ConfigStatus(request.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        
        config = config_service.update_config(
            session=session,
            config_id=config_id,
            name=request.name,
            description=request.description,
            params=request.params,
            status=status
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.delete("/{config_id}")
async def delete_config(
    config_id: UUID,
    session: Session = Depends(get_session)
):
    """
    Delete a configuration.
    
    If the configuration is being used by any retrievers, it will be marked as deprecated.
    If not in use, it will be permanently deleted.
    """
    try:
        success = config_service.delete_config(session, config_id)
        if not success:
            raise HTTPException(status_code=404, detail="Config not found")
        
        return {"message": "Config deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {str(e)}")


@router.post("/find-or-create", response_model=ConfigResponse)
async def find_or_create_config(
    request: ConfigCreate,
    session: Session = Depends(get_session)
):
    """
    Find existing configuration or create new one.
    
    Searches for an existing active configuration with the same component combination.
    If found, returns the existing configuration. Otherwise, creates a new one.
    """
    try:
        config = config_service.get_or_create_config(
            session=session,
            parser_id=request.parser_id,
            chunker_id=request.chunker_id,
            indexer_id=request.indexer_id,
            name=request.name,
            description=request.description,
            params=request.params
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get or create config: {str(e)}") 