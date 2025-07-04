import logging
import os
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings

from sqlmodel import Session, select
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class VectorDBService:
    """
    Simplified VectorDB service using ChromaDB
    
    Architecture:
    - ChromaDB: Store embeddings + metadata + documents
    - PostgreSQL: Store collection metadata and statistics
    """
    
    def __init__(self, chroma_path: str = "./resources/chroma"):
        self.chroma_path = chroma_path
        self.client = self._init_chroma_client()
        
    def _init_chroma_client(self):
        """Initialize ChromaDB client"""
        try:
            # Ensure directory exists
            os.makedirs(self.chroma_path, exist_ok=True)
            
            # Create persistent client
            client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info(f"ChromaDB client initialized at {self.chroma_path}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise HTTPException(status_code=500, detail=f"VectorDB initialization failed: {str(e)}")
    
    def store_embeddings(
        self,
        library_id: UUID,
        doc_ids: List[str],
        contents: List[str],
        embedding_model: str = "openai_embed_3_large",
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Store embeddings in ChromaDB
        
        Args:
            library_id: Library UUID
            doc_ids: Document IDs
            contents: Document contents
            embedding_model: Embedding model name
            metadata_list: Optional metadata for each document
            
        Returns:
            Storage result metadata
        """
        try:
            # 1. Generate collection name
            collection_name = f"lib_{str(library_id).replace('-', '_')}_{embedding_model}"
            
            # 2. Get or create collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "library_id": str(library_id),
                    "embedding_model": embedding_model,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # 3. Prepare metadata
            metadatas = []
            for i, (doc_id, content) in enumerate(zip(doc_ids, contents)):
                base_metadata = {
                    "doc_id": doc_id,
                    "library_id": str(library_id),
                    "chunk_index": i,
                    "embedding_model": embedding_model,
                    "created_at": datetime.utcnow().isoformat(),
                    "content_preview": content[:100] + "..." if len(content) > 100 else content
                }
                
                # Merge with provided metadata
                if metadata_list and i < len(metadata_list):
                    base_metadata.update(metadata_list[i])
                
                metadatas.append(base_metadata)
            
            # 4. Add to ChromaDB (automatically generates embeddings)
            collection.add(
                ids=doc_ids,
                documents=contents,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully stored {len(doc_ids)} documents in collection {collection_name}")
            
            return {
                "collection_name": collection_name,
                "total_documents": len(doc_ids),
                "embedding_model": embedding_model,
                "library_id": str(library_id),
                "vector_dimension": self._get_vector_dimension(collection),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {str(e)}")
    
    def similarity_search(
        self,
        library_id: UUID,
        query: str,
        top_k: int = 10,
        embedding_model: str = "openai_embed_3_large",
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search in ChromaDB
        
        Args:
            library_id: Library UUID
            query: Search query
            top_k: Number of results to return
            embedding_model: Embedding model name
            filters: Additional filters for metadata
            
        Returns:
            List of search results
        """
        try:
            # 1. Build collection name
            collection_name = f"lib_{str(library_id).replace('-', '_')}_{embedding_model}"
            
            # 2. Get collection
            try:
                collection = self.client.get_collection(collection_name)
            except Exception:
                logger.warning(f"Collection {collection_name} not found")
                return []
            
            # 3. Build query filters - use simple dict for ChromaDB compatibility
            where_filter = {"library_id": str(library_id)}
            if filters:
                # Only add simple key-value filters that ChromaDB supports
                for key, value in filters.items():
                    if isinstance(value, (str, int, float, bool)):
                        where_filter[key] = str(value)  # Convert to string for ChromaDB compatibility
            
            # 4. Execute search - handle potential type issues by using Any
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k, 100),  # Limit to prevent excessive results
                    where=where_filter,  # type: ignore
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as e:
                logger.error(f"ChromaDB query failed: {str(e)}")
                return []
            
            # 5. Format results - safely access nested data
            search_results = []
            if not results:
                return search_results
                
            ids = results.get("ids", [])
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            distances = results.get("distances", [])
            
            if ids and len(ids) > 0 and len(ids[0]) > 0:
                for i in range(len(ids[0])):
                    search_results.append({
                        "doc_id": ids[0][i],
                        "content": documents[0][i] if documents and len(documents) > 0 and len(documents[0]) > i else "",
                        "metadata": metadatas[0][i] if metadatas and len(metadatas) > 0 and len(metadatas[0]) > i else {},
                        "score": 1 - distances[0][i] if distances and len(distances) > 0 and len(distances[0]) > i else 0.0,
                        "rank": i + 1
                    })
            
            logger.info(f"Similarity search returned {len(search_results)} results for library {library_id}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    def get_collection_stats(self, library_id: UUID, embedding_model: str = "openai_embed_3_large") -> Dict[str, Any]:
        """Get statistics for a collection"""
        try:
            collection_name = f"lib_{str(library_id).replace('-', '_')}_{embedding_model}"
            
            try:
                collection = self.client.get_collection(collection_name)
                count = collection.count()
                
                return {
                    "collection_name": collection_name,
                    "library_id": str(library_id),
                    "embedding_model": embedding_model,
                    "total_documents": count,
                    "vector_dimension": self._get_vector_dimension(collection),
                    "status": "active"
                }
            except Exception:
                return {
                    "collection_name": collection_name,
                    "library_id": str(library_id),
                    "embedding_model": embedding_model,
                    "total_documents": 0,
                    "status": "not_found"
                }
                
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    def delete_collection(self, library_id: UUID, embedding_model: str = "openai_embed_3_large") -> Dict[str, Any]:
        """Delete a collection and all its data"""
        try:
            collection_name = f"lib_{str(library_id).replace('-', '_')}_{embedding_model}"
            
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"Successfully deleted collection {collection_name}")
                return {
                    "collection_name": collection_name,
                    "library_id": str(library_id),
                    "status": "deleted"
                }
            except Exception:
                logger.warning(f"Collection {collection_name} not found for deletion")
                return {
                    "collection_name": collection_name,
                    "library_id": str(library_id),
                    "status": "not_found"
                }
                
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections in ChromaDB"""
        try:
            collections = self.client.list_collections()
            
            result = []
            for collection in collections:
                # Parse collection name to extract library_id and embedding_model
                name_parts = collection.name.split('_')
                if len(name_parts) >= 6 and name_parts[0] == 'lib':
                    # Format: lib_{uuid_part1}_{uuid_part2}_{uuid_part3}_{uuid_part4}_{embedding_model}
                    library_id_parts = name_parts[1:5]
                    embedding_model = '_'.join(name_parts[5:])
                    library_id = '-'.join(library_id_parts)
                    
                    result.append({
                        "collection_name": collection.name,
                        "library_id": library_id,
                        "embedding_model": embedding_model,
                        "total_documents": collection.count(),
                        "metadata": collection.metadata
                    })
                else:
                    # Handle collections with different naming patterns
                    result.append({
                        "collection_name": collection.name,
                        "library_id": "unknown",
                        "embedding_model": "unknown",
                        "total_documents": collection.count(),
                        "metadata": collection.metadata
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")
    
    def _get_vector_dimension(self, collection) -> int:
        """Get vector dimension from collection"""
        try:
            # Try to get a sample document to determine dimension
            sample = collection.peek(limit=1)
            if sample and sample.get("embeddings") and len(sample["embeddings"]) > 0:
                return len(sample["embeddings"][0])
            return 0
        except Exception:
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Check VectorDB service health"""
        try:
            # Test basic operations
            collections = self.client.list_collections()
            
            return {
                "status": "healthy",
                "chroma_path": self.chroma_path,
                "total_collections": len(collections),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"VectorDB health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            } 