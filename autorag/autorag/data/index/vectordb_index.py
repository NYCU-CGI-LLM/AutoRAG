import asyncio
import logging
import uuid
import os
from typing import List, Dict, Any, Tuple, Optional

from autorag.data.index.base import indexer_node
from autorag.vectordb import load_vectordb

logger = logging.getLogger("AutoRAG")


@indexer_node
def vectordb_index(
    doc_ids: List[str],
    contents: List[str],
    index_type: str,
    metadata_list: List[Dict[str, Any]],
    vectordb_type: str = "chroma",
    embedding_model: str = "openai_embed_3_large",
    collection_name: Optional[str] = None,
    **vectordb_kwargs
) -> Tuple[List[str], List[str], List[str], List[Dict[str, Any]]]:
    """
    Create vector database index for chunked documents.
    
    Args:
        doc_ids: List of document IDs from chunked data
        contents: List of document contents from chunked data
        index_type: Type of index (should be "vector" for this function)
        metadata_list: List of metadata dictionaries for each document
        vectordb_type: Type of vector database (chroma, pinecone, qdrant, etc.)
        embedding_model: Name of the embedding model to use
        collection_name: Name of the collection/index in the vector database
        **vectordb_kwargs: Additional parameters for vector database initialization
    
    Returns:
        Tuple of (doc_ids, index_ids, index_types, metadata_list)
    """
    
    if index_type != "vector":
        raise ValueError(f"vectordb_index only supports 'vector' index_type, got '{index_type}'")
    
    # Check for OpenAI API key if using OpenAI embedding models
    if "openai" in embedding_model.lower():
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key or openai_api_key.strip() == "":
            logger.warning("OPENAI_API_KEY not found or empty. Switching to mock embedding for testing.")
            embedding_model = "mock"
    
    # Generate collection name if not provided
    if collection_name is None:
        collection_name = f"{embedding_model}_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Creating vector index with {vectordb_type} for {len(doc_ids)} documents")
    logger.info(f"Using embedding model: {embedding_model}")
    logger.info(f"Collection name: {collection_name}")
    
    try:
        # Initialize vector database
        vectordb = load_vectordb(
            vectordb_type,
            embedding_model=embedding_model,
            collection_name=collection_name,
            **vectordb_kwargs
        )
        
        # Add documents to vector database
        if asyncio.iscoroutinefunction(vectordb.add):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(vectordb.add(doc_ids, contents))
        else:
            # For synchronous add methods
            vectordb.add(doc_ids, contents)
        
        logger.info(f"Successfully indexed {len(doc_ids)} documents to {vectordb_type}")
        
        # Generate index IDs (same as doc_ids for vector databases)
        index_ids = doc_ids.copy()
        
        # Create index types list
        index_types = ["vector"] * len(doc_ids)
        
        # Update metadata with indexing information
        updated_metadata_list = []
        for metadata in metadata_list:
            updated_metadata = metadata.copy()
            updated_metadata.update({
                "vectordb_type": vectordb_type,
                "embedding_model": embedding_model,
                "collection_name": collection_name,
                "index_type": "vector"
            })
            updated_metadata_list.append(updated_metadata)
        
        return doc_ids, index_ids, index_types, updated_metadata_list
        
    except Exception as e:
        logger.error(f"Error creating vector index: {str(e)}")
        raise RuntimeError(f"Failed to create vector index: {str(e)}") from e 