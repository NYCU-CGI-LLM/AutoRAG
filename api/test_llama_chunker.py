#!/usr/bin/env python3
import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path('.').absolute()))
from app.services.chunker_service import ChunkerService

test_data = pd.DataFrame({
    'texts': ['Test document with multiple sentences. This should be chunked properly.'],
    'path': ['test.txt'],
    'page': [1],
    'last_modified_datetime': ['2024-01-01']
})

chunker_service = ChunkerService()
try:
    result = chunker_service._run_autorag_chunker(
        test_data,
        'llama_index_chunk',
        'Token',
        {'chunk_size': 50, 'chunk_overlap': 0}
    )
    print('llama_index_chunk test successful!')
    print('Number of chunks:', len(result.get('doc_id', [])))
except Exception as e:
    print('Error:', str(e))
    import traceback
    traceback.print_exc() 