from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List
from uuid import UUID, uuid4
import os
import shutil
import json # For saving metadata
import yaml # For saving vectordb.yaml
import asyncio # Added for asyncio.sleep in background task
from pathlib import Path
import pandas as pd

from app.schemas import (
    Variation, VariationCreate, VariationSummary, TaskStatus,
    BM25Options, EmbeddingOptions, IndexerConfigBase, TaskStatusEnum
)
# Assuming knowledge_bases.py contains these helpers or similar logic
from .knowledge_bases import _get_kb_dir, _get_kb_raw_data_dir, _get_kb_variations_dir 

# autorag imports
from autorag.parser import Parser as AutoRAGParser
from autorag.chunker import Chunker as AutoRAGChunker
from autorag.nodes.retrieval.bm25 import bm25_ingest
from autorag.nodes.retrieval.vectordb import vectordb_ingest
from autorag.vectordb import load_vectordb_from_yaml # Added for loading vectordb instance
from pydantic import BaseModel # Added for type hint in run_indexing_pipeline

router = APIRouter(
    prefix="/knowledge-bases/{kb_id}/variations",
    tags=["Knowledge Base Variations"],
)

# --- Helper Functions (Placeholder) ---
async def _get_variation_dir(kb_id: UUID, variation_id: UUID) -> str:
    return os.path.join(await _get_kb_variations_dir(kb_id), str(variation_id))

async def _get_variation_config_dir(kb_id: UUID, variation_id: UUID) -> str:
    return os.path.join(await _get_variation_dir(kb_id, variation_id), "config")

async def _get_variation_processed_data_dir(kb_id: UUID, variation_id: UUID) -> str:
    return os.path.join(await _get_variation_dir(kb_id, variation_id), "processed_data")

async def _get_variation_index_dir(kb_id: UUID, variation_id: UUID) -> str:
    return os.path.join(await _get_variation_dir(kb_id, variation_id), "index")

async def _get_variation_metadata_path(kb_id: UUID, variation_id: UUID) -> str:
    return os.path.join(await _get_variation_dir(kb_id, variation_id), "variation_metadata.json")

async def _save_variation_metadata(kb_id: UUID, variation: Variation):
    metadata_path = await _get_variation_metadata_path(kb_id, variation.id)
    with open(metadata_path, 'w') as f:
        json.dump(variation.model_dump(mode='json'), f, indent=4)

async def _load_variation_metadata(kb_id: UUID, variation_id: UUID) -> Variation:
    metadata_path = await _get_variation_metadata_path(kb_id, variation_id)
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variation metadata not found")
    with open(metadata_path, 'r') as f:
        data = json.load(f)
    return Variation(**data)

async def _update_variation_status(kb_id: UUID, variation_id: UUID, new_status: TaskStatusEnum, error_message: str = None):
    metadata_path = await _get_variation_metadata_path(kb_id, variation_id)
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r+') as f:
            data = json.load(f)
            data['status'] = new_status.value
            if error_message:
                data['error_message'] = error_message
            else:
                data.pop('error_message', None)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
    else:
        # This case should ideally not happen if metadata is created first
        # Consider logging this error appropriately
        print(f"Error: Metadata file not found for variation {variation_id} to update status to {new_status.value}")

# --- Background Task for Indexing (Placeholder) ---
async def run_indexing_pipeline(kb_id: UUID, variation_id: UUID, indexer_config: IndexerConfigBase):
    """
    The core asynchronous task that runs the parsing, chunking, and ingestion pipeline.
    """
    variation_obj = None # Will be loaded from metadata

    try:
        # 0. Load variation metadata to confirm details (optional, but good for consistency)
        metadata_path = await _get_variation_metadata_path(kb_id, variation_id)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                variation_data = json.load(f)
                # variation_obj = Variation(**variation_data) # Re-validate if needed
        else:
            # Should not happen if called after metadata creation
            await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, "Variation metadata not found at start of pipeline.")
            return

        await _update_variation_status(kb_id, variation_id, TaskStatusEnum.PROCESSING)

        # 1. Setup Directories
        variation_dir = await _get_variation_dir(kb_id, variation_id)
        raw_data_dir = await _get_kb_raw_data_dir(kb_id)
        config_dir = await _get_variation_config_dir(kb_id, variation_id)
        
        processed_data_dir = await _get_variation_processed_data_dir(kb_id, variation_id)
        parser_project_dir = os.path.join(processed_data_dir, "parser_output")
        chunker_project_dir = os.path.join(processed_data_dir, "chunker_output")
        index_dir = await _get_variation_index_dir(kb_id, variation_id)
        # final_corpus_dir is processed_data_dir itself for corpus.parquet

        for d in [variation_dir, raw_data_dir, config_dir, processed_data_dir, parser_project_dir, chunker_project_dir, index_dir]:
            os.makedirs(d, exist_ok=True)

        # 2. Prepare Parser Configuration (parser.yaml)
        parser_yaml_path = os.path.join(config_dir, "parser.yaml")
        # Using a simple default parser config targeting common file types
        # In a real scenario, this might be more dynamic or user-configurable
        default_parser_config = {
            "modules": [
                {"module_type": "langchain_parse", "parse_method": "pdfminer", "file_type": "pdf"},
                {"module_type": "langchain_parse", "parse_method": "unstructured", "file_type": "txt"},
                {"module_type": "langchain_parse", "parse_method": "unstructuredmarkdown", "file_type": "md"},
                # Add other common types if necessary, or rely on autorag's internal default_map
            ]
        }
        with open(parser_yaml_path, 'w') as f:
            yaml.dump(default_parser_config, f)

        # 3. Run Parser
        print(f"Starting parser for variation {variation_id}...")
        parser_instance = AutoRAGParser(data_path_glob=os.path.join(raw_data_dir, "*"), project_dir=parser_project_dir)
        # Setting all_files=False allows processing of multiple file types if specified in YAML,
        # and it will create a single parsed_result.parquet by concatenation.
        parser_instance.start_parsing(yaml_path=parser_yaml_path, all_files=False)
        parsed_output_parquet = os.path.join(parser_project_dir, "parsed_result.parquet")
        
        if not os.path.exists(parsed_output_parquet):
            await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, "Parser did not produce parsed_result.parquet.")
            return
        print(f"Parser finished for variation {variation_id}. Output: {parsed_output_parquet}")

        # 4. Prepare Chunker Configuration (chunker.yaml)
        chunker_yaml_path = os.path.join(config_dir, "chunker.yaml")
        # This will be simple as we expect one chunking strategy per variation
        # TODO: Make chunk_size, chunk_overlap configurable via IndexerConfigBase if not already
        chunker_config_content = {
            "modules": [
                {
                    "module_type": "llama_index_chunk", # Defaulting to llama_index_chunk
                    "chunk_method": "TokenTextSplitter", # A common default
                    "chunk_size": 512, # Example default, should come from indexer_config ideally
                    "chunk_overlap": 50  # Example default
                }
            ]
        }
        # Example: If indexer_config had specific chunker settings:
        # if indexer_config.chunker_settings: # Hypothetical field
        #     chunker_config_content["modules"][0].update(indexer_config.chunker_settings)

        with open(chunker_yaml_path, 'w') as f:
            yaml.dump(chunker_config_content, f)
            
        # 5. Run Chunker
        print(f"Starting chunker for variation {variation_id}...")
        # Chunker.from_parquet expects the direct path to the parquet file.
        chunker_instance = AutoRAGChunker.from_parquet(parsed_data_path=parsed_output_parquet, project_dir=chunker_project_dir)
        chunker_instance.start_chunking(yaml_path=chunker_yaml_path)
        
        # run_chunker saves output as 0.parquet, 1.parquet etc.
        # Assuming one strategy in YAML, output is 0.parquet
        chunked_output_temp_path = os.path.join(chunker_project_dir, "0.parquet")
        if not os.path.exists(chunked_output_temp_path):
            await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, "Chunker did not produce 0.parquet.")
            return
        print(f"Chunker finished for variation {variation_id}. Output: {chunked_output_temp_path}")

        # 6. Finalize Corpus (move/rename chunker output to corpus.parquet)
        final_corpus_path = os.path.join(processed_data_dir, "corpus.parquet")
        shutil.move(chunked_output_temp_path, final_corpus_path)
        print(f"Corpus finalized at: {final_corpus_path}")

        # Load the final corpus data for ingestion
        corpus_df = pd.read_parquet(final_corpus_path)

        # 7. Call Ingestion
        if indexer_config.method == "bm25":
            print(f"Starting BM25 ingestion for variation {variation_id}...")
            bm25_tokenizer = indexer_config.bm25_options.tokenizer if indexer_config.bm25_options else "porter_stemmer"
            # Define the output path for the BM25 pickle file within the variation's index directory
            bm25_output_pkl_path = os.path.join(index_dir, f"bm25_{bm25_tokenizer.replace('/', '-')}.pkl")
            bm25_ingest(corpus_path=bm25_output_pkl_path, corpus_data=corpus_df, bm25_tokenizer=bm25_tokenizer)
            print(f"BM25 ingestion done for variation {variation_id}.")
        
        elif indexer_config.method == "embedding":
            print(f"Starting VectorDB ingestion for variation {variation_id}...")
            if not indexer_config.embedding_options:
                await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, "Embedding options missing for embedding method.")
                return

            # Create vectordb.yaml
            vectordb_yaml_path = os.path.join(config_dir, "vectordb.yaml")
            # The structure for vectordb.yaml for autorag is a dictionary where keys are vectordb_names
            # and values are their configurations.
            # Our API schema stores this in embedding_options.vectordb_configs
            
            # Convert Pydantic models to dict for YAML dump
            yaml_compatible_configs = {}
            for name, cfg in indexer_config.embedding_options.vectordb_configs.items():
                # Assuming cfg is already a Pydantic model (VectorDBConfig)
                # And its sub-model (EmbeddingModelConfig) also needs model_dump
                cfg_dict = cfg.model_dump()
                if 'embedding_model' in cfg_dict and isinstance(cfg_dict['embedding_model'], BaseModel): # BaseModel is Pydantic's base
                     cfg_dict['embedding_model'] = cfg_dict['embedding_model'].model_dump()
                yaml_compatible_configs[name] = cfg_dict


            with open(vectordb_yaml_path, 'w') as f:
                yaml.dump(yaml_compatible_configs, f, sort_keys=False)
            print(f"vectordb.yaml created at {vectordb_yaml_path}")
            
            # Load the VectorDB instance using the created YAML and project_dir (variation_dir)
            # The project_dir for load_vectordb_from_yaml is where it looks for relative paths in vectordb.yaml (like persist_path)
            vector_store_instance = load_vectordb_from_yaml(
                yaml_path=vectordb_yaml_path, 
                vectordb_name=indexer_config.embedding_options.default_vectordb_config_name, # This is the key from the YAML
                project_dir=variation_dir # The variation_dir is the root for relative persist_paths
            )
            
            # vectordb_ingest is an async function
            await vectordb_ingest(
                vectordb=vector_store_instance, 
                corpus_data=corpus_df
            )
            print(f"VectorDB ingestion done for variation {variation_id}.")
        else:
            await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, f"Unknown indexer method: {indexer_config.method}")
            return

        await _update_variation_status(kb_id, variation_id, TaskStatusEnum.SUCCESS)
        print(f"Pipeline SUCCESS for variation {variation_id}")

    except Exception as e:
        print(f"Pipeline FAILED for variation {variation_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        await _update_variation_status(kb_id, variation_id, TaskStatusEnum.FAILURE, str(e))


# --- Endpoints ---
@router.post("/", response_model=Variation, status_code=status.HTTP_202_ACCEPTED)
async def create_variation(
    kb_id: UUID, 
    variation_create: VariationCreate, 
    background_tasks: BackgroundTasks
):
    """Create a new processed and indexed variation from the raw data of a knowledge base."""
    kb_dir = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")

    new_variation = Variation(
        **variation_create.model_dump(), 
        knowledge_base_id=kb_id,
        status=TaskStatusEnum.PENDING # Initial status
    )
    variation_id = new_variation.id
    
    var_dir = await _get_variation_dir(kb_id, variation_id)
    var_config_dir = await _get_variation_config_dir(kb_id, variation_id)
    var_processed_data_dir = await _get_variation_processed_data_dir(kb_id, variation_id)
    var_index_dir = await _get_variation_index_dir(kb_id, variation_id)

    try:
        os.makedirs(var_dir, exist_ok=False)
        os.makedirs(var_config_dir, exist_ok=True)
        os.makedirs(var_processed_data_dir, exist_ok=True)
        os.makedirs(var_index_dir, exist_ok=True)
        await _save_variation_metadata(kb_id, new_variation) # Save initial metadata
    except FileExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Variation with ID {variation_id} might already exist or collision.")
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create variation directories: {e}")

    # Add indexing to background tasks
    background_tasks.add_task(run_indexing_pipeline, kb_id, variation_id, variation_create.indexer_config)
    
    return new_variation

@router.get("/", response_model=List[VariationSummary])
async def list_variations(kb_id: UUID):
    """List all available variations for a given knowledge base."""
    variations_dir = await _get_kb_variations_dir(kb_id)
    if not os.path.isdir(variations_dir):
        # This could mean the KB doesn't exist or has no variations dir yet
        kb_main_dir = await _get_kb_dir(kb_id)
        if not os.path.isdir(kb_main_dir):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")
        return [] # No variations directory, so no variations

    summaries: List[VariationSummary] = []
    for item_name in os.listdir(variations_dir):
        item_path = os.path.join(variations_dir, item_name)
        if os.path.isdir(item_path):
            try:
                variation_id = UUID(item_name)
                meta = await _load_variation_metadata(kb_id, variation_id)
                summaries.append(VariationSummary(
                    id=meta.id,
                    name=meta.name,
                    status=meta.status,
                    method=meta.indexer_config.method
                ))
            except (ValueError, HTTPException) as e: # HTTPException if metadata not found for a dir
                # Not a valid UUID named directory or metadata issue, log and skip
                print(f"Skipping directory {item_name} in variations: {e}") # Replace with logging
    return summaries

@router.get("/{variation_id}", response_model=Variation)
async def get_variation(kb_id: UUID, variation_id: UUID):
    """Get detailed information about a specific variation."""
    # Check if KB exists first
    kb_main_dir = await _get_kb_dir(kb_id)
    if not os.path.isdir(kb_main_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found")

    return await _load_variation_metadata(kb_id, variation_id)

@router.delete("/{variation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variation(kb_id: UUID, variation_id: UUID):
    """Delete a specific variation (its processed data, index, and configuration)."""
    variation_dir = await _get_variation_dir(kb_id, variation_id)
    if not os.path.isdir(variation_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variation not found")
    
    try:
        shutil.rmtree(variation_dir)
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete variation: {e}")
    return

# Placeholder for task status endpoint (can be moved to a dedicated tasks.py router)
@router.get("/{variation_id}/status", response_model=TaskStatus)
async def get_variation_indexing_status(kb_id: UUID, variation_id: UUID):
    """Get the indexing status of a specific variation."""
    try:
        variation_meta = await _load_variation_metadata(kb_id, variation_id)
        # This is a simplified status; a real task manager would be better
        return TaskStatus(
            task_id=f"indexing_{variation_id}", 
            status=variation_meta.status,
            message=f"Indexing status for variation {variation_id}"
        )
    except HTTPException as e:
        if e.status_code == 404:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variation or its metadata not found, cannot get status.")
        raise e 