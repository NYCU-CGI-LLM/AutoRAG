import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.retriever import Retriever, RetrieverStatus
from app.models.library import Library
from app.models.parser import Parser, ParserStatus
from app.models.chunker import Chunker, ChunkerStatus
from app.models.indexer import Indexer, IndexerStatus
from app.models.file import File, FileStatus
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus

from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
from app.services.index_service import IndexService

logger = logging.getLogger(__name__)

class RetrieverService:
    """
    Service for managing retriever configurations and coordinating
    the complete parse -> chunk -> index pipeline
    """
    
    def __init__(self):
        self.parser_service = ParserService()
        self.chunker_service = ChunkerService()
        self.index_service = IndexService()
    
    def get_retriever_by_id(self, session: Session, retriever_id: UUID) -> Optional[Retriever]:
        """Get retriever by ID"""
        return session.get(Retriever, retriever_id)
    
    def get_active_retrievers(self, session: Session) -> List[Retriever]:
        """Get all active retrievers"""
        statement = select(Retriever).where(Retriever.status != RetrieverStatus.DEPRECATED)
        return session.exec(statement).all()
    
    def get_retrievers_by_library(self, session: Session, library_id: UUID) -> List[Retriever]:
        """Get all retrievers for a specific library"""
        statement = select(Retriever).where(Retriever.library_id == library_id)
        return session.exec(statement).all()
    
    def create_retriever(
        self,
        session: Session,
        name: str,
        library_id: UUID,
        parser_id: UUID,
        chunker_id: UUID,
        indexer_id: UUID,
        description: Optional[str] = None,
        top_k: int = 10,
        params: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> Retriever:
        """
        Create a new retriever configuration
        """
        try:
            # Validate all dependencies exist
            library = session.get(Library, library_id)
            if not library:
                raise HTTPException(status_code=404, detail="Library not found")
            
            parser = session.get(Parser, parser_id)
            if not parser or parser.status != ParserStatus.ACTIVE:
                raise HTTPException(status_code=404, detail="Parser not found or inactive")
            
            chunker = session.get(Chunker, chunker_id)
            if not chunker or chunker.status != ChunkerStatus.ACTIVE:
                raise HTTPException(status_code=404, detail="Chunker not found or inactive")
            
            indexer = session.get(Indexer, indexer_id)
            if not indexer or indexer.status != IndexerStatus.ACTIVE:
                raise HTTPException(status_code=404, detail="Indexer not found or inactive")
            
            # Check if this exact combination already exists
            statement = select(Retriever).where(
                Retriever.library_id == library_id,
                Retriever.parser_id == parser_id,
                Retriever.chunker_id == chunker_id,
                Retriever.indexer_id == indexer_id
            )
            existing_combination = session.exec(statement).first()
            if existing_combination:
                raise HTTPException(
                    status_code=409,
                    detail=f"Retriever with this exact configuration already exists: {existing_combination.name}"
                )
            
            # Generate collection name if not provided
            if not collection_name:
                collection_name = f"retriever_{name.lower().replace(' ', '_').replace('-', '_')}"
            
            # Create storage path
            storage_path = f"retrievers/{library_id}/{uuid4()}"
            
            retriever = Retriever(
                name=name,
                description=description,
                library_id=library_id,
                parser_id=parser_id,
                chunker_id=chunker_id,
                indexer_id=indexer_id,
                top_k=top_k,
                params=params or {},
                storage_path=storage_path,
                collection_name=collection_name,
                status=RetrieverStatus.PENDING
            )
            
            session.add(retriever)
            session.commit()
            session.refresh(retriever)
            
            logger.info(f"Created retriever: {name} (ID: {retriever.id})")
            return retriever
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating retriever: {e}")
            raise HTTPException(status_code=500, detail="Failed to create retriever")
    
    async def build_retriever(
        self,
        session: Session,
        retriever_id: UUID,
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Build a retriever by executing the complete pipeline:
        1. Parse files in the library
        2. Chunk the parsed results
        3. Create vector index
        """
        try:
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            if retriever.status == RetrieverStatus.BUILDING:
                raise HTTPException(
                    status_code=409,
                    detail="Retriever is already being built"
                )
            
            if retriever.status == RetrieverStatus.ACTIVE and not force_rebuild:
                raise HTTPException(
                    status_code=409,
                    detail="Retriever is already active. Use force_rebuild=True to rebuild."
                )
            
            # Update status to building
            retriever.status = RetrieverStatus.BUILDING
            retriever.error_message = None
            session.add(retriever)
            session.commit()
            
            logger.info(f"Starting retriever build for {retriever.name} (ID: {retriever_id})")
            
            try:
                # Step 1: Parse files in the library
                parse_results = await self._parse_library_files(session, retriever)
                logger.info(f"Parsed {len(parse_results)} files")
                
                # Step 2: Chunk parsed results
                chunk_results = await self._chunk_parse_results(session, retriever, parse_results)
                logger.info(f"Created {len(chunk_results)} chunk results")
                
                # Step 3: Create vector index
                chunk_result_ids = [cr.id for cr in chunk_results if cr.status == ChunkStatus.SUCCESS]
                if not chunk_result_ids:
                    raise Exception("No successful chunk results available for indexing")
                
                index_result = await self.index_service.create_qdrant_index_for_retriever(
                    session=session,
                    retriever_id=retriever_id,
                    chunk_result_ids=chunk_result_ids,
                    metadata_config={
                        "retriever_name": retriever.name,
                        "library_id": str(retriever.library_id),
                        "build_timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                # Retriever status is updated by index_service.create_qdrant_index_for_retriever
                session.refresh(retriever)
                
                logger.info(f"Successfully built retriever {retriever.name}")
                
                return {
                    "retriever_id": str(retriever_id),
                    "status": "success",
                    "parse_results": len(parse_results),
                    "chunk_results": len(chunk_results),
                    "successful_chunks": len(chunk_result_ids),
                    "index_result": index_result,
                    "collection_name": retriever.collection_name,
                    "total_chunks": retriever.total_chunks
                }
                
            except Exception as e:
                # Update retriever status to failed
                retriever.status = RetrieverStatus.FAILED
                retriever.error_message = str(e)
                session.add(retriever)
                session.commit()
                
                logger.error(f"Failed to build retriever {retriever_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to build retriever: {str(e)}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error building retriever {retriever_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    async def _parse_library_files(
        self,
        session: Session,
        retriever: Retriever
    ) -> List[FileParseResult]:
        """Parse all files in the library using the specified parser"""
        
        # Get all active files in the library
        files_statement = select(File).where(
            File.library_id == retriever.library_id,
            File.status == FileStatus.ACTIVE
        )
        files = session.exec(files_statement).all()
        
        if not files:
            raise Exception(f"No active files found in library {retriever.library_id}")
        
        file_ids = [file.id for file in files]
        logger.info(f"Parsing {len(file_ids)} files with parser {retriever.parser_id}")
        
        # Parse files using parser service
        parse_results = self.parser_service.parse_files(
            session=session,
            file_ids=file_ids,
            parser_id=retriever.parser_id
        )
        
        return parse_results
    
    async def _chunk_parse_results(
        self,
        session: Session,
        retriever: Retriever,
        parse_results: List[FileParseResult]
    ) -> List[FileChunkResult]:
        """Chunk all successful parse results using the specified chunker"""
        
        # Filter successful parse results
        successful_parse_results = [
            pr for pr in parse_results 
            if pr.status == ParseStatus.SUCCESS
        ]
        
        if not successful_parse_results:
            raise Exception("No successful parse results available for chunking")
        
        parse_result_ids = [pr.id for pr in successful_parse_results]
        logger.info(f"Chunking {len(parse_result_ids)} parse results with chunker {retriever.chunker_id}")
        
        # Chunk parse results using chunker service
        chunk_results = self.chunker_service.chunk_parsed_results(
            session=session,
            parse_result_ids=parse_result_ids,
            chunker_id=retriever.chunker_id
        )
        
        return chunk_results
    
    async def query_retriever(
        self,
        session: Session,
        retriever_id: UUID,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query a retriever and return search results
        """
        try:
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            if retriever.status != RetrieverStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Retriever is not active. Current status: {retriever.status.value}"
                )
            
            if not retriever.collection_name:
                raise HTTPException(
                    status_code=400,
                    detail="Retriever has no collection name"
                )
            
            # Use retriever's top_k if not specified
            top_k = top_k or retriever.top_k
            
            # Get indexer configuration
            indexer = session.get(Indexer, retriever.indexer_id)
            if not indexer:
                raise HTTPException(status_code=404, detail="Indexer configuration not found")
            
            # Query the collection
            results = await self.index_service.search_qdrant_collection(
                collection_name=retriever.collection_name,
                query=query,
                top_k=top_k,
                embedding_model=indexer.model,
                qdrant_config=indexer.params,
                filters=filters
            )
            
            # Add retriever context to results
            for result in results:
                result["retriever_id"] = str(retriever_id)
                result["retriever_name"] = retriever.name
                result["library_id"] = str(retriever.library_id)
            
            logger.info(f"Query '{query}' on retriever {retriever.name} returned {len(results)} results")
            return results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to query retriever {retriever_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    def get_retriever_stats(
        self,
        session: Session,
        retriever_id: UUID
    ) -> Dict[str, Any]:
        """Get detailed statistics for a retriever"""
        
        try:
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            # Get related entities
            library = session.get(Library, retriever.library_id)
            parser = session.get(Parser, retriever.parser_id)
            chunker = session.get(Chunker, retriever.chunker_id)
            indexer = session.get(Indexer, retriever.indexer_id)
            
            # Count files in library
            files_count = session.exec(
                select(File).where(
                    File.library_id == retriever.library_id,
                    File.status == FileStatus.ACTIVE
                )
            ).all()
            
            # Count parse results
            parse_results = session.exec(
                select(FileParseResult).where(
                    FileParseResult.parser_id == retriever.parser_id,
                    FileParseResult.file_id.in_([f.id for f in files_count])
                )
            ).all()
            
            # Count chunk results
            chunk_results = session.exec(
                select(FileChunkResult).where(
                    FileChunkResult.chunker_id == retriever.chunker_id,
                    FileChunkResult.file_parse_result_id.in_([pr.id for pr in parse_results])
                )
            ).all()
            
            stats = {
                "retriever_id": str(retriever.id),
                "name": retriever.name,
                "status": retriever.status.value,
                "collection_name": retriever.collection_name,
                "indexed_at": retriever.indexed_at.isoformat() if retriever.indexed_at else None,
                "total_chunks": retriever.total_chunks,
                "error_message": retriever.error_message,
                
                # Configuration
                "configuration": {
                    "library": {
                        "id": str(library.id),
                        "name": library.library_name
                    } if library else None,
                    "parser": {
                        "id": str(parser.id),
                        "name": parser.name,
                        "module_type": parser.module_type
                    } if parser else None,
                    "chunker": {
                        "id": str(chunker.id),
                        "name": chunker.name,
                        "chunk_method": chunker.chunk_method,
                        "chunk_size": chunker.chunk_size
                    } if chunker else None,
                    "indexer": {
                        "id": str(indexer.id),
                        "name": indexer.name,
                        "index_type": indexer.index_type,
                        "model": indexer.model
                    } if indexer else None
                },
                
                # Pipeline statistics
                "pipeline_stats": {
                    "total_files": len(files_count),
                    "parse_results": {
                        "total": len(parse_results),
                        "successful": len([pr for pr in parse_results if pr.status == ParseStatus.SUCCESS]),
                        "failed": len([pr for pr in parse_results if pr.status == ParseStatus.FAILED])
                    },
                    "chunk_results": {
                        "total": len(chunk_results),
                        "successful": len([cr for cr in chunk_results if cr.status == ChunkStatus.SUCCESS]),
                        "failed": len([cr for cr in chunk_results if cr.status == ChunkStatus.FAILED])
                    }
                },
                
                # Additional metadata
                "extra_meta": retriever.extra_meta
            }
            
            return stats
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get retriever stats for {retriever_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    def update_retriever_status(
        self,
        session: Session,
        retriever_id: UUID,
        status: RetrieverStatus,
        error_message: Optional[str] = None
    ) -> Retriever:
        """Update retriever status"""
        
        try:
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            retriever.status = status
            if error_message is not None:
                retriever.error_message = error_message
            
            session.add(retriever)
            session.commit()
            session.refresh(retriever)
            
            logger.info(f"Updated retriever {retriever_id} status to {status.value}")
            return retriever
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update retriever status: {e}")
            raise HTTPException(status_code=500, detail="Failed to update status")
    
    def delete_retriever(
        self,
        session: Session,
        retriever_id: UUID,
        delete_collection: bool = True
    ) -> bool:
        """
        Delete a retriever and optionally its Qdrant collection
        """
        try:
            retriever = session.get(Retriever, retriever_id)
            if not retriever:
                raise HTTPException(status_code=404, detail="Retriever not found")
            
            # Delete Qdrant collection if requested and exists
            if delete_collection and retriever.collection_name:
                try:
                    # We'd need to implement collection deletion in IndexService
                    logger.info(f"Would delete Qdrant collection: {retriever.collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete Qdrant collection: {e}")
            
            # Delete retriever from database
            session.delete(retriever)
            session.commit()
            
            logger.info(f"Deleted retriever {retriever_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete retriever {retriever_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete retriever") 