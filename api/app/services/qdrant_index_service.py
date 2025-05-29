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
from app.models.retriever import Retriever, RetrieverStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.services.minio_service import MinIOService

# Import our enhanced Qdrant class directly
from autorag.vectordb.qdrant import Qdrant

logger = logging.getLogger(__name__)

class QdrantIndexService:
    """Enhanced service for Qdrant indexing operations with database integration"""
    
    def __init__(self):
        self.minio_service = MinIOService()
        
        # Default Qdrant configuration for single server setup
        self.default_qdrant_config = {
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
        
        # Default embedding model
        self.default_embedding_model = "openai_embed_3_large"
    
    def get_indexer_by_id(self, session: Session, indexer_id: UUID) -> Optional[Indexer]:
        """Get indexer by ID"""
        return session.get(Indexer, indexer_id)
    
    def get_active_indexers(self, session: Session) -> List[Indexer]:
        """Get all active indexers"""
        statement = select(Indexer).where(Indexer.status == IndexerStatus.ACTIVE)
        return session.exec(statement).all()
    
    def create_indexer(
        self,
        session: Session,
        name: str,
        index_type: str = "vector",
        model: str = None,
        params: Dict[str, Any] = None
    ) -> Indexer:
        """Create a new indexer configuration"""
        try:
            model = model or self.default_embedding_model
            params = params or {}
            
            # Check if indexer name already exists
            statement = select(Indexer).where(Indexer.name == name)
            existing_indexer = session.exec(statement).first()
            
            if existing_indexer:
                raise HTTPException(
                    status_code=409,
                    detail=f"Indexer with name '{name}' already exists"
                )
            
            indexer = Indexer(
                name=name,
                index_type=index_type,
                model=model,
                params=params,
                status=IndexerStatus.ACTIVE
            )
            
            session.add(indexer)
            session.commit()
            session.refresh(indexer)
            
            logger.info(f"Created indexer: {name} (ID: {indexer.id})")
            return indexer
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating indexer: {e}")
            raise HTTPException(status_code=500, detail="Failed to create indexer")

    async def create_qdrant_index_for_retriever(
        self,
        session: Session,
        retriever_id: UUID,
        chunk_result_ids: List[UUID],
        metadata_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Qdrant index for a specific retriever
        Updates retriever status and stores collection info
        """
        try:
            # Get retriever and validate
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            # Update retriever status to building
            retriever.status = RetrieverStatus.BUILDING
            session.add(retriever)
            session.commit()
            
            # Get indexer configuration
            indexer = session.get(Indexer, retriever.indexer_id)
            if not indexer:
                raise HTTPException(status_code=404, detail="Indexer not found")
            
            # Use indexer model as embedding model
            embedding_model = indexer.model
            collection_name = retriever.collection_name or f"retriever_{retriever_id}"
            
            # Merge indexer params with default config
            qdrant_config = self.default_qdrant_config.copy()
            qdrant_config.update(indexer.params)
            
            logger.info(f"Creating Qdrant index for retriever {retriever_id}")
            logger.info(f"Collection: {collection_name}, Model: {embedding_model}")
            
            # Create the index
            result = await self.create_qdrant_index(
                session=session,
                chunk_result_ids=chunk_result_ids,
                collection_name=collection_name,
                embedding_model=embedding_model,
                qdrant_config=qdrant_config,
                metadata_config=metadata_config
            )
            
            # Update retriever with success info
            retriever.status = RetrieverStatus.ACTIVE
            retriever.collection_name = collection_name
            retriever.indexed_at = datetime.utcnow()
            retriever.total_chunks = result["total_documents"]
            retriever.extra_meta = {
                "collection_info": result["collection_info"],
                "indexed_files": result["indexed_files"],
                "embedding_model": embedding_model
            }
            session.add(retriever)
            session.commit()
            
            logger.info(f"Successfully indexed retriever {retriever_id}")
            
            return {
                **result,
                "retriever_id": str(retriever_id),
                "retriever_status": "active"
            }
            
        except Exception as e:
            # Update retriever status to failed
            if 'retriever' in locals():
                retriever.status = RetrieverStatus.FAILED
                retriever.error_message = str(e)
                session.add(retriever)
                session.commit()
            
            logger.error(f"Failed to create index for retriever {retriever_id}: {str(e)}")
            raise

    async def create_qdrant_index(
        self,
        session: Session,
        chunk_result_ids: List[UUID],
        collection_name: str,
        embedding_model: Optional[str] = None,
        qdrant_config: Optional[Dict[str, Any]] = None,
        metadata_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Qdrant index from chunk results
        Core indexing logic (unchanged from previous implementation)
        """
        
        # Use defaults if not provided
        embedding_model = embedding_model or self.default_embedding_model
        config = self.default_qdrant_config.copy()
        if qdrant_config:
            config.update(qdrant_config)
        
        try:
            # 1. Get chunk results from database
            chunk_results = session.exec(
                select(FileChunkResult).where(FileChunkResult.id.in_(chunk_result_ids))
            ).all()
            
            if len(chunk_results) != len(chunk_result_ids):
                missing_ids = set(chunk_result_ids) - set(cr.id for cr in chunk_results)
                raise HTTPException(
                    status_code=404, 
                    detail=f"Chunk results not found: {list(missing_ids)}"
                )
            
            # Check all chunk results are successful
            failed_results = [cr for cr in chunk_results if cr.status != ChunkStatus.SUCCESS]
            if failed_results:
                failed_info = [
                    {"id": str(cr.id), "status": cr.status.value, "error": cr.error_message}
                    for cr in failed_results
                ]
                raise HTTPException(
                    status_code=400, 
                    detail=f"Some chunk results are not successful: {failed_info}"
                )
            
            # Verify all files exist in MinIO before proceeding
            logger.info(f"Verifying {len(chunk_results)} chunk files exist in MinIO")
            missing_files = []
            for chunk_result in chunk_results:
                try:
                    self.minio_service.client.stat_object(
                        bucket_name=chunk_result.bucket,
                        object_name=chunk_result.object_key
                    )
                except Exception:
                    missing_files.append({
                        "chunk_result_id": str(chunk_result.id),
                        "bucket": chunk_result.bucket,
                        "object_key": chunk_result.object_key,
                        "file_name": chunk_result.file.file_name if chunk_result.file else "Unknown"
                    })
            
            if missing_files:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": "Some chunk files are missing from MinIO storage",
                        "missing_files": missing_files,
                        "suggestion": "These chunk results may need to be recreated."
                    }
                )
            
            # 2. Load and combine all chunk data
            logger.info(f"Loading chunk data for {len(chunk_results)} chunk results")
            all_chunks_data = []
            
            for chunk_result in chunk_results:
                try:
                    chunk_data = self._load_chunk_parquet(chunk_result)
                    # Add source metadata
                    chunk_data['source_file'] = chunk_result.file.file_name if chunk_result.file else 'Unknown'
                    chunk_data['chunk_result_id'] = chunk_result.id
                    all_chunks_data.append(chunk_data)
                except Exception as e:
                    logger.error(f"Failed to load chunk data for {chunk_result.id}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "message": f"Failed to load chunk data for result {chunk_result.id}",
                            "error": str(e),
                            "file_info": {
                                "bucket": chunk_result.bucket,
                                "object_key": chunk_result.object_key,
                                "status": chunk_result.status.value
                            }
                        }
                    )
            
            # Combine all chunks into single DataFrame
            combined_df = pd.concat(all_chunks_data, ignore_index=True)
            logger.info(f"Combined {len(combined_df)} total chunks")
            
            # 3. Initialize Qdrant with enhanced configuration
            logger.info(f"Initializing Qdrant with collection: {collection_name}")
            logger.info(f"Embedding model: {embedding_model}")
            
            # Filter config parameters for Qdrant
            valid_qdrant_params = {
                'embedding_model', 'collection_name', 'embedding_batch', 'similarity_metric',
                'client_type', 'url', 'host', 'api_key', 'dimension', 'ingest_batch', 
                'parallel', 'max_retries', 'store_text', 'use_uuid_ids'
            }
            filtered_config = {k: v for k, v in config.items() if k in valid_qdrant_params}
            invalid_params = {k: v for k, v in config.items() if k not in valid_qdrant_params}
            
            if invalid_params:
                logger.warning(f"Removing invalid Qdrant parameters: {invalid_params}")
            
            logger.info(f"Filtered config for Qdrant: {filtered_config}")
            
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **filtered_config
            )
            
            # 4. Prepare documents and metadata for indexing
            doc_ids = combined_df['doc_id'].tolist()
            contents = combined_df['contents'].tolist()
            
            # Create rich metadata for each document
            metadata_list = []
            for idx, row in combined_df.iterrows():
                doc_metadata = {
                    "source_file": row.get('source_file', ''),
                    "chunk_result_id": str(row.get('chunk_result_id', '')),
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
            
            # Use enhanced add method with metadata
            await qdrant.add(doc_ids, contents, metadata_list)
            
            # 6. Get collection stats
            collection_info = qdrant.client.get_collection(collection_name)
            collection_stats = {
                "collection_name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "params": {
                        "vector_size": collection_info.config.params.vectors.size,
                        "distance": collection_info.config.params.vectors.distance.value
                    }
                }
            }
            
            # 7. Save indexing metadata to MinIO
            index_metadata = {
                "collection_name": collection_name,
                "embedding_model": embedding_model,
                "qdrant_config": config,
                "chunk_result_ids": [str(cid) for cid in chunk_result_ids],
                "total_documents": len(doc_ids),
                "source_files": combined_df['source_file'].unique().tolist(),
                "indexed_at": datetime.utcnow().isoformat(),
                "collection_info": collection_stats,
                "status": "success"
            }
            
            # Ensure rag-indexes bucket exists
            try:
                if not self.minio_service.client.bucket_exists("rag-indexes"):
                    self.minio_service.client.make_bucket("rag-indexes")
            except Exception as e:
                logger.warning(f"Could not create rag-indexes bucket: {e}")
            
            # Save metadata to MinIO
            metadata_key = f"qdrant_indexes/{collection_name}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}/metadata.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as temp_file:
                json.dump(index_metadata, temp_file, indent=2, default=str)
                temp_file.flush()
                
                try:
                    with open(temp_file.name, 'rb') as f:
                        self.minio_service.client.put_object(
                            bucket_name="rag-indexes",
                            object_name=metadata_key,
                            data=f,
                            length=os.path.getsize(temp_file.name),
                            content_type="application/json"
                        )
                    logger.info(f"Saved index metadata to MinIO: {metadata_key}")
                except Exception as e:
                    logger.warning(f"Failed to save metadata to MinIO: {e}")
                finally:
                    os.unlink(temp_file.name)
            
            logger.info(f"Successfully indexed {len(doc_ids)} documents to Qdrant collection '{collection_name}'")
            
            return {
                "status": "success",
                "collection_name": collection_name,
                "total_documents": len(doc_ids),
                "embedding_model": embedding_model,
                "metadata_key": metadata_key,
                "collection_info": collection_stats,
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
        embedding_model: Optional[str] = None,
        qdrant_config: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search in Qdrant collection with payload
        """
        
        # Use defaults if not provided
        embedding_model = embedding_model or self.default_embedding_model
        config = self.default_qdrant_config.copy()
        if qdrant_config:
            config.update(qdrant_config)
        
        try:
            # Filter config parameters for Qdrant
            valid_qdrant_params = {
                'embedding_model', 'collection_name', 'embedding_batch', 'similarity_metric',
                'client_type', 'url', 'host', 'api_key', 'dimension', 'ingest_batch', 
                'parallel', 'max_retries', 'store_text', 'use_uuid_ids'
            }
            filtered_config = {k: v for k, v in config.items() if k in valid_qdrant_params}
            
            # Initialize Qdrant
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **filtered_config
            )
            
            # Perform search with payload
            try:
                results_with_payload, scores = await qdrant.query_with_payload(
                    queries=[query],
                    top_k=top_k
                )
            except AttributeError:
                # Fallback to basic query if payload method not available
                logger.warning("query_with_payload not available, using basic query")
                result_ids, scores = await qdrant.query(
                    queries=[query],
                    top_k=top_k
                )
                results_with_payload = [[{"id": id_} for id_ in result_ids[0]]]
            
            # Format results
            formatted_results = []
            if results_with_payload and len(results_with_payload) > 0:
                for i, (result, score) in enumerate(zip(results_with_payload[0], scores[0])):
                    # Extract content from payload
                    payload = result.get("payload", {})
                    content = payload.get("text", "")
                    
                    formatted_results.append({
                        "rank": i + 1,
                        "doc_id": result.get("id", ""),
                        "content": content,
                        "score": score,
                        "metadata": payload,
                        "source_file": payload.get("source_file", ""),
                        "indexed_at": payload.get("indexed_at", "")
                    })
            
            logger.info(f"Search in collection '{collection_name}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search Qdrant collection: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to search collection: {str(e)}")

    async def get_collection_stats(
        self,
        collection_name: str,
        embedding_model: Optional[str] = None,
        qdrant_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get statistics for Qdrant collection"""
        
        # Use defaults if not provided
        embedding_model = embedding_model or self.default_embedding_model
        config = self.default_qdrant_config.copy()
        if qdrant_config:
            config.update(qdrant_config)
        
        try:
            # Filter config parameters for Qdrant
            valid_qdrant_params = {
                'embedding_model', 'collection_name', 'embedding_batch', 'similarity_metric',
                'client_type', 'url', 'host', 'api_key', 'dimension', 'ingest_batch', 
                'parallel', 'max_retries', 'store_text', 'use_uuid_ids'
            }
            filtered_config = {k: v for k, v in config.items() if k in valid_qdrant_params}
            
            qdrant = Qdrant(
                embedding_model=embedding_model,
                collection_name=collection_name,
                **filtered_config
            )
            
            collection_info = qdrant.client.get_collection(collection_name)
            collection_stats = {
                "collection_name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "config": {
                    "params": {
                        "vector_size": collection_info.config.params.vectors.size,
                        "distance": collection_info.config.params.vectors.distance.value
                    }
                }
            }
            
            return {
                "collection_name": collection_name,
                "embedding_model": embedding_model,
                "status": "active",
                "collection_info": collection_stats,
                "qdrant_config": {
                    "url": config.get("url"),
                    "client_type": config.get("client_type")
                },
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "collection_name": collection_name,
                "embedding_model": embedding_model,
                "status": "error", 
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def _load_chunk_parquet(self, chunk_result: FileChunkResult) -> pd.DataFrame:
        """Load chunked data from MinIO parquet file"""
        
        try:
            # Download parquet file from MinIO using the correct bucket
            file_data = self.minio_service.download_file(
                object_name=chunk_result.object_key,
                bucket_name=chunk_result.bucket
            )
            
            # Load as DataFrame
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as temp_file:
                temp_file.write(file_data.read())
                temp_file.flush()
                
                df = pd.read_parquet(temp_file.name)
                os.unlink(temp_file.name)
            
            logger.debug(f"Loaded {len(df)} chunks from {chunk_result.bucket}/{chunk_result.object_key}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load chunk parquet {chunk_result.bucket}/{chunk_result.object_key}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to load chunk data: {str(e)}"
            )
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get the default Qdrant configuration"""
        return self.default_qdrant_config.copy()
    
    def get_default_embedding_model(self) -> str:
        """Get the default embedding model"""
        return self.default_embedding_model 