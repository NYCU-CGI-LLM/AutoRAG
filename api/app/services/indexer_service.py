import logging
import tempfile
import os
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.indexer import Indexer, IndexerStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.services.minio_service import MinIOService

from autorag.vectordb import vectordb_modules
from autorag.embedding.base import EmbeddingModel

logger = logging.getLogger(__name__)

class IndexerService:
    """Service for handling document indexing operations"""
    
    def __init__(self):
        self.minio_service = MinIOService()
    
    def get_indexer_by_id(self, session: Session, indexer_id: UUID) -> Optional[Indexer]:
        """Get indexer by ID"""
        statement = select(Indexer).where(Indexer.id == indexer_id)
        return session.exec(statement).first()
    
    def get_active_indexers(self, session: Session) -> List[Indexer]:
        """Get all active indexers"""
        statement = select(Indexer).where(Indexer.status == IndexerStatus.ACTIVE)
        return session.exec(statement).all()
    
    def create_indexer(
        self,
        session: Session,
        name: str,
        index_type: str,
        model: str,
        params: Dict[str, Any] = None
    ) -> Indexer:
        """Create a new indexer configuration"""
        indexer = Indexer(
            name=name,
            index_type=index_type,
            model=model,
            params=params or {},
            status=IndexerStatus.ACTIVE
        )
        session.add(indexer)
        session.commit()
        session.refresh(indexer)
        return indexer
    
    def index_chunk_results(
        self,
        session: Session,
        chunk_result_ids: List[int],
        indexer_id: UUID
    ) -> Dict[str, Any]:
        """Index multiple chunk results using specified indexer"""
        
        # Get indexer configuration
        indexer = self.get_indexer_by_id(session, indexer_id)
        if not indexer:
            raise HTTPException(status_code=404, detail="Indexer not found")
        
        # Get chunk results
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
        
        try:
            # Collect all chunked data
            all_chunks_data = []
            for chunk_result in chunk_results:
                chunk_data = self._get_chunked_data(chunk_result)
                all_chunks_data.append(chunk_data)
            
            # Combine all chunks into single DataFrame
            combined_df = pd.concat(all_chunks_data, ignore_index=True)
            
            # Create index based on indexer type
            index_result = self._create_index(combined_df, indexer)
            
            # Save index metadata to MinIO
            index_metadata = {
                "indexer_id": str(indexer_id),
                "indexer_name": indexer.name,
                "index_type": indexer.index_type,
                "model": indexer.model,
                "params": indexer.params,
                "chunk_result_ids": chunk_result_ids,
                "num_documents": len(combined_df),
                "created_at": datetime.utcnow().isoformat(),
                "index_info": index_result
            }
            
            # Save metadata to MinIO
            metadata_key = f"indexes/{indexer_id}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}/metadata.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json") as temp_file:
                json.dump(index_metadata, temp_file, indent=2, default=str)
                temp_file.seek(0)
                
                self.minio_service.client.put_object(
                    bucket_name="rag-indexes",
                    object_name=metadata_key,
                    data=temp_file,
                    length=os.path.getsize(temp_file.name),
                    content_type="application/json"
                )
            
            return {
                "status": "success",
                "indexer_id": str(indexer_id),
                "metadata_key": metadata_key,
                "num_documents": len(combined_df),
                "index_info": index_result
            }
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create index: {str(e)}")
    
    def _get_chunked_data(self, chunk_result: FileChunkResult) -> pd.DataFrame:
        """Get chunked data from MinIO"""
        
        # Download parquet file from MinIO
        file_data = self.minio_service.download_file(chunk_result.object_key)
        
        # Load as DataFrame
        with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
            temp_file.write(file_data.read())
            temp_file.seek(0)
            df = pd.read_parquet(temp_file.name)
        
        return df
    
    def _create_index(self, data: pd.DataFrame, indexer: Indexer) -> Dict[str, Any]:
        """Create index based on indexer configuration"""
        
        if indexer.index_type == "vector":
            return self._create_vector_index(data, indexer)
        elif indexer.index_type == "bm25":
            return self._create_bm25_index(data, indexer)
        elif indexer.index_type == "hybrid":
            # Create both vector and BM25 indexes
            vector_result = self._create_vector_index(data, indexer)
            bm25_result = self._create_bm25_index(data, indexer)
            return {
                "vector_index": vector_result,
                "bm25_index": bm25_result
            }
        else:
            raise ValueError(f"Unsupported index_type: {indexer.index_type}")
    
    def _create_vector_index(self, data: pd.DataFrame, indexer: Indexer) -> Dict[str, Any]:
        """Create vector index using autorag vectordb"""
        
        # Get vectordb configuration from params
        vectordb_type = indexer.params.get("vectordb_type", "chroma")
        vectordb_params = indexer.params.get("vectordb_params", {})
        
        # Initialize vector database
        vectordb_class = vectordb_modules.get(vectordb_type)
        if not vectordb_class:
            raise ValueError(f"Unsupported vectordb_type: {vectordb_type}")
        
        # Create vectordb instance
        vectordb = vectordb_class(
            embedding_model=indexer.model,
            **vectordb_params
        )
        
        # Prepare data for indexing
        doc_ids = data["doc_id"].tolist()
        contents = data["contents"].tolist()
        
        # Add documents to vector database
        # Note: This is async in the original implementation
        # For simplicity, we'll assume synchronous operation here
        # In production, you might want to use async/await
        try:
            # This would typically be: await vectordb.add(doc_ids, contents)
            # For now, we'll simulate the indexing process
            logger.info(f"Creating vector index for {len(doc_ids)} documents")
            
            # Save vector index data to MinIO
            index_data = {
                "doc_ids": doc_ids,
                "contents": contents,
                "vectordb_type": vectordb_type,
                "embedding_model": indexer.model,
                "vectordb_params": vectordb_params
            }
            
            # Save to MinIO
            index_key = f"indexes/{indexer.id}/vector_index.json"
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json") as temp_file:
                json.dump(index_data, temp_file, indent=2, default=str)
                temp_file.seek(0)
                
                self.minio_service.client.put_object(
                    bucket_name="rag-indexes",
                    object_name=index_key,
                    data=temp_file,
                    length=os.path.getsize(temp_file.name),
                    content_type="application/json"
                )
            
            return {
                "type": "vector",
                "vectordb_type": vectordb_type,
                "embedding_model": indexer.model,
                "num_documents": len(doc_ids),
                "index_key": index_key
            }
            
        except Exception as e:
            logger.error(f"Error creating vector index: {str(e)}")
            raise
    
    def _create_bm25_index(self, data: pd.DataFrame, indexer: Indexer) -> Dict[str, Any]:
        """Create BM25 index"""
        
        try:
            from rank_bm25 import BM25Okapi
            import pickle
        except ImportError:
            raise ImportError("rank_bm25 is required for BM25 indexing. Install with: pip install rank-bm25")
        
        # Prepare data for BM25 indexing
        doc_ids = data["doc_id"].tolist()
        contents = data["contents"].tolist()
        
        # Tokenize documents (simple whitespace tokenization)
        # In production, you might want to use more sophisticated tokenization
        tokenized_docs = [doc.lower().split() for doc in contents]
        
        # Create BM25 index
        bm25 = BM25Okapi(tokenized_docs)
        
        # Save BM25 index to MinIO
        index_data = {
            "doc_ids": doc_ids,
            "contents": contents,
            "tokenized_docs": tokenized_docs
        }
        
        # Save index data
        index_key = f"indexes/{indexer.id}/bm25_index.json"
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json") as temp_file:
            json.dump(index_data, temp_file, indent=2, default=str)
            temp_file.seek(0)
            
            self.minio_service.client.put_object(
                bucket_name="rag-indexes",
                object_name=index_key,
                data=temp_file,
                length=os.path.getsize(temp_file.name),
                content_type="application/json"
            )
        
        # Save BM25 model
        bm25_key = f"indexes/{indexer.id}/bm25_model.pkl"
        with tempfile.NamedTemporaryFile(suffix=".pkl") as temp_file:
            pickle.dump(bm25, temp_file)
            temp_file.seek(0)
            
            self.minio_service.client.put_object(
                bucket_name="rag-indexes",
                object_name=bm25_key,
                data=temp_file,
                length=os.path.getsize(temp_file.name),
                content_type="application/octet-stream"
            )
        
        return {
            "type": "bm25",
            "num_documents": len(doc_ids),
            "index_key": index_key,
            "model_key": bm25_key
        }
    
    def search_index(
        self,
        session: Session,
        indexer_id: UUID,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search in the created index"""
        
        indexer = self.get_indexer_by_id(session, indexer_id)
        if not indexer:
            raise HTTPException(status_code=404, detail="Indexer not found")
        
        if indexer.index_type == "vector":
            return self._search_vector_index(indexer, query, top_k)
        elif indexer.index_type == "bm25":
            return self._search_bm25_index(indexer, query, top_k)
        elif indexer.index_type == "hybrid":
            # Combine results from both indexes
            vector_results = self._search_vector_index(indexer, query, top_k)
            bm25_results = self._search_bm25_index(indexer, query, top_k)
            
            # Simple hybrid scoring (you might want to implement more sophisticated fusion)
            combined_results = []
            for i, result in enumerate(vector_results):
                result["vector_rank"] = i + 1
                result["vector_score"] = result.get("score", 0)
                combined_results.append(result)
            
            for i, result in enumerate(bm25_results):
                doc_id = result["doc_id"]
                # Find if this doc_id already exists in vector results
                existing = next((r for r in combined_results if r["doc_id"] == doc_id), None)
                if existing:
                    existing["bm25_rank"] = i + 1
                    existing["bm25_score"] = result.get("score", 0)
                    # Simple hybrid score: average of normalized ranks
                    existing["hybrid_score"] = (1/(existing["vector_rank"]) + 1/(i+1)) / 2
                else:
                    result["bm25_rank"] = i + 1
                    result["bm25_score"] = result.get("score", 0)
                    result["hybrid_score"] = 1/(i+1) / 2  # Only BM25 score
                    combined_results.append(result)
            
            # Sort by hybrid score and return top_k
            combined_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            return combined_results[:top_k]
        else:
            raise ValueError(f"Unsupported index_type: {indexer.index_type}")
    
    def _search_vector_index(self, indexer: Indexer, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search vector index"""
        # This is a simplified implementation
        # In production, you would load the actual vector database and perform similarity search
        
        try:
            # Load index data
            index_key = f"indexes/{indexer.id}/vector_index.json"
            file_data = self.minio_service.download_file(index_key)
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix=".json") as temp_file:
                temp_file.write(file_data.read().decode('utf-8'))
                temp_file.seek(0)
                index_data = json.load(temp_file)
            
            # Simulate vector search (in production, use actual vector database)
            doc_ids = index_data["doc_ids"]
            contents = index_data["contents"]
            
            # Simple text matching for demonstration
            results = []
            query_lower = query.lower()
            for i, (doc_id, content) in enumerate(zip(doc_ids, contents)):
                if query_lower in content.lower():
                    # Simple relevance score based on term frequency
                    score = content.lower().count(query_lower) / len(content.split())
                    results.append({
                        "doc_id": doc_id,
                        "content": content,
                        "score": score,
                        "rank": len(results) + 1
                    })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching vector index: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error searching vector index: {str(e)}")
    
    def _search_bm25_index(self, indexer: Indexer, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search BM25 index"""
        
        try:
            import pickle
            from rank_bm25 import BM25Okapi
        except ImportError:
            raise ImportError("rank_bm25 is required for BM25 search")
        
        try:
            # Load BM25 model
            bm25_key = f"indexes/{indexer.id}/bm25_model.pkl"
            model_data = self.minio_service.download_file(bm25_key)
            
            with tempfile.NamedTemporaryFile(suffix=".pkl") as temp_file:
                temp_file.write(model_data.read())
                temp_file.seek(0)
                bm25 = pickle.load(temp_file)
            
            # Load index data
            index_key = f"indexes/{indexer.id}/bm25_index.json"
            file_data = self.minio_service.download_file(index_key)
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix=".json") as temp_file:
                temp_file.write(file_data.read().decode('utf-8'))
                temp_file.seek(0)
                index_data = json.load(temp_file)
            
            # Tokenize query
            tokenized_query = query.lower().split()
            
            # Get BM25 scores
            scores = bm25.get_scores(tokenized_query)
            
            # Get top_k results
            doc_ids = index_data["doc_ids"]
            contents = index_data["contents"]
            
            # Create results with scores
            results = []
            for i, (doc_id, content, score) in enumerate(zip(doc_ids, contents, scores)):
                results.append({
                    "doc_id": doc_id,
                    "content": content,
                    "score": float(score),
                    "rank": i + 1
                })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching BM25 index: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error searching BM25 index: {str(e)}") 