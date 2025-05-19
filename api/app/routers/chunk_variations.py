from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from uuid import UUID, uuid4
import os
import shutil
import json
from datetime import datetime

from app.schemas.chunking_variation import ChunkingVariationCreate, ChunkingVariation
from app.schemas.parsing_variation import ParsingVariation # To read parsing variation metadata
from app.tasks.data_processing_tasks import (
    chunk_data_variation_task,
    finalize_chunking_variation_task,
    handle_chunking_failure_task,
    _DEFAULT_CHUNKER_YAML_PATH # For default YAML path
)
# Assuming parsing variation helpers can be reused or adapted for path context
from .parse_variations import (
    _get_kb_parse_variation_dir,
    _read_parse_variation_metadata
)
from .knowledge_bases import _get_kb_dir # For top-level KB check

router = APIRouter(
    prefix="/knowledge-bases/{kb_id}/parse-variations/{parse_variation_id}/chunk-variations",
    tags=["Chunk Variations"]
)

# Define the base directory for chunker configuration files
# This path is relative to the current file's location (routers directory)
CHUNKER_CONFIGS_BASE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "chunk")
)

# --- Helper Functions for Chunking Variations ---

async def _get_parse_var_chunk_variations_base_dir(kb_id: UUID, parse_variation_id: UUID) -> str:
    """Base directory to store all chunking variations."""
    kb_dir = await _get_kb_dir(kb_id)
    return os.path.join(kb_dir, "chunked_data")

async def _get_chunk_variation_dir(kb_id: UUID, parse_variation_id: UUID, chunk_variation_id: UUID) -> str:
    """Specific directory for a single chunking variation."""
    base_chunk_vars_dir = await _get_parse_var_chunk_variations_base_dir(kb_id, parse_variation_id)
    return os.path.join(base_chunk_vars_dir, str(chunk_variation_id))

async def _get_chunk_variation_metadata_path(kb_id: UUID, parse_variation_id: UUID, chunk_variation_id: UUID) -> str:
    chunk_var_dir = await _get_chunk_variation_dir(kb_id, parse_variation_id, chunk_variation_id)
    return os.path.join(chunk_var_dir, "chunk_variation_metadata.json")

async def _read_chunk_variation_metadata(kb_id: UUID, parse_variation_id: UUID, chunk_variation_id: UUID) -> Optional[ChunkingVariation]:
    metadata_path = await _get_chunk_variation_metadata_path(kb_id, parse_variation_id, chunk_variation_id)
    if not os.path.exists(metadata_path):
        return None
    try:
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        return ChunkingVariation(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error reading or parsing chunk_variation_metadata.json for CV {chunk_variation_id} in PV {parse_variation_id} KB {kb_id}: {e}")
        return None

async def _write_chunk_variation_metadata(metadata: ChunkingVariation):
    variation_dir = await _get_chunk_variation_dir(metadata.kb_id, metadata.parse_variation_id, metadata.id)
    os.makedirs(variation_dir, exist_ok=True)
    metadata_path = await _get_chunk_variation_metadata_path(metadata.kb_id, metadata.parse_variation_id, metadata.id)
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata.model_dump(mode='json'), f, indent=4)
    except Exception as e:
        print(f"Error writing chunk_variation_metadata.json for CV {metadata.id} in PV {metadata.parse_variation_id} KB {metadata.kb_id}: {e}")

# --- API Endpoints for Chunking Variations ---

@router.post(
    "/",
    response_model=ChunkingVariation,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_chunk_variation(
    kb_id: UUID,
    parse_variation_id: UUID,
    variation_create: ChunkingVariationCreate,
):
    # Validate Knowledge Base existence
    kb_dir_check = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_dir_check):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")

    # Validate Parsing Variation existence and get its output path
    parse_variation_metadata = await _read_parse_variation_metadata(kb_id, parse_variation_id)
    if not parse_variation_metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parsing variation with ID {parse_variation_id} not found.")
    if parse_variation_metadata.status != "completed" or not parse_variation_metadata.parsed_file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parsing variation {parse_variation_id} is not completed or has no output file.")
    
    parsed_file_to_chunk = parse_variation_metadata.parsed_file_path
    if not os.path.isfile(parsed_file_to_chunk):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Parsed file {parsed_file_to_chunk} for variation {parse_variation_id} not found on disk.")

    # Determine the chunker YAML path
    chunker_yaml_to_use = None
    config_filename_to_store = "default_chunk.yaml" # Default if none provided
    if variation_create.chunker_config_filename:
        candidate_path = os.path.join(CHUNKER_CONFIGS_BASE_DIR, variation_create.chunker_config_filename)
        if not os.path.isfile(candidate_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Chunker config file '{variation_create.chunker_config_filename}' not found in {CHUNKER_CONFIGS_BASE_DIR}."
            )
        chunker_yaml_to_use = candidate_path
        config_filename_to_store = variation_create.chunker_config_filename
    else:
        default_yaml_path = os.path.join(CHUNKER_CONFIGS_BASE_DIR, "default_chunk.yaml")
        if not os.path.isfile(default_yaml_path):
            # Fallback to system default if no default_chunk.yaml in config dir
            logger.warning(f"default_chunk.yaml not found in {CHUNKER_CONFIGS_BASE_DIR}, attempting to use system default _DEFAULT_CHUNKER_YAML_PATH")
            if not os.path.isfile(_DEFAULT_CHUNKER_YAML_PATH):
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No chunker_config_filename provided and no default_chunk.yaml or system default chunker YAML found.")
            chunker_yaml_to_use = _DEFAULT_CHUNKER_YAML_PATH
            # config_filename_to_store will remain "default_chunk.yaml" indicating an attempt to use it, 
            # or you could store the actual path or a special value if system default is used.
            # For simplicity, if user doesn't provide, we imply they wanted the default from the config dir.
        else:
            chunker_yaml_to_use = default_yaml_path

    chunk_variation_id = uuid4()
    chunk_variation_output_dir = await _get_chunk_variation_dir(kb_id, parse_variation_id, chunk_variation_id)
    os.makedirs(chunk_variation_output_dir, exist_ok=True)

    chunk_metadata_path = await _get_chunk_variation_metadata_path(kb_id, parse_variation_id, chunk_variation_id)

    chunk_variation_metadata = ChunkingVariation(
        id=chunk_variation_id,
        kb_id=kb_id,
        parse_variation_id=parse_variation_id,
        variation_name=variation_create.variation_name if variation_create.variation_name else f"Chunk-{chunk_variation_id.hex[:8]}",
        description=variation_create.description,
        chunker_config_filename=config_filename_to_store,
        status="pending",
        output_dir=chunk_variation_output_dir 
    )
    await _write_chunk_variation_metadata(chunk_variation_metadata)

    task_signature = chunk_data_variation_task.s(
        kb_id=str(kb_id),
        parsed_file_path=parsed_file_to_chunk,
        target_chunk_variation_output_dir=chunk_variation_output_dir,
        chunker_yaml_path=chunker_yaml_to_use
    ).set(
        link=finalize_chunking_variation_task.s(chunk_variation_metadata_path_str=str(chunk_metadata_path)),
        link_error=handle_chunking_failure_task.s(chunk_variation_metadata_path_str=str(chunk_metadata_path))
    )
    task_result = task_signature.apply_async()

    chunk_variation_metadata.celery_task_id = task_result.id
    chunk_variation_metadata.status = "processing"
    chunk_variation_metadata.updated_at = datetime.utcnow()
    await _write_chunk_variation_metadata(chunk_variation_metadata)

    return chunk_variation_metadata

@router.get(
    "/",
    response_model=List[ChunkingVariation],
)
async def list_chunk_variations(kb_id: UUID, parse_variation_id: UUID):
    # Ensure parse variation exists
    parse_var_dir = await _get_kb_parse_variation_dir(kb_id, parse_variation_id)
    if not os.path.isdir(parse_var_dir):
        # Further check if KB itself exists for a more accurate error
        kb_dir_check = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_dir_check):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsing variation not found, so cannot list its chunking variations.")

    chunk_vars_base_dir = await _get_parse_var_chunk_variations_base_dir(kb_id, parse_variation_id)
    if not os.path.isdir(chunk_vars_base_dir):
        return [] # No chunking variations created yet for this KB

    variations = []
    for item_name in os.listdir(chunk_vars_base_dir):
        try:
            variation_uuid = UUID(item_name)
            metadata = await _read_chunk_variation_metadata(kb_id, parse_variation_id, variation_uuid)
            if metadata and metadata.parse_variation_id == parse_variation_id:
                variations.append(metadata)
        except ValueError:
            pass # Not a UUID named directory
    return variations

@router.get(
    "/{chunk_variation_id}",
    response_model=ChunkingVariation,
)
async def get_chunk_variation(kb_id: UUID, parse_variation_id: UUID, chunk_variation_id: UUID):
    metadata = await _read_chunk_variation_metadata(kb_id, parse_variation_id, chunk_variation_id)
    if not metadata:
        # Check if parent dirs exist for better error messages
        chunk_var_dir = await _get_chunk_variation_dir(kb_id, parse_variation_id, chunk_variation_id)
        if not os.path.isdir(chunk_var_dir):
            parse_var_dir = await _get_kb_parse_variation_dir(kb_id, parse_variation_id)
            if not os.path.isdir(parse_var_dir):
                kb_dir_check = await _get_kb_dir(kb_id)
                if not os.path.isdir(kb_dir_check):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsing variation not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chunking variation with ID {chunk_variation_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata for chunking variation {chunk_variation_id} not found, but its directory exists.")
    if metadata.parse_variation_id != parse_variation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chunking variation {chunk_variation_id} does not belong to parsing variation {parse_variation_id}.")
    return metadata

@router.delete(
    "/{chunk_variation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chunk_variation(kb_id: UUID, parse_variation_id: UUID, chunk_variation_id: UUID):
    variation_dir = await _get_chunk_variation_dir(kb_id, parse_variation_id, chunk_variation_id)
    if not os.path.isdir(variation_dir):
        # Add checks for parent existence like in GET to provide better context
        parse_var_dir = await _get_kb_parse_variation_dir(kb_id, parse_variation_id)
        if not os.path.isdir(parse_var_dir):
            kb_dir_check = await _get_kb_dir(kb_id)
            if not os.path.isdir(kb_dir_check):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parsing variation not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chunking variation with ID {chunk_variation_id} not found.")
    metadata = await _read_chunk_variation_metadata(kb_id, parse_variation_id, chunk_variation_id)
    if not metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata for chunking variation {chunk_variation_id} not found.")
    if metadata.parse_variation_id != parse_variation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chunking variation {chunk_variation_id} does not belong to parsing variation {parse_variation_id}.")
    try:
        shutil.rmtree(variation_dir)
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete chunking variation directory: {e}")
    return

# Need to import logger for the warning in create_chunk_variation
import logging
logger = logging.getLogger(__name__) 