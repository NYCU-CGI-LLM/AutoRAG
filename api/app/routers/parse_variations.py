from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import os
import shutil
import json
from datetime import datetime

from app.schemas import ParsingVariationCreate, ParsingVariation
# Import new tasks and ensure parse_data_task is also available if not already used directly
from app.tasks.data_processing_tasks import (
    parse_data_task, 
    finalize_parsing_variation_task, 
    handle_parsing_failure_task
)
# Import necessary helper functions from knowledge_bases.py
# These are for base KB paths that parsed variation paths will build upon.
from .knowledge_bases import _get_kb_dir, _get_kb_raw_data_dir, _get_kb_parsed_data_dir

router = APIRouter(
    prefix="/parse-variations/{kb_id}",
    tags=["Parse Variations"],
)

# Define the base directory for parser configuration files
# This path is relative to the `parsed_data_variations.py` file's location (routers directory)
# Adjust if your config directory is elsewhere, e.g., at the root of the API app.
PARSER_CONFIGS_BASE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "parse")
)

# --- Helper Functions for Parsed Data Variations ---

async def _get_kb_parse_variation_dir(kb_id: UUID, parse_variation_id: UUID) -> str:
    # Specific directory for a single parsing variation, under the main parsed_data directory for the KB
    return os.path.join(await _get_kb_parsed_data_dir(kb_id), str(parse_variation_id))

async def _get_kb_parse_variation_metadata_path(kb_id: UUID, parse_variation_id: UUID) -> str:
    return os.path.join(await _get_kb_parse_variation_dir(kb_id, parse_variation_id), "parse_variation_metadata.json")

async def _read_parse_variation_metadata(kb_id: UUID, parse_variation_id: UUID) -> Optional[ParsingVariation]:
    metadata_path = await _get_kb_parse_variation_metadata_path(kb_id, parse_variation_id)
    if not os.path.exists(metadata_path):
        return None
    try:
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        return ParsingVariation(**data)
    except (json.JSONDecodeError, TypeError) as e: # Add PydanticValidationError if Pydantic v2
        # Consider logging this error properly
        print(f"Error reading or parsing parse_variation_metadata.json for PV {parse_variation_id} in KB {kb_id}: {e}")
        return None

async def _write_parse_variation_metadata(metadata: ParsingVariation):
    variation_dir = await _get_kb_parse_variation_dir(metadata.kb_id, metadata.id)
    os.makedirs(variation_dir, exist_ok=True) # Ensure variation directory exists
    metadata_path = await _get_kb_parse_variation_metadata_path(metadata.kb_id, metadata.id)
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata.model_dump(mode='json'), f, indent=4)
    except Exception as e:
        # Consider logging this error properly
        print(f"Error writing parse_variation_metadata.json for PV {metadata.id} in KB {metadata.kb_id}: {e}")

# --- API Endpoints for Parsed Data Variations ---

@router.post("/", response_model=ParsingVariation, status_code=status.HTTP_202_ACCEPTED)
async def create_parse_variation(
    kb_id: UUID,
    variation_create: ParsingVariationCreate,
    background_tasks: BackgroundTasks
):
    kb_dir_check = await _get_kb_dir(kb_id) # Ensure KB itself exists
    if not os.path.isdir(kb_dir_check):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")

    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    # Check if there are files to parse, by checking if raw_data_dir contains files or if files_metadata.json has entries
    # For simplicity, checking if raw_data_dir has any files directly. A more robust check might involve _read_files_metadata from knowledge_bases.py
    if not os.path.isdir(raw_data_dir) or not any(os.path.isfile(os.path.join(raw_data_dir, f)) for f in os.listdir(raw_data_dir)):
        # If you have _read_files_metadata available and prefer to use it:
        # files_metadata = await _read_files_metadata(kb_id) # Assuming this helper can be imported or called
        # if not files_metadata:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge Base has no raw files to parse. Upload files first.")

    # Determine the parser YAML path to use
    parser_yaml_to_use = None
    if variation_create.parser_config_filename:
        candidate_path = os.path.join(PARSER_CONFIGS_BASE_DIR, variation_create.parser_config_filename)
        if not os.path.isfile(candidate_path):
            # You might want to list available configs here in the error message
            # available_configs = [f for f in os.listdir(PARSER_CONFIGS_BASE_DIR) if os.path.isfile(os.path.join(PARSER_CONFIGS_BASE_DIR, f)) and f.endswith('.yaml')]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Parser config file '{variation_create.parser_config_filename}' not found in config directory. Check available configurations."
            )
        parser_yaml_to_use = candidate_path
    else:
        # Default behavior if no config filename is provided: use a default.yaml if it exists
        default_yaml_path = os.path.join(PARSER_CONFIGS_BASE_DIR, "default.yaml")
        if not os.path.isfile(default_yaml_path):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="No parser_config_filename provided and default.yaml not found in config directory."
            )
        parser_yaml_to_use = default_yaml_path

    variation_id = uuid4()
    variation_output_dir = await _get_kb_parse_variation_dir(kb_id, variation_id)
    os.makedirs(variation_output_dir, exist_ok=True)

    # Get the metadata path to pass to callback tasks
    variation_metadata_path = await _get_kb_parse_variation_metadata_path(kb_id, variation_id)

    data_path_glob = os.path.join(raw_data_dir, "*.*") 

    variation_metadata = ParsingVariation(
        id=variation_id,
        kb_id=kb_id,
        variation_name=variation_create.variation_name if variation_create.variation_name else f"Parse-{variation_id.hex[:8]}",
        description=variation_create.description,
        # Store the filename that was used, not the full path or dict content
        parser_config_filename=variation_create.parser_config_filename if variation_create.parser_config_filename else "default.yaml",
        status="pending",
        output_dir=variation_output_dir 
    )
    await _write_parse_variation_metadata(variation_metadata)

    # Use apply_async to link tasks
    task_signature = parse_data_task.s(
        project_id=str(kb_id), 
        data_path_glob=data_path_glob,
        target_variation_output_dir=variation_output_dir,
        parser_yaml_path=parser_yaml_to_use,
        all_files=True
    ).set(
        link=finalize_parsing_variation_task.s(variation_metadata_path_str=str(variation_metadata_path)),
        link_error=handle_parsing_failure_task.s(variation_metadata_path_str=str(variation_metadata_path))
    )
    
    task_result = task_signature.apply_async()

    # Update metadata with celery_task_id and status="processing"
    variation_metadata.celery_task_id = task_result.id
    variation_metadata.status = "processing"
    variation_metadata.updated_at = datetime.utcnow()
    await _write_parse_variation_metadata(variation_metadata)

    return variation_metadata

@router.get("/", response_model=List[ParsingVariation])
async def list_parse_variations(kb_id: UUID):
    kb_parsed_data_dir = await _get_kb_parsed_data_dir(kb_id) # Base dir for all parse variations of this KB
    if not os.path.isdir(kb_parsed_data_dir):
        kb_dir_check = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_dir_check):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        return []

    variations = []
    for item_name in os.listdir(kb_parsed_data_dir):
        try:
            variation_uuid = UUID(item_name) # Check if dir name is a UUID
            variation_specific_dir = os.path.join(kb_parsed_data_dir, item_name)
            if os.path.isdir(variation_specific_dir):
                metadata = await _read_parse_variation_metadata(kb_id, variation_uuid)
                if metadata:
                    variations.append(metadata)
        except ValueError: 
            pass 
    return variations

@router.get("/{parse_variation_id}", response_model=ParsingVariation)
async def get_parse_variation(kb_id: UUID, parse_variation_id: UUID):
    metadata = await _read_parse_variation_metadata(kb_id, parse_variation_id)
    if not metadata:
        # Check if KB or specific variation dir exists for more accurate error
        variation_dir = await _get_kb_parse_variation_dir(kb_id, parse_variation_id)
        if not os.path.isdir(variation_dir): # Implies KB might exist but not this specific variation
             kb_dir_check = await _get_kb_dir(kb_id)
             if not os.path.isdir(kb_dir_check):
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parsing variation with ID {parse_variation_id} not found.")
        # Directory exists but metadata is missing
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata for parsing variation {parse_variation_id} not found, but its directory exists.")
    return metadata

@router.delete("/{parse_variation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parse_variation(kb_id: UUID, parse_variation_id: UUID):
    variation_dir = await _get_kb_parse_variation_dir(kb_id, parse_variation_id)
    if not os.path.isdir(variation_dir):
        kb_dir_check = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_dir_check):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parsing variation with ID {parse_variation_id} not found.")
    
    try:
        shutil.rmtree(variation_dir)
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete parsing variation directory: {e}")
    return
 