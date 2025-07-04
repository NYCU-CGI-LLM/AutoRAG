#!/usr/bin/env python3
"""
Test script for ChunkerService

This script tests the chunker service functionality by:
1. Listing available chunkers
2. Listing successful parse results
3. Testing chunking with specific parse results and chunkers
"""

import argparse
import sys
import os
from typing import List, Optional

# Add the api directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_session
from app.services.chunker_service import ChunkerService
from app.models.chunker import Chunker, ChunkerStatus
from app.models.file_parse_result import FileParseResult, ParseStatus
from app.models.file_chunk_result import FileChunkResult, ChunkStatus
from app.models.file import File
from sqlmodel import Session, select


def list_chunkers(session: Session) -> List[Chunker]:
    """List all available chunkers"""
    chunker_service = ChunkerService()
    chunkers = chunker_service.get_active_chunkers(session)
    
    print("=== Available Chunkers ===")
    for i, chunker in enumerate(chunkers, 1):
        print(f"{i}. ID: {chunker.id}")
        print(f"   Name: {chunker.name}")
        print(f"   Module Type: {chunker.module_type}")
        print(f"   Chunk Method: {chunker.chunk_method}")
        print(f"   Chunk Size: {chunker.chunk_size}")
        print(f"   Chunk Overlap: {chunker.chunk_overlap}")
        print(f"   Status: {chunker.status}")
        print(f"   Params: {chunker.params}")
        print()
    
    return chunkers


def list_successful_parse_results(session: Session, limit: int = 10) -> List[FileParseResult]:
    """List successful parse results"""
    statement = select(FileParseResult).where(
        FileParseResult.status == ParseStatus.SUCCESS
    ).limit(limit)
    parse_results = session.exec(statement).all()
    
    print("=== Successful Parse Results ===")
    for i, result in enumerate(parse_results, 1):
        # Get file info
        file = session.get(File, result.file_id)
        file_name = file.file_name if file else "Unknown"
        
        print(f"{i}. Parse Result ID: {result.id}")
        print(f"   File ID: {result.file_id}")
        print(f"   File Name: {file_name}")
        print(f"   Parser ID: {result.parser_id}")
        print(f"   Status: {result.status}")
        print(f"   Parsed At: {result.parsed_at}")
        print(f"   Object Key: {result.object_key}")
        if result.extra_meta:
            print(f"   Extra Meta: {result.extra_meta}")
        print()
    
    return list(parse_results)


def test_chunking(
    session: Session, 
    parse_result_ids: List[str], 
    chunker_id: str
) -> List[FileChunkResult]:
    """Test chunking with specific parse results and chunker"""
    chunker_service = ChunkerService()
    
    print(f"=== Testing Chunking ===")
    print(f"Parse Result IDs: {parse_result_ids}")
    print(f"Chunker ID: {chunker_id}")
    print()
    
    try:
        # Convert IDs to UUID
        from uuid import UUID
        chunker_uuid = UUID(chunker_id)
        parse_result_uuids = [UUID(pid) for pid in parse_result_ids]
        
        # Perform chunking
        results = chunker_service.chunk_parsed_results(
            session=session,
            parse_result_ids=parse_result_uuids,
            chunker_id=chunker_uuid
        )
        
        print("=== Chunking Results ===")
        for i, result in enumerate(results, 1):
            print(f"{i}. Chunk Result ID: {result.id}")
            print(f"   File ID: {result.file_id}")
            print(f"   Parse Result ID: {result.file_parse_result_id}")
            print(f"   Chunker ID: {result.chunker_id}")
            print(f"   Status: {result.status}")
            print(f"   Bucket: {result.bucket}")
            print(f"   Object Key: {result.object_key}")
            print(f"   Chunked At: {result.chunked_at}")
            if result.error_message:
                print(f"   Error: {result.error_message}")
            if result.extra_meta:
                print(f"   Extra Meta: {result.extra_meta}")
            print()
        
        return results
        
    except Exception as e:
        print(f"❌ Error during chunking: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def list_chunk_results(session: Session, limit: int = 10) -> List[FileChunkResult]:
    """List recent chunk results"""
    statement = select(FileChunkResult).limit(limit)
    chunk_results = session.exec(statement).all()
    
    print("=== Recent Chunk Results ===")
    for i, result in enumerate(chunk_results, 1):
        # Get file info
        file = session.get(File, result.file_id)
        file_name = file.file_name if file else "Unknown"
        
        # Get chunker info
        chunker = session.get(Chunker, result.chunker_id)
        chunker_name = chunker.name if chunker else "Unknown"
        
        print(f"{i}. Chunk Result ID: {result.id}")
        print(f"   File: {file_name} (ID: {result.file_id})")
        print(f"   Parse Result ID: {result.file_parse_result_id}")
        print(f"   Chunker: {chunker_name} (ID: {result.chunker_id})")
        print(f"   Status: {result.status}")
        print(f"   Chunked At: {result.chunked_at}")
        if result.error_message:
            print(f"   Error: {result.error_message}")
        if result.extra_meta:
            print(f"   Extra Meta: {result.extra_meta}")
        print()
    
    return list(chunk_results)


def get_chunked_data_preview(session: Session, chunk_result_id: str, preview_rows: int = 5):
    """Get preview of chunked data"""
    chunker_service = ChunkerService()
    
    try:
        from uuid import UUID
        chunk_result_uuid = UUID(chunk_result_id)
        df = chunker_service.get_chunked_data(session, chunk_result_uuid)
        
        print(f"=== Chunked Data Preview (Result ID: {chunk_result_id}) ===")
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print()
        
        # Show preview
        preview_df = df.head(preview_rows)
        print(f"First {preview_rows} rows:")
        for i in range(len(preview_df)):
            row = preview_df.iloc[i]
            print(f"Row {i+1}:")
            for col in df.columns:
                value = row[col]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {col}: {value}")
            print()
            
    except Exception as e:
        print(f"❌ Error getting chunked data: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Test ChunkerService functionality")
    parser.add_argument("--list-chunkers", action="store_true", help="List available chunkers")
    parser.add_argument("--list-parse-results", action="store_true", help="List successful parse results")
    parser.add_argument("--list-chunk-results", action="store_true", help="List recent chunk results")
    parser.add_argument("--test-chunk", action="store_true", help="Test chunking")
    parser.add_argument("--parse-result-ids", type=str, help="Comma-separated parse result IDs for chunking")
    parser.add_argument("--chunker-id", type=str, help="Chunker ID for chunking")
    parser.add_argument("--preview-data", type=str, help="Preview chunked data for given chunk result ID")
    parser.add_argument("--limit", type=int, default=10, help="Limit for listing results")
    
    args = parser.parse_args()
    
    # Get database session
    session = next(get_session())
    
    try:
        if args.list_chunkers:
            list_chunkers(session)
        
        if args.list_parse_results:
            list_successful_parse_results(session, args.limit)
        
        if args.list_chunk_results:
            list_chunk_results(session, args.limit)
        
        if args.test_chunk:
            if not args.parse_result_ids or not args.chunker_id:
                print("❌ Error: --parse-result-ids and --chunker-id are required for testing chunking")
                return
            
            parse_result_ids = [x.strip() for x in args.parse_result_ids.split(",")]
            test_chunking(session, parse_result_ids, args.chunker_id)
        
        if args.preview_data:
            get_chunked_data_preview(session, args.preview_data)
        
        if not any([args.list_chunkers, args.list_parse_results, args.list_chunk_results, 
                   args.test_chunk, args.preview_data]):
            print("No action specified. Use --help for available options.")
            print("\nQuick start:")
            print("1. List chunkers: python test_chunker_service.py --list-chunkers")
            print("2. List parse results: python test_chunker_service.py --list-parse-results")
            print("3. Test chunking: python test_chunker_service.py --test-chunk --parse-result-ids 1,2 --chunker-id <chunker-uuid>")
            print("4. List chunk results: python test_chunker_service.py --list-chunk-results")
            print("5. Preview data: python test_chunker_service.py --preview-data <chunk-result-id>")
    
    finally:
        session.close()


if __name__ == "__main__":
    main() 