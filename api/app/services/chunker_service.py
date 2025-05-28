import logging
import tempfile
import os
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.chunker import Chunker, ChunkerStatus
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.services.minio_service import MinIOService


from autorag.data.chunk.langchain_chunk import langchain_chunk
from autorag.data.chunk.llama_index_chunk import llama_index_chunk

logger = logging.getLogger(__name__)

class ChunkerService:
    """Service for handling document chunking operations"""
    
    def __init__(self):
        self.minio_service = MinIOService()
    
    def get_chunker_by_id(self, session: Session, chunker_id: UUID) -> Optional[Chunker]:
        """Get chunker by ID"""
        statement = select(Chunker).where(Chunker.id == chunker_id)
        return session.exec(statement).first()
    
    def get_active_chunkers(self, session: Session) -> List[Chunker]:
        """Get all active chunkers"""
        statement = select(Chunker).where(Chunker.status == ChunkerStatus.ACTIVE)
        return list(session.exec(statement).all())
    
    def create_chunker(
        self,
        session: Session,
        name: str,
        module_type: str,
        chunk_method: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Chunker:
        """Create a new chunker configuration"""
        chunker = Chunker(
            name=name,
            module_type=module_type,
            chunk_method=chunk_method,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            params=params or {},
            status=ChunkerStatus.ACTIVE
        )
        session.add(chunker)
        session.commit()
        session.refresh(chunker)
        return chunker
    
    def chunk_parsed_results(
        self,
        session: Session,
        parse_result_ids: List[UUID],
        chunker_id: UUID
    ) -> List[FileChunkResult]:
        """Chunk multiple parsed results using specified chunker"""
        
        # Get chunker configuration
        chunker = self.get_chunker_by_id(session, chunker_id)
        if not chunker:
            raise HTTPException(status_code=404, detail="Chunker not found")
        
        # Get parse results
        parse_results = []
        for parse_result_id in parse_result_ids:
            parse_result = session.get(FileParseResult, parse_result_id)
            if parse_result:
                parse_results.append(parse_result)
        
        if len(parse_results) != len(parse_result_ids):
            raise HTTPException(status_code=404, detail="Some parse results not found")
        
        # Check all parse results are successful
        failed_results = [pr for pr in parse_results if pr.status != ParseStatus.SUCCESS]
        if failed_results:
            raise HTTPException(
                status_code=400, 
                detail=f"Parse results {[pr.id for pr in failed_results]} are not successful"
            )
        
        results = []
        for parse_result in parse_results:
            try:
                result = self._chunk_single_parse_result(session, parse_result, chunker)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to chunk parse result {parse_result.id}: {str(e)}")
                # Create failed result record
                result = self._create_failed_chunk_result(session, parse_result, chunker, str(e))
                results.append(result)
        
        return results
    
    def _chunk_single_parse_result(
        self,
        session: Session,
        parse_result: FileParseResult,
        chunker: Chunker
    ) -> FileChunkResult:
        """Chunk a single parse result"""
        
        if chunker.id is None:
            raise ValueError("Chunker ID cannot be None")
        
        # Check if chunk result already exists
        existing_result = session.exec(
            select(FileChunkResult).where(
                FileChunkResult.file_parse_result_id == parse_result.id,
                FileChunkResult.chunker_id == chunker.id
            )
        ).first()
        
        if existing_result:
            if existing_result.status == ChunkStatus.SUCCESS:
                logger.info(f"Chunk result already exists and is successful for parse result {parse_result.id}")
                return existing_result
            else:
                # Delete failed/pending result and retry
                logger.info(f"Deleting existing failed/pending chunk result {existing_result.id}")
                session.delete(existing_result)
                session.commit()
        
        # Create chunk result record
        chunk_result = FileChunkResult(
            file_id=parse_result.file_id,
            file_parse_result_id=parse_result.id,
            chunker_id=chunker.id,
            bucket="rag-chunked-files",
            object_key=f"chunked/{parse_result.file_id}/{parse_result.id}/{chunker.name}.parquet",
            status=ChunkStatus.PENDING,
            chunked_at=None,
            error_message=None
        )
        session.add(chunk_result)
        session.commit()
        session.refresh(chunk_result)
        
        try:
            # Download parsed data from MinIO
            parsed_data = self._get_parsed_data(parse_result)
            
            # Run chunking using autorag
            chunked_data = self._run_autorag_chunker(
                parsed_data,
                chunker.module_type,
                chunker.chunk_method,
                chunker.params
            )
            
            # Convert to DataFrame and save to MinIO
            df = pd.DataFrame(chunked_data)
            
            # Save chunked result to MinIO
            with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_parquet:
                df.to_parquet(temp_parquet.name, index=False)
                
                # Upload to MinIO
                with open(temp_parquet.name, 'rb') as file_data:
                    self.minio_service.client.put_object(
                        bucket_name=chunk_result.bucket,
                        object_name=chunk_result.object_key,
                        data=file_data,
                        length=os.path.getsize(temp_parquet.name),
                        content_type="application/octet-stream"
                    )
            
            # Update chunk result status
            chunk_result.status = ChunkStatus.SUCCESS
            chunk_result.chunked_at = datetime.utcnow()
            chunk_result.extra_meta = {
                "num_chunks": len(chunked_data.get("doc_id", [])),
                "chunker_params": chunker.params,
                "chunk_method": chunker.chunk_method,
                "chunk_size": chunker.chunk_size,
                "chunk_overlap": chunker.chunk_overlap
            }
            
        except Exception as e:
            logger.error(f"Error chunking parse result {parse_result.id}: {str(e)}")
            chunk_result.status = ChunkStatus.FAILED
            chunk_result.error_message = str(e)
        
        session.add(chunk_result)
        session.commit()
        session.refresh(chunk_result)
        
        return chunk_result
    
    def _get_parsed_data(self, parse_result: FileParseResult) -> pd.DataFrame:
        """Get parsed data from MinIO"""
        
        # Download parquet file from MinIO using the correct bucket and object_key from parse_result
        file_data = self.minio_service.client.get_object(parse_result.bucket, parse_result.object_key)
        
        # Load as DataFrame
        with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
            temp_file.write(file_data.read())
            temp_file.seek(0)
            df = pd.read_parquet(temp_file.name)
        
        return df
    
    def _run_autorag_chunker(
        self,
        parsed_data: pd.DataFrame,
        module_type: str,
        chunk_method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run autorag chunker on parsed data"""
        
        def _run_chunker_in_thread():
            """Run chunker in a separate thread to avoid event loop conflicts"""
            # Prepare chunker parameters
            chunker_params = params.copy()
            
            if module_type == "langchain_chunk":
                # Use langchain chunker
                result = langchain_chunk(
                    parsed_data,
                    chunk_method,
                    **chunker_params
                )
                
            elif module_type == "llama_index_chunk":
                # Use llama_index chunker  
                result = llama_index_chunk(
                    parsed_data,
                    chunk_method,
                    **chunker_params
                )
                
            else:
                raise ValueError(f"Unsupported module_type: {module_type}")
            
            return result
        
        # Run chunker in a separate thread to avoid event loop conflicts
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_chunker_in_thread)
            result = future.result()
        
        # Convert result to dictionary format
        if isinstance(result, pd.DataFrame):
            # Convert DataFrame to dict with string keys
            result_dict = {}
            for key, value in result.to_dict('list').items():
                result_dict[str(key)] = value
            return result_dict
        else:
            # Assume result is a tuple (doc_id, contents, path, start_end_idx, metadata)
            return {
                "doc_id": result[0],
                "contents": result[1],
                "path": result[2],
                "start_end_idx": result[3],
                "metadata": result[4]
            }
    
    def _create_failed_chunk_result(
        self,
        session: Session,
        parse_result: FileParseResult,
        chunker: Chunker,
        error_message: str
    ) -> FileChunkResult:
        """Create a failed chunk result record"""
        
        if chunker.id is None:
            raise ValueError("Chunker ID cannot be None")
        
        chunk_result = FileChunkResult(
            file_id=parse_result.file_id,
            file_parse_result_id=parse_result.id,
            chunker_id=chunker.id,
            bucket="rag-chunked-files",
            object_key=f"chunked/{parse_result.file_id}/{parse_result.id}/{chunker.name}.parquet",
            status=ChunkStatus.FAILED,
            chunked_at=None,
            error_message=error_message
        )
        session.add(chunk_result)
        session.commit()
        session.refresh(chunk_result)
        
        return chunk_result
    
    def get_chunk_results(
        self,
        session: Session,
        file_id: Optional[UUID] = None,
        parse_result_id: Optional[int] = None,
        chunker_id: Optional[UUID] = None,
        status: Optional[ChunkStatus] = None
    ) -> List[FileChunkResult]:
        """Get chunk results with optional filters"""
        
        statement = select(FileChunkResult)
        
        if file_id:
            statement = statement.where(FileChunkResult.file_id == file_id)
        if parse_result_id:
            statement = statement.where(FileChunkResult.file_parse_result_id == parse_result_id)
        if chunker_id:
            statement = statement.where(FileChunkResult.chunker_id == chunker_id)
        if status:
            statement = statement.where(FileChunkResult.status == status)
            
        return list(session.exec(statement).all())
    
    def get_chunked_data(
        self,
        session: Session,
        chunk_result_id: UUID
    ) -> pd.DataFrame:
        """Get chunked data from MinIO"""
        
        chunk_result = session.get(FileChunkResult, chunk_result_id)
        if not chunk_result:
            raise HTTPException(status_code=404, detail="Chunk result not found")
        
        if chunk_result.status != ChunkStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Chunk result is not successful")
        
        # Download parquet file from MinIO
        file_data = self.minio_service.download_file(chunk_result.object_key)
        
        # Load as DataFrame
        with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
            temp_file.write(file_data.read())
            temp_file.seek(0)
            df = pd.read_parquet(temp_file.name)
        
        return df 