from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID
import os
import shutil # For file operations
import json # Added for saving metadata

from app.schemas import (
    KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseDetail, FileInfo #, VariationSummary # Commented out
)

router = APIRouter(
    prefix="/knowledge-bases",
    tags=["Knowledge Bases"],
)

# --- Configuration ---
# This would typically come from a config file or environment variables
BASE_KB_DIR = "./data/kbs" # Base directory to store all knowledge bases

# Ensure base directory exists
os.makedirs(BASE_KB_DIR, exist_ok=True)

# --- Helper Functions (Placeholder) ---
async def _get_kb_dir(kb_id: UUID) -> str:
    return os.path.join(BASE_KB_DIR, str(kb_id))

async def _get_kb_raw_data_dir(kb_id: UUID) -> str:
    return os.path.join(await _get_kb_dir(kb_id), "raw_data")

async def _get_kb_variations_dir(kb_id: UUID) -> str:
    return os.path.join(await _get_kb_dir(kb_id), "variations")

async def _get_kb_metadata_path(kb_id: UUID) -> str:
    return os.path.join(await _get_kb_dir(kb_id), "metadata.json")

async def _get_kb_files_metadata_path(kb_id: UUID) -> str:
    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    return os.path.join(raw_data_dir, "files_metadata.json")

async def _read_files_metadata(kb_id: UUID) -> List[FileInfo]:
    metadata_path = await _get_kb_files_metadata_path(kb_id)
    if not os.path.exists(metadata_path):
        return []
    try:
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        return [FileInfo(**item) for item in data] # Validate with model
    except (json.JSONDecodeError, TypeError) as e: # TypeError for Pydantic validation issues
        print(f"Error reading or parsing files_metadata.json for KB {kb_id}: {e}") # Replace with logging
        return [] # Or raise an error

async def _write_files_metadata(kb_id: UUID, files_info: List[FileInfo]):
    metadata_path = await _get_kb_files_metadata_path(kb_id)
    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    os.makedirs(raw_data_dir, exist_ok=True) # Ensure raw_data_dir exists
    try:
        with open(metadata_path, 'w') as f:
            # Use model_dump to ensure datetime is serialized correctly if not using mode='json' everywhere
            json.dump([item.model_dump(mode='json') for item in files_info], f, indent=4)
    except Exception as e:
        print(f"Error writing files_metadata.json for KB {kb_id}: {e}") # Replace with logging
        # Consider how to handle write failures (e.g., backup, retry, raise)

# --- Endpoints ---

@router.post("/", response_model=KnowledgeBase, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(kb_create: KnowledgeBaseCreate):
    """Create a new knowledge base."""
    new_kb = KnowledgeBase(**kb_create.model_dump())
    kb_dir = await _get_kb_dir(new_kb.id)
    raw_data_dir = await _get_kb_raw_data_dir(new_kb.id)
    variations_dir = await _get_kb_variations_dir(new_kb.id)
    metadata_path = await _get_kb_metadata_path(new_kb.id)

    try:
        os.makedirs(kb_dir, exist_ok=False)
        os.makedirs(raw_data_dir, exist_ok=True)
        os.makedirs(variations_dir, exist_ok=True)
        # Persist KB metadata
        with open(metadata_path, 'w') as f:
            json.dump(new_kb.model_dump(mode='json'), f, indent=4) # Use mode='json' for datetime to str
    except FileExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Knowledge Base with ID {new_kb.id} might already exist or collision.")
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create directories: {e}")
    return new_kb

@router.get("/", response_model=List[KnowledgeBase])
async def list_knowledge_bases():
    """List all available knowledge bases."""
    kbs = []
    if not os.path.exists(BASE_KB_DIR):
        return []
        
    for item_name in os.listdir(BASE_KB_DIR):
        item_path = os.path.join(BASE_KB_DIR, item_name)
        if os.path.isdir(item_path):
            try:
                kb_id = UUID(item_name)
                metadata_path = await _get_kb_metadata_path(kb_id)
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        data = json.load(f)
                    kbs.append(KnowledgeBase(**data))
                else:
                    # Fallback if metadata.json is missing (should ideally not happen for KBs created via API)
                    # Or log a warning/error
                    print(f"Warning: metadata.json not found for KB ID {kb_id}")
                    # kbs.append(KnowledgeBase(id=kb_id, name=item_name, description="Metadata missing"))
            except json.JSONDecodeError:
                print(f"Warning: Error decoding metadata.json for KB ID {item_name}")
                pass
            except ValueError:
                # Not a valid UUID named directory, skip
                pass 
    return kbs

@router.get("/{kb_id}", response_model=KnowledgeBaseDetail)
async def get_knowledge_base(kb_id: UUID):
    """Get detailed information about a specific knowledge base."""
    kb_dir = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
    
    metadata_path = await _get_kb_metadata_path(kb_id)
    if not os.path.exists(metadata_path):
        # This case implies an orphaned directory or an error during creation
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base metadata not found.")

    try:
        with open(metadata_path, 'r') as f:
            kb_data_dict = json.load(f)
        kb_data = KnowledgeBase(**kb_data_dict) # Validate with the model
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error decoding knowledge base metadata.")
    except Exception as e: # Catch any other Pydantic validation errors etc.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing knowledge base metadata: {e}")
    
    raw_file_count = 0
    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    if os.path.exists(raw_data_dir):
        raw_file_count = len([name for name in os.listdir(raw_data_dir) if os.path.isfile(os.path.join(raw_data_dir, name))])

    # TODO: Fetch actual variation summaries
    # variation_summaries = [] 

    return KnowledgeBaseDetail(
        **kb_data.model_dump(),
        raw_file_count=raw_file_count,
        # variation_summaries=variation_summaries # Add when VariationSummary is complete
    )

@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(kb_id: UUID):
    """Delete an entire knowledge base."""
    kb_dir = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
    
    try:
        shutil.rmtree(kb_dir)
        # TODO: Delete KB metadata from persisted store
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete knowledge base: {e}")
    return

@router.post("/{kb_id}/files", response_model=List[FileInfo])
async def upload_knowledge_base_files(kb_id: UUID, files: List[UploadFile] = File(...)):
    """Upload one or more raw data files to a knowledge base."""
    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    if not os.path.isdir(raw_data_dir):
        kb_dir = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_dir):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        os.makedirs(raw_data_dir, exist_ok=True)

    current_files_metadata = await _read_files_metadata(kb_id)
    # Create a lookup for existing files to handle overwrites or updates if necessary
    existing_files_map = {fi.name: fi for fi in current_files_metadata}

    newly_uploaded_files_info: List[FileInfo] = []

    for file in files:
        file_location = os.path.join(raw_data_dir, file.filename)
        try:
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            
            # Create FileInfo object. If file already in metadata, update it; otherwise, add.
            # For simplicity, this example overwrites if name matches. Consider versioning or unique naming if needed.
            file_info = FileInfo(name=file.filename, size=file.size, type=file.content_type)
            existing_files_map[file.filename] = file_info # Add or update in map
            newly_uploaded_files_info.append(file_info) # Track what was processed in this batch

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload {file.filename}: {e}")
        finally:
            file.file.close()
            
    # Update the full list of metadata
    updated_metadata_list = list(existing_files_map.values())
    await _write_files_metadata(kb_id, updated_metadata_list)
    
    return newly_uploaded_files_info # Return info only for files processed in this request

@router.get("/{kb_id}/files", response_model=List[FileInfo])
async def list_knowledge_base_files(kb_id: UUID):
    """List all raw files within a specific knowledge base."""
    # Ensure KB exists and raw_data directory is there or can be accessed
    raw_data_dir = await _get_kb_raw_data_dir(kb_id)
    if not os.path.isdir(raw_data_dir):
        # Check if the main KB directory exists. If not, KB itself is not found.
        kb_dir = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_dir):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        # KB exists, but no raw_data dir might mean no files yet, so return empty list.
        return [] 

    files_info = await _read_files_metadata(kb_id)
    # Optional: You could add a step here to reconcile with actual files on disk
    # e.g., remove metadata for files that no longer exist, or add metadata for untracked files (though this is less common for API-managed uploads)
    return files_info

@router.delete("/{kb_id}/files/{file_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base_file(kb_id: UUID, file_name: str):
    """Delete a specific raw file from a knowledge base."""
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file name.")

    file_path = os.path.join(await _get_kb_raw_data_dir(kb_id), file_name)

    if not os.path.isfile(file_path):
        # Even if file not on disk, check if it's in metadata and remove it
        # This handles cases where file was deleted manually but metadata remained
        pass # Continue to metadata cleanup
    else:
        try:
            os.remove(file_path)
        except OSError as e:
            # If physical delete fails, we might still want to try cleaning metadata or just raise
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete physical file: {e}")

    # Update metadata
    current_files_metadata = await _read_files_metadata(kb_id)
    updated_metadata = [fi for fi in current_files_metadata if fi.name != file_name]

    if len(updated_metadata) == len(current_files_metadata) and not os.path.exists(file_path):
        # File wasn't in metadata and also not on disk (already deleted or never existed properly)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_name}' not found.")
    
    await _write_files_metadata(kb_id, updated_metadata)
    return 