#!/usr/bin/env python3
"""
Test script for ParserService._parse_single_file() method
This script uses existing database data to test the parsing functionality
"""

import sys
import os
import logging
from pathlib import Path
from uuid import UUID
from typing import List, Optional

# Add the api directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine
from app.services.parser_service import ParserService
from app.models.file import File
from app.models.parser import Parser
from app.models.file_parse_result import FileParseResult, ParseStatus
from sqlmodel import Session, select

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_available_files() -> List[File]:
    """List all available files in the database"""
    with Session(engine) as session:
        files = session.exec(select(File)).all()
        files_list = list(files)
        if not files_list:
            print("No files found in database")
            return []
        
        print(f"\nFound {len(files_list)} files in database:")
        print("-" * 80)
        for file in files_list:
            print(f"ID: {file.id}")
            print(f"Name: {file.file_name}")
            print(f"MIME Type: {file.mime_type}")
            print(f"Library ID: {file.library_id}")
            print(f"Bucket: {file.bucket}")
            print(f"Object Key: {file.object_key}")
            print(f"Status: {file.status}")
            print(f"Uploaded: {file.uploaded_at}")
            print("-" * 80)
        
        return files_list

def list_available_parsers() -> List[Parser]:
    """List all available parsers in the database"""
    with Session(engine) as session:
        parsers = session.exec(select(Parser)).all()
        parsers_list = list(parsers)
        if not parsers_list:
            print("No parsers found in database")
            return []
        
        print(f"\nFound {len(parsers_list)} parsers in database:")
        print("-" * 80)
        for parser in parsers_list:
            print(f"ID: {parser.id}")
            print(f"Name: {parser.name}")
            print(f"Module Type: {parser.module_type}")
            print(f"Supported MIME: {parser.supported_mime}")
            print(f"Parameters: {parser.params}")
            print(f"Status: {parser.status}")
            print("-" * 80)
        
        return parsers_list

def find_compatible_parser(file_mime_type: str, parsers: List[Parser]) -> Optional[Parser]:
    """Find a parser that supports the given file MIME type"""
    for parser in parsers:
        if file_mime_type in parser.supported_mime or "*/*" in parser.supported_mime:
            return parser
    return None

def test_parse_single_file(file_id: Optional[str] = None, parser_id: Optional[str] = None):
    """Test the _parse_single_file method"""
    
    # Initialize parser service
    parser_service = ParserService()
    
    with Session(engine) as session:
        # Get files and parsers
        files = list_available_files()
        parsers = list_available_parsers()
        
        if not files:
            print("❌ No files available for testing")
            return
        
        if not parsers:
            print("❌ No parsers available for testing")
            return
        
        # Select file to test
        if file_id:
            try:
                file_uuid = UUID(file_id)
                file = session.get(File, file_uuid)
                if not file:
                    print(f"❌ File with ID {file_id} not found")
                    return
            except ValueError:
                print(f"❌ Invalid file ID format: {file_id}")
                return
        else:
            # Use the first available file
            file = files[0]
            print(f"📁 Using first available file: {file.file_name}")
        
        # Select parser to test
        if parser_id:
            try:
                parser_uuid = UUID(parser_id)
                parser = session.get(Parser, parser_uuid)
                if not parser:
                    print(f"❌ Parser with ID {parser_id} not found")
                    return
            except ValueError:
                print(f"❌ Invalid parser ID format: {parser_id}")
                return
        else:
            # Find a compatible parser
            parser = find_compatible_parser(file.mime_type, parsers)
            if not parser:
                print(f"❌ No compatible parser found for MIME type: {file.mime_type}")
                return
            print(f"🔧 Using compatible parser: {parser.name}")
        
        # Check if parser supports the file type
        if file.mime_type not in parser.supported_mime and "*/*" not in parser.supported_mime:
            print(f"❌ Parser {parser.name} does not support MIME type {file.mime_type}")
            print(f"   Supported types: {parser.supported_mime}")
            return
        
        print(f"\n🚀 Testing parser service with:")
        print(f"   File: {file.file_name} ({file.mime_type})")
        print(f"   Parser: {parser.name} ({parser.module_type})")
        print(f"   File Object Key: {file.object_key}")
        
        # Check if file exists in MinIO
        try:
            file_data = parser_service.minio_service.download_file(file.object_key)
            content = file_data.read()
            print(f"✅ File found in MinIO, size: {len(content)} bytes")
        except Exception as e:
            print(f"❌ Failed to download file from MinIO: {str(e)}")
            return
        
        # Test the _parse_single_file method
        try:
            print(f"\n⏳ Starting parse operation...")
            result = parser_service._parse_single_file(session, file, parser)
            
            print(f"\n✅ Parse operation completed!")
            print(f"   Result ID: {result.id}")
            print(f"   Status: {result.status}")
            print(f"   Bucket: {result.bucket}")
            print(f"   Object Key: {result.object_key}")
            
            if result.status == ParseStatus.SUCCESS:
                print(f"   Parsed At: {result.parsed_at}")
                print(f"   Extra Meta: {result.extra_meta}")
                
                # Try to download and check the parsed result
                if result.id is not None:
                    try:
                        parsed_df = parser_service.get_parsed_data(session, result.id)
                        print(f"   📊 Parsed DataFrame shape: {parsed_df.shape}")
                        print(f"   📊 Columns: {list(parsed_df.columns)}")
                        if not parsed_df.empty:
                            print(f"   📊 First few rows:")
                            print(parsed_df.head().to_string())
                    except Exception as e:
                        print(f"   ⚠️  Could not retrieve parsed data: {str(e)}")
                else:
                    print(f"   ⚠️  Result ID is None, cannot retrieve parsed data")
                    
            elif result.status == ParseStatus.FAILED:
                print(f"   ❌ Error: {result.error_message}")
            
        except Exception as e:
            print(f"❌ Parse operation failed: {str(e)}")
            logger.exception("Detailed error:")

def main():
    """Main function to run the test"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ParserService._parse_single_file() method")
    parser.add_argument("--file-id", help="Specific file ID to test (UUID)")
    parser.add_argument("--parser-id", help="Specific parser ID to use (UUID)")
    parser.add_argument("--list-only", action="store_true", help="Only list available files and parsers")
    
    args = parser.parse_args()
    
    if args.list_only:
        list_available_files()
        list_available_parsers()
    else:
        test_parse_single_file(args.file_id, args.parser_id)

if __name__ == "__main__":
    main() 