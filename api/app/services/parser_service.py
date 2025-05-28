import logging
import tempfile
import os
import pandas as pd
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.parser import Parser, ParserStatus
from app.models.file import File
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.services.minio_service import MinIOService

from autorag.data.parse.langchain_parse import langchain_parse
from autorag.data.parse.clova import clova_ocr

logger = logging.getLogger(__name__)

class ParserService:
    """Service for handling document parsing operations"""
    
    def __init__(self):
        self.minio_service = MinIOService()
    
    def get_parser_by_id(self, session: Session, parser_id: UUID) -> Optional[Parser]:
        """Get parser by ID"""
        statement = select(Parser).where(Parser.id == parser_id)
        return session.exec(statement).first()
    
    def get_active_parsers(self, session: Session) -> List[Parser]:
        """Get all active parsers"""
        statement = select(Parser).where(Parser.status == ParserStatus.ACTIVE)
        return session.exec(statement).all()
    
    def create_parser(
        self, 
        session: Session,
        name: str,
        module_type: str,
        supported_mime: List[str],
        params: Dict[str, Any]
    ) -> Parser:
        """Create a new parser configuration"""
        parser = Parser(
            name=name,
            module_type=module_type,
            supported_mime=supported_mime,
            params=params,
            status=ParserStatus.ACTIVE
        )
        session.add(parser)
        session.commit()
        session.refresh(parser)
        return parser
    
    def parse_files(
        self,
        session: Session,
        file_ids: List[UUID],
        parser_id: UUID
    ) -> List[FileParseResult]:
        """Parse multiple files using specified parser"""
        
        # Get parser configuration
        parser = self.get_parser_by_id(session, parser_id)
        if not parser:
            raise HTTPException(status_code=404, detail="Parser not found")
        
        # Get files
        files = []
        for file_id in file_ids:
            file = session.get(File, file_id)
            if file:
                files.append(file)
        
        if len(files) != len(file_ids):
            raise HTTPException(status_code=404, detail="Some files not found")
        
        results = []
        for file in files:
            try:
                result = self._parse_single_file(session, file, parser)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to parse file {file.id}: {str(e)}")
                # Create failed result record
                result = self._create_failed_parse_result(session, file, parser, str(e))
                results.append(result)
        
        return results
    
    def _parse_single_file(
        self,
        session: Session,
        file: File,
        parser: Parser
    ) -> FileParseResult:
        """Parse a single file"""
        
        # Check if file type is supported
        if file.mime_type not in parser.supported_mime:
            raise ValueError(f"File type {file.mime_type} not supported by parser {parser.name}")
        
        # Create parse result record
        parse_result = FileParseResult(
            file_id=file.id,
            parser_id=parser.id,
            bucket="rag-parsed-files",
            object_key=f"parsed/{file.id}/{parser.name}.parquet",
            status=ParseStatus.PENDING
        )
        session.add(parse_result)
        session.commit()
        session.refresh(parse_result)
        
        try:
            # Download file from MinIO to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.file_name}") as temp_file:
                file_data = self.minio_service.download_file(file.object_key)
                temp_file.write(file_data.read())
                temp_file_path = temp_file.name
            
            try:
                # Parse the file using autorag
                parsed_data = self._run_autorag_parser(
                    temp_file_path,
                    file.mime_type,
                    parser.module_type,
                    parser.params
                )
                
                # Convert to DataFrame and save to MinIO
                df = pd.DataFrame(parsed_data)
                
                # Save parsed result to MinIO
                with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_parquet:
                    df.to_parquet(temp_parquet.name, index=False)
                    temp_parquet.seek(0)
                    
                    # Upload to MinIO
                    self.minio_service.client.put_object(
                        bucket_name=parse_result.bucket,
                        object_name=parse_result.object_key,
                        data=temp_parquet,
                        length=os.path.getsize(temp_parquet.name),
                        content_type="application/octet-stream"
                    )
                
                # Update parse result status
                parse_result.status = ParseStatus.SUCCESS
                parse_result.parsed_at = datetime.utcnow()
                parse_result.extra_meta = {
                    "num_texts": len(parsed_data.get("texts", [])),
                    "parser_params": parser.params
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error parsing file {file.id}: {str(e)}")
            parse_result.status = ParseStatus.FAILED
            parse_result.error_message = str(e)
        
        session.add(parse_result)
        session.commit()
        session.refresh(parse_result)
        
        return parse_result
    
    def _run_autorag_parser(
        self,
        file_path: str,
        mime_type: str,
        module_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, List]:
        """Run autorag parser on a file"""
        
        # Map mime type to file type
        file_type_map = {
            "application/pdf": "pdf",
            "text/csv": "csv",
            "application/json": "json",
            "text/markdown": "md",
            "text/html": "html",
            "application/xml": "xml",
            "text/xml": "xml"
        }
        
        file_type = file_type_map.get(mime_type, "all_files")
        
        # Create data path glob pattern
        data_path_glob = file_path
        
        if module_type == "langchain":
            # Use langchain parser
            parse_method = params.get("parse_method", "pymupdf")
            parser_params = {k: v for k, v in params.items() if k != "parse_method"}
            
            result = langchain_parse(
                data_path_glob=data_path_glob,
                file_type=file_type,
                parse_method=parse_method,
                **parser_params
            )
            
        elif module_type == "clova_ocr":
            # Use Clova OCR
            result = clova_ocr(
                data_path_glob=data_path_glob,
                file_type=file_type,
                **params
            )
            
        else:
            raise ValueError(f"Unsupported module_type: {module_type}. Supported types: langchain, clova_ocr")
        
        # Convert result to dictionary format
        if isinstance(result, pd.DataFrame):
            return result.to_dict('list')
        else:
            # Assume result is a tuple (texts, paths, pages, last_modified_datetime)
            return {
                "texts": result[0],
                "path": result[1], 
                "page": result[2],
                "last_modified_datetime": result[3] if len(result) > 3 else [None] * len(result[0])
            }
    
    def _create_failed_parse_result(
        self,
        session: Session,
        file: File,
        parser: Parser,
        error_message: str
    ) -> FileParseResult:
        """Create a failed parse result record"""
        
        parse_result = FileParseResult(
            file_id=file.id,
            parser_id=parser.id,
            bucket="rag-parsed-files",
            object_key=f"parsed/{file.id}/{parser.name}.parquet",
            status=ParseStatus.FAILED,
            error_message=error_message
        )
        session.add(parse_result)
        session.commit()
        session.refresh(parse_result)
        
        return parse_result
    
    def get_parse_results(
        self,
        session: Session,
        file_id: Optional[UUID] = None,
        parser_id: Optional[UUID] = None,
        status: Optional[ParseStatus] = None
    ) -> List[FileParseResult]:
        """Get parse results with optional filters"""
        
        statement = select(FileParseResult)
        
        if file_id:
            statement = statement.where(FileParseResult.file_id == file_id)
        if parser_id:
            statement = statement.where(FileParseResult.parser_id == parser_id)
        if status:
            statement = statement.where(FileParseResult.status == status)
            
        return session.exec(statement).all()
    
    def get_parsed_data(
        self,
        session: Session,
        parse_result_id: int
    ) -> pd.DataFrame:
        """Get parsed data from MinIO"""
        
        parse_result = session.get(FileParseResult, parse_result_id)
        if not parse_result:
            raise HTTPException(status_code=404, detail="Parse result not found")
        
        if parse_result.status != ParseStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Parse result is not successful")
        
        # Download parquet file from MinIO
        file_data = self.minio_service.download_file(parse_result.object_key)
        
        # Load as DataFrame
        with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
            temp_file.write(file_data.read())
            temp_file.seek(0)
            df = pd.read_parquet(temp_file.name)
        
        return df 