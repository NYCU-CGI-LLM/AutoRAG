import logging
import tempfile
import os
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Union
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.indexer import Indexer, IndexerStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.services.minio_service import MinIOService

# Import our enhanced Qdrant class directly
from autorag.vectordb.qdrant import Qdrant

logger = logging.getLogger(__name__)

class QdrantIndexService:
    """Simplified service for Qdrant-only indexing operations"""
    
    def __init__(self):
        self.minio_service = MinIOService()
    
    async def create_qdrant_index(
        self,
        session: Session,
        chunk_result_ids: List[int],
        collection_name: str,
        embedding_model: str = "openai_embed_3_large",
        qdrant_config: Optional[Dict[str, Any]] = None,
        metadata_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Qdrant index from chunk results
        
        Args:
            session: Database session
            chunk_result_ids: List of chunk result IDs to index
            collection_name: Qdrant collection name
            embedding_model: Embedding model to use
            qdrant_config: Qdrant connection configuration
            metadata_config: Additional metadata configuration
            
        Returns:
            Indexing result with collection info
        """
        
        # Default Qdrant configuration
        default_config = {
            "client_type": "docker",
            "url": "http://localhost:6333",
            "similarity_metric": "cosine",
            "store_text": True,
            "use_uuid_ids": True,
            "embedding_batch": 50,
            "ingest_batch": 64,
            "parallel": 2,
            "max_retries": 3
        }
        
        if qdrant_config:
            default_config.update(qdrant_config)
        
        try:
            # 1. Get chunk results from database
            chunk_results = session.exec(
                select(FileChunkResult).where(FileChunkResult.id.in_(chunk_result_ids))
            ).all()
            
            if len(chunk_results) != len(chunk_result_ids):
                raise HTTPException(status_code=404, detail="Some chunk results not found")
            
            # Check all chunk results are successful
            failed_results = [cr for cr in chunk_results if cr.status != ChunkStatus.SUCCESS]
            if failed_results:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Chunk results {[cr.id for cr in failed_results]} are not successful"
                )
            
            # 2. Load and combine all chunk data
            logger.info(f"Loading chunk data for {len(chunk_results)} chunk results")
            all_chunks_data = []
            
            for chunk_result in chunk_results:
                chunk_data = self._load_chunk_parquet(chunk_result)
                # Add source metadata
                chunk_data['source_file'] = chunk_result.file_name
                chunk_data['chunk_result_id'] = chunk_result.id
                all_chunks_data.append(chunk_data)
            
            # Combine all chunks into single DataFrame
            combined_df = pd.concat(all_chunks_data, ignore_index=True)
            logger.info(f"Combined {len(combined_df)} total chunks")
            
            # 3. Initialize Qdrant with enhanced configuration
            logger.info(f"Initializing Qdrant with collection: {collection_name}")
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **default_config
            )
            
            # 4. Prepare documents and metadata for indexing
            doc_ids = combined_df['doc_id'].tolist()
            contents = combined_df['contents'].tolist()
            
            # Create rich metadata for each document
            metadata_list = []
            for idx, row in combined_df.iterrows():
                doc_metadata = {
                    "source_file": row.get('source_file', ''),
                    "chunk_result_id": int(row.get('chunk_result_id', 0)),
                    "chunk_index": int(idx),
                    "content_length": len(row['contents']),
                    "doc_type": "chunk",
                    "indexed_at": datetime.utcnow().isoformat(),
                    "embedding_model": embedding_model
                }
                
                # Add any additional metadata from config
                if metadata_config:
                    doc_metadata.update(metadata_config)
                
                # Add any existing metadata from the chunk
                if 'metadata' in row and pd.notna(row['metadata']):
                    try:
                        if isinstance(row['metadata'], str):
                            existing_metadata = json.loads(row['metadata'])
                        else:
                            existing_metadata = row['metadata']
                        doc_metadata.update(existing_metadata)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                metadata_list.append(doc_metadata)
            
            # 5. Index documents in Qdrant with payload
            logger.info(f"Indexing {len(doc_ids)} documents to Qdrant collection '{collection_name}'")
            
            # Use the enhanced add method with metadata
            await qdrant.add(doc_ids, contents, metadata_list)
            
            # 6. Get collection stats
            collection_info = await qdrant.get_collection_info()
            
            # 7. Save indexing metadata to MinIO
            index_metadata = {
                "collection_name": collection_name,
                "embedding_model": embedding_model,
                "qdrant_config": default_config,
                "chunk_result_ids": chunk_result_ids,
                "total_documents": len(doc_ids),
                "source_files": combined_df['source_file'].unique().tolist(),
                "indexed_at": datetime.utcnow().isoformat(),
                "collection_info": collection_info,
                "status": "success"
            }
            
            # Save metadata to MinIO
            metadata_key = f"qdrant_indexes/{collection_name}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}/metadata.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as temp_file:
                json.dump(index_metadata, temp_file, indent=2, default=str)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as f:
                    self.minio_service.client.put_object(
                        bucket_name="rag-indexes",
                        object_name=metadata_key,
                        data=f,
                        length=os.path.getsize(temp_file.name),
                        content_type="application/json"
                    )
                
                os.unlink(temp_file.name)
            
            logger.info(f"Successfully indexed {len(doc_ids)} documents to Qdrant collection '{collection_name}'")
            
            return {
                "status": "success",
                "collection_name": collection_name,
                "total_documents": len(doc_ids),
                "embedding_model": embedding_model,
                "metadata_key": metadata_key,
                "collection_info": collection_info,
                "indexed_files": combined_df['source_file'].unique().tolist()
            }
            
        except Exception as e:
            logger.error(f"Failed to create Qdrant index: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create Qdrant index: {str(e)}")
    
    async def search_qdrant_collection(
        self,
        collection_name: str,
        query: str,
        top_k: int = 10,
        embedding_model: str = "openai_embed_3_large",
        qdrant_config: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search in Qdrant collection with payload
        
        Args:
            collection_name: Qdrant collection name
            query: Search query
            top_k: Number of results to return
            embedding_model: Embedding model to use
            qdrant_config: Qdrant connection configuration
            filters: Search filters for metadata
            
        Returns:
            Search results with payload data
        """
        
        # Default Qdrant configuration
        default_config = {
            "client_type": "docker",
            "url": "http://localhost:6333"
        }
        
        if qdrant_config:
            default_config.update(qdrant_config)
        
        try:
            # Initialize Qdrant
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **default_config
            )
            
            # Perform search with payload
            results = await qdrant.query_with_payload(
                query_texts=[query],
                top_k=top_k,
                filters=filters
            )
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append({
                    "rank": i + 1,
                    "doc_id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                    "source_file": result.get("metadata", {}).get("source_file", ""),
                    "indexed_at": result.get("metadata", {}).get("indexed_at", "")
                })
            
            logger.info(f"Search in collection '{collection_name}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search Qdrant collection: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to search collection: {str(e)}")
    
    async def get_collection_stats(
        self,
        collection_name: str,
        embedding_model: str = "openai_embed_3_large",
        qdrant_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get statistics for Qdrant collection"""
        
        default_config = {
            "client_type": "docker",
            "url": "http://localhost:6333"
        }
        
        if qdrant_config:
            default_config.update(qdrant_config)
        
        try:
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **default_config
            )
            
            collection_info = await qdrant.get_collection_info()
            
            return {
                "collection_name": collection_name,
                "embedding_model": embedding_model,
                "status": "active",
                "collection_info": collection_info,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "collection_name": collection_name,
                "status": "error",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def _load_chunk_parquet(self, chunk_result: FileChunkResult) -> pd.DataFrame:
        """Load chunked data from MinIO parquet file"""
        
        try:
            # Download parquet file from MinIO
            file_data = self.minio_service.download_file(chunk_result.object_key)
            
            # Load as DataFrame
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as temp_file:
                temp_file.write(file_data.read())
                temp_file.flush()
                
                df = pd.read_parquet(temp_file.name)
                os.unlink(temp_file.name)
            
            logger.debug(f"Loaded {len(df)} chunks from {chunk_result.object_key}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load chunk parquet {chunk_result.object_key}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to load chunk data: {str(e)}"
            ) 