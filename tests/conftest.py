import os
import pytest
import tempfile
import sys
import json
from uuid import uuid4
from pathlib import Path
from unittest.mock import Mock, patch

# Add the api directory to Python path for app module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'autorag'))

from app.services.parser_service import ParserService
from app.services.minio_service import MinIOService


def pytest_sessionstart(session):
    os.environ["BM25"] = "bm25"


@pytest.fixture(scope="session")
def temp_test_dir():
    """Create a temporary directory for test files that persists for the session"""
    temp_dir = tempfile.mkdtemp(prefix="parser_test_")
    yield temp_dir
    # Cleanup after all tests
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.fixture
def sample_text_content():
    """Sample text content for testing"""
    return """
# Sample Document Title

This is a sample document that simulates PDF content.

## Section 1: Introduction
This document contains multiple sections and paragraphs to test the parsing functionality.

## Section 2: Technical Details
- Point 1: AutoRAG integration
- Point 2: Parser service functionality
- Point 3: MinIO storage integration

## Section 3: Conclusion
The parser service successfully processes documents and extracts structured text content.
"""


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing"""
    return """name,age,city,occupation
John Doe,30,New York,Engineer
Jane Smith,25,San Francisco,Designer
Bob Johnson,35,Chicago,Manager
Alice Brown,28,Boston,Developer
"""


@pytest.fixture
def sample_json_content():
    """Sample JSON content for testing"""
    return {
        "document_info": {
            "title": "Sample JSON Document",
            "author": "Test Author",
            "created_date": "2024-01-01"
        },
        "content": [
            {
                "section": "Introduction",
                "text": "This is a sample JSON document for testing parser functionality."
            },
            {
                "section": "Details",
                "text": "The parser should extract this structured content correctly."
            }
        ]
    }


@pytest.fixture
def sample_markdown_content():
    """Sample Markdown content for testing"""
    return """# Sample Markdown Document

## Overview
This is a **sample markdown** document for testing the parser service.

### Features
- Supports *italic* and **bold** text
- Code blocks and `inline code`
- Lists and tables

### Code Example
```python
def hello_world():
    print("Hello, World!")
```

### Table Example
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Data A   | Data B   | Data C   |
"""


@pytest.fixture
def sample_files(temp_test_dir, sample_text_content, sample_csv_content, 
                sample_json_content, sample_markdown_content):
    """Create sample files for testing"""
    files = {}
    
    # Create text file
    text_file = os.path.join(temp_test_dir, "sample_document.txt")
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(sample_text_content)
    files['text'] = text_file
    
    # Create CSV file
    csv_file = os.path.join(temp_test_dir, "sample_data.csv")
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write(sample_csv_content)
    files['csv'] = csv_file
    
    # Create JSON file
    json_file = os.path.join(temp_test_dir, "sample_data.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sample_json_content, f, indent=2)
    files['json'] = json_file
    
    # Create Markdown file
    md_file = os.path.join(temp_test_dir, "sample_document.md")
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(sample_markdown_content)
    files['markdown'] = md_file
    
    return files


@pytest.fixture
def parser_configs():
    """Create parser configurations for testing"""
    return {
        'text': {
            'id': uuid4(),
            'name': 'Langchain Text Parser',
            'module_type': 'langchain',
            'supported_mime': ['text/plain', 'application/pdf'],
            'params': {
                'parse_method': 'pymupdf'
            }
        },
        'csv': {
            'id': uuid4(),
            'name': 'Langchain CSV Parser',
            'module_type': 'langchain',
            'supported_mime': ['text/csv'],
            'params': {
                'parse_method': 'csv'
            }
        },
        'json': {
            'id': uuid4(),
            'name': 'Langchain JSON Parser',
            'module_type': 'langchain',
            'supported_mime': ['application/json'],
            'params': {
                'parse_method': 'json',
                'jq_schema': '.'
            }
        },
        'markdown': {
            'id': uuid4(),
            'name': 'Langchain Markdown Parser',
            'module_type': 'langchain',
            'supported_mime': ['text/markdown'],
            'params': {
                'parse_method': 'unstructuredmarkdown'
            }
        }
    }


@pytest.fixture
def parser_service():
    """Create a ParserService instance for testing"""
    return ParserService()


@pytest.fixture
def mock_minio_service():
    """Create a mock MinIO service for testing"""
    with patch('app.services.minio_service.MinIOService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_file_records():
    """Create mock file records for testing"""
    return [
        {
            'id': uuid4(),
            'file_name': 'sample_document.txt',
            'object_key': f'test_files/{uuid4()}/sample_document.txt',
            'mime_type': 'text/plain',
            'file_size': 1024,
            'file_type': 'text'
        },
        {
            'id': uuid4(),
            'file_name': 'sample_data.csv',
            'object_key': f'test_files/{uuid4()}/sample_data.csv',
            'mime_type': 'text/csv',
            'file_size': 512,
            'file_type': 'csv'
        }
    ]
