#!/usr/bin/env python3
"""
CLI Test Script for Parser Service

Usage:
    python test_parser_service.py --help
    python test_parser_service.py create-parser --name "pdf_parser" --module-type "langchain" --mime-types "application/pdf" --params '{"parse_method": "pymupdf"}'
    python test_parser_service.py list-parsers
    python test_parser_service.py upload-file --library-id <uuid> --file-path "/path/to/file.pdf"
    python test_parser_service.py parse-file --file-id <uuid> --parser-id <uuid>
    python test_parser_service.py get-results --parser-id <uuid>
"""

import argparse
import json
import sys
import os
from pathlib import Path
from uuid import UUID, uuid4
from typing import Dict, Any, List
import tempfile

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.services.minio_service import MinIOService
from app.models.parser import Parser, ParserStatus
from app.models.file import File, FileStatus
from app.models.library import Library
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.core.database import get_session
from sqlmodel import Session, select

class ParserServiceTester:
    """CLI tester for Parser Service"""
    
    def __init__(self):
        self.parser_service = ParserService()
        self.minio_service = MinIOService()
    
    def create_parser(self, name: str, module_type: str, mime_types: List[str], params: Dict[str, Any]) -> str:
        """Create a new parser configuration"""
        try:
            with get_session() as session:
                parser = self.parser_service.create_parser(
                    session=session,
                    name=name,
                    module_type=module_type,
                    supported_mime=mime_types,
                    params=params
                )
                return f"Created parser: {parser.id} - {parser.name}"
        except Exception as e:
            return f"Error creating parser: {str(e)}"
    
    def list_parsers(self) -> str:
        """List all active parsers"""
        try:
            with get_session() as session:
                parsers = self.parser_service.get_active_parsers(session)
                if not parsers:
                    return "No active parsers found"
                
                result = "Active Parsers:\n"
                for parser in parsers:
                    result += f"  ID: {parser.id}\n"
                    result += f"  Name: {parser.name}\n"
                    result += f"  Module Type: {parser.module_type}\n"
                    result += f"  Supported MIME: {parser.supported_mime}\n"
                    result += f"  Params: {parser.params}\n"
                    result += f"  Status: {parser.status}\n"
                    result += "  ---\n"
                return result
        except Exception as e:
            return f"Error listing parsers: {str(e)}"
    
    def create_test_library(self, name: str = "Test Library") -> str:
        """Create a test library for file uploads"""
        try:
            with get_session() as session:
                library = Library(
                    library_name=name,
                    description="Test library for parser service testing",
                    type="regular"
                )
                session.add(library)
                session.commit()
                session.refresh(library)
                return f"Created test library: {library.id} - {library.library_name}"
        except Exception as e:
            return f"Error creating test library: {str(e)}"
    
    def upload_file(self, library_id: str, file_path: str) -> str:
        """Upload a file to MinIO and create database record"""
        try:
            library_uuid = UUID(library_id)
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return f"File not found: {file_path}"
            
            # Determine MIME type
            mime_type_map = {
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.csv': 'text/csv',
                '.json': 'application/json',
                '.md': 'text/markdown',
                '.html': 'text/html',
                '.xml': 'application/xml'
            }
            
            file_extension = file_path_obj.suffix.lower()
            mime_type = mime_type_map.get(file_extension, 'application/octet-stream')
            
            # Create a mock UploadFile object
            class MockUploadFile:
                def __init__(self, file_path: Path):
                    self.filename = file_path.name
                    self.content_type = mime_type
                    self._file_path = file_path
                
                async def read(self):
                    with open(self._file_path, 'rb') as f:
                        return f.read()
                
                async def seek(self, position: int):
                    pass
            
            # Upload to MinIO
            mock_file = MockUploadFile(file_path_obj)
            file_id = uuid4()
            
            # Manually upload file to MinIO
            object_name = f"libraries/{library_uuid}/{file_id}/{file_path_obj.name}"
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
                file_size = len(file_content)
                
                import io
                self.minio_service.client.put_object(
                    bucket_name=self.minio_service.bucket_name,
                    object_name=object_name,
                    data=io.BytesIO(file_content),
                    length=file_size,
                    content_type=mime_type
                )
            
            # Create database record
            with get_session() as session:
                file_record = File(
                    id=file_id,
                    library_id=library_uuid,
                    bucket=self.minio_service.bucket_name,
                    object_key=object_name,
                    file_name=file_path_obj.name,
                    mime_type=mime_type,
                    size_bytes=file_size,
                    status=FileStatus.ACTIVE
                )
                session.add(file_record)
                session.commit()
                session.refresh(file_record)
                
                return f"Uploaded file: {file_record.id} - {file_record.file_name} ({mime_type})"
                
        except Exception as e:
            return f"Error uploading file: {str(e)}"
    
    def parse_file(self, file_id: str, parser_id: str) -> str:
        """Parse a file using specified parser"""
        try:
            file_uuid = UUID(file_id)
            parser_uuid = UUID(parser_id)
            
            with get_session() as session:
                results = self.parser_service.parse_files(
                    session=session,
                    file_ids=[file_uuid],
                    parser_id=parser_uuid
                )
                
                if results:
                    result = results[0]
                    return f"Parse result: {result.id} - Status: {result.status}"
                else:
                    return "No parse results returned"
                    
        except Exception as e:
            return f"Error parsing file: {str(e)}"
    
    def get_parse_results(self, parser_id: str = None, file_id: str = None) -> str:
        """Get parse results with optional filters"""
        try:
            parser_uuid = UUID(parser_id) if parser_id else None
            file_uuid = UUID(file_id) if file_id else None
            
            with get_session() as session:
                results = self.parser_service.get_parse_results(
                    session=session,
                    parser_id=parser_uuid,
                    file_id=file_uuid
                )
                
                if not results:
                    return "No parse results found"
                
                output = "Parse Results:\n"
                for result in results:
                    output += f"  ID: {result.id}\n"
                    output += f"  File ID: {result.file_id}\n"
                    output += f"  Parser ID: {result.parser_id}\n"
                    output += f"  Status: {result.status}\n"
                    output += f"  Object Key: {result.object_key}\n"
                    if result.parsed_at:
                        output += f"  Parsed At: {result.parsed_at}\n"
                    if result.error_message:
                        output += f"  Error: {result.error_message}\n"
                    if result.extra_meta:
                        output += f"  Metadata: {result.extra_meta}\n"
                    output += "  ---\n"
                
                return output
                
        except Exception as e:
            return f"Error getting parse results: {str(e)}"
    
    def get_parsed_data(self, parse_result_id: str) -> str:
        """Get parsed data from a successful parse result"""
        try:
            result_id = int(parse_result_id)
            
            with get_session() as session:
                df = self.parser_service.get_parsed_data(session, result_id)
                
                output = f"Parsed Data (Shape: {df.shape}):\n"
                output += f"Columns: {list(df.columns)}\n"
                output += f"First 3 rows:\n{df.head(3).to_string()}\n"
                
                return output
                
        except Exception as e:
            return f"Error getting parsed data: {str(e)}"
    
    def test_autorag_availability(self) -> str:
        """Test if AutoRAG modules are available"""
        try:
            from app.services.parser_service import LANGCHAIN_AVAILABLE, LLAMAPARSE_AVAILABLE, CLOVA_AVAILABLE
            
            output = "AutoRAG Module Availability:\n"
            output += f"  Langchain Parse: {'✓' if LANGCHAIN_AVAILABLE else '✗'}\n"
            output += f"  LlamaParse: {'✓' if LLAMAPARSE_AVAILABLE else '✗'}\n"
            output += f"  Clova OCR: {'✓' if CLOVA_AVAILABLE else '✗'}\n"
            
            return output
            
        except Exception as e:
            return f"Error checking AutoRAG availability: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="CLI Test Tool for Parser Service")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create parser command
    create_parser = subparsers.add_parser('create-parser', help='Create a new parser')
    create_parser.add_argument('--name', required=True, help='Parser name')
    create_parser.add_argument('--module-type', required=True, help='Module type (langchain, llama_parse, clova_ocr)')
    create_parser.add_argument('--mime-types', required=True, help='Comma-separated MIME types')
    create_parser.add_argument('--params', default='{}', help='JSON parameters')
    
    # List parsers command
    subparsers.add_parser('list-parsers', help='List all active parsers')
    
    # Create test library command
    create_lib_parser = subparsers.add_parser('create-library', help='Create a test library')
    create_lib_parser.add_argument('--name', default='Test Library', help='Library name')
    
    # Upload file command
    upload_parser = subparsers.add_parser('upload-file', help='Upload a file')
    upload_parser.add_argument('--library-id', required=True, help='Library UUID')
    upload_parser.add_argument('--file-path', required=True, help='Path to file')
    
    # Parse file command
    parse_parser = subparsers.add_parser('parse-file', help='Parse a file')
    parse_parser.add_argument('--file-id', required=True, help='File UUID')
    parse_parser.add_argument('--parser-id', required=True, help='Parser UUID')
    
    # Get results command
    results_parser = subparsers.add_parser('get-results', help='Get parse results')
    results_parser.add_argument('--parser-id', help='Filter by parser UUID')
    results_parser.add_argument('--file-id', help='Filter by file UUID')
    
    # Get parsed data command
    data_parser = subparsers.add_parser('get-data', help='Get parsed data')
    data_parser.add_argument('--result-id', required=True, help='Parse result ID')
    
    # Test AutoRAG availability
    subparsers.add_parser('test-autorag', help='Test AutoRAG module availability')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tester = ParserServiceTester()
    
    try:
        if args.command == 'create-parser':
            mime_types = [mt.strip() for mt in args.mime_types.split(',')]
            params = json.loads(args.params)
            result = tester.create_parser(args.name, args.module_type, mime_types, params)
            
        elif args.command == 'list-parsers':
            result = tester.list_parsers()
            
        elif args.command == 'create-library':
            result = tester.create_test_library(args.name)
            
        elif args.command == 'upload-file':
            result = tester.upload_file(args.library_id, args.file_path)
            
        elif args.command == 'parse-file':
            result = tester.parse_file(args.file_id, args.parser_id)
            
        elif args.command == 'get-results':
            result = tester.get_parse_results(args.parser_id, args.file_id)
            
        elif args.command == 'get-data':
            result = tester.get_parsed_data(args.result_id)
            
        elif args.command == 'test-autorag':
            result = tester.test_autorag_availability()
            
        else:
            result = "Unknown command"
        
        print(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 