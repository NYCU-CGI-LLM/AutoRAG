from fastapi import APIRouter, HTTPException, status
from uuid import UUID, uuid4
import os
import shutil
import json
from app.schemas.indexing_variation import (
    IndexingVariationCreate,
    IndexingVariation
)
from .knowledge_bases import _get_kb_dir
from .parse_variations import _get_kb_parse_variation_dir
from .chunk_variations import _get_chunk_variation_dir

router = APIRouter(
    prefix="/index-variations/{kb_id}/{parse_id}/{chunk_id}",
    tags=["Indexing Variations"]
)

async def _get_index_variations_base_dir(
    kb_id: UUID, parse_id: UUID, chunk_id: UUID
) -> str:
    # Base directory under a specific chunk variation
    chunk_dir = await _get_chunk_variation_dir(kb_id, parse_id, chunk_id)
    return chunk_dir

async def _get_index_variation_dir(
    kb_id: UUID, parse_id: UUID, chunk_id: UUID, index_id: UUID
) -> str:
    base = await _get_index_variations_base_dir(kb_id, parse_id, chunk_id)
    return os.path.join(base, str(index_id))

async def _get_index_variation_metadata_path(
    kb_id: UUID, parse_id: UUID, chunk_id: UUID, index_id: UUID
) -> str:
    iv_dir = await _get_index_variation_dir(kb_id, parse_id, chunk_id, index_id)
    return os.path.join(iv_dir, "index_variation_metadata.json")

@router.post("/", response_model=IndexingVariation, status_code=status.HTTP_202_ACCEPTED)
async def create_index_variation(
    kb_id: UUID,
    parse_id: UUID,
    chunk_id: UUID,
    variation_create: IndexingVariationCreate
):
    # Validate KB, parse and chunk variation directories exist
    kb_dir_path = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_dir_path):
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    parse_dir = await _get_kb_parse_variation_dir(kb_id, parse_id)
    if not os.path.isdir(parse_dir):
        raise HTTPException(status_code=404, detail="Parsing variation not found")
    chunk_dir_path = await _get_chunk_variation_dir(kb_id, parse_id, chunk_id)
    if not os.path.isdir(chunk_dir_path):
        raise HTTPException(status_code=404, detail="Chunking variation not found")
    # Create index variation directory
    iv_id = uuid4()
    iv_dir = await _get_index_variation_dir(kb_id, parse_id, chunk_id, iv_id)
    os.makedirs(iv_dir, exist_ok=True)
    # Copy first parquet file (0.parquet) to project data folder for ingestion
    src_parquet = os.path.join(chunk_dir_path, "0.parquet")
    if not os.path.isfile(src_parquet):
        raise HTTPException(status_code=400, detail="Chunk parquet file 0.parquet not found")
    data_dir = os.path.join(kb_dir_path, "data")
    os.makedirs(data_dir, exist_ok=True)
    dst_parquet = os.path.join(data_dir, "corpus.parquet")
    shutil.copyfile(src_parquet, dst_parquet)
    # Build metadata
    metadata = IndexingVariation(
        id=iv_id,
        kb_id=kb_id,
        parse_variation_id=parse_id,
        chunk_variation_id=chunk_id,
        variation_name=variation_create.variation_name,
        description=variation_create.description,
        index_config_filename=variation_create.index_config_filename,
        status="created",
        output_dir=iv_dir,
        indexed_file_path=dst_parquet,
    )
    # Persist metadata
    meta_path = await _get_index_variation_metadata_path(kb_id, parse_id, chunk_id, iv_id)
    with open(meta_path, 'w') as f:
        json.dump(metadata.model_dump(mode='json'), f, indent=4)
    return metadata

@router.get("/", response_model=list[IndexingVariation])
async def list_index_variations(
    kb_id: UUID,
    parse_id: UUID,
    chunk_id: UUID
):
    base = await _get_index_variations_base_dir(kb_id, parse_id, chunk_id)
    if not os.path.isdir(base):
        return []
    variations = []
    for name in os.listdir(base):
        iv_dir = os.path.join(base, name)
        if os.path.isdir(iv_dir):
            meta_path = os.path.join(iv_dir, "index_variation_metadata.json")
            if os.path.isfile(meta_path):
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                variations.append(IndexingVariation(**data))
    return variations

@router.get("/{index_id}", response_model=IndexingVariation)
async def get_index_variation(
    kb_id: UUID,
    parse_id: UUID,
    chunk_id: UUID,
    index_id: UUID
):
    meta_path = await _get_index_variation_metadata_path(kb_id, parse_id, chunk_id, index_id)
    if not os.path.isfile(meta_path):
        raise HTTPException(status_code=404, detail="Indexing variation not found")
    with open(meta_path, 'r') as f:
        data = json.load(f)
    return IndexingVariation(**data)

@router.delete("/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index_variation(
    kb_id: UUID,
    parse_id: UUID,
    chunk_id: UUID,
    index_id: UUID
):
    iv_dir = await _get_index_variation_dir(kb_id, parse_id, chunk_id, index_id)
    if os.path.isdir(iv_dir):
        shutil.rmtree(iv_dir)
    return 