#!/usr/bin/env python3
"""
Test script to verify chunker service works with thread-based execution
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add the api directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.services.chunker_service import ChunkerService

def test_chunker_service():
    """Test the chunker service with thread-based execution"""
    
    # Create test data that mimics parsed result
    test_data = pd.DataFrame({
        'texts': [
            'This is a test document with multiple sentences. It should be chunked properly.',
            'Another test document here. This one also has multiple sentences for testing.'
        ],
        'path': ['test1.txt', 'test2.txt'],
        'page': [1, 1],
        'last_modified_datetime': ['2024-01-01', '2024-01-01']
    })
    
    # Create chunker service
    chunker_service = ChunkerService()
    
    # Test parameters
    module_type = "langchain_chunk"
    chunk_method = "character"
    params = {
        "separator": ". ",
        "chunk_size": 50,
        "chunk_overlap": 0
    }
    
    try:
        print("Testing chunker service...")
        result = chunker_service._run_autorag_chunker(
            test_data,
            module_type,
            chunk_method,
            params
        )
        
        print("Success! Chunker service works correctly.")
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys())}")
        print(f"Number of chunks: {len(result.get('doc_id', []))}")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chunker_service()
    sys.exit(0 if success else 1) 