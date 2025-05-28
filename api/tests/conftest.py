"""
Pytest configuration and fixtures for API tests
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import pandas as pd
from sqlalchemy import text

# Add the api directory to Python path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

# Add autorag to path
autorag_dir = api_dir.parent / "autorag"
if autorag_dir.exists():
    sys.path.insert(0, str(autorag_dir))

from app.core.database import get_session
from app.core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test settings fixture"""
    return Settings(
        autorag_api_env="test",
        secret_key="test-secret-key",
        minio_endpoint="localhost:9000",
        minio_access_key="testkey",
        minio_secret_key="testsecret",
        minio_secure=False,
        minio_bucket_name="test-bucket"
    )


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session"""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables manually for SQLite compatibility
    # Skip the problematic ARRAY and JSONB columns for testing
    with engine.begin() as conn:
        # Create simplified tables for testing
        conn.execute(text("""
            CREATE TABLE library (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE file (
                id TEXT PRIMARY KEY,
                library_id TEXT NOT NULL,
                bucket TEXT DEFAULT 'rag-files',
                object_key TEXT NOT NULL,
                file_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER,
                checksum_md5 TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploader_id TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (library_id) REFERENCES library(id)
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE parser (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                module_type TEXT NOT NULL,
                supported_mime TEXT DEFAULT '[]',
                params TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active'
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE file_parse_result (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                parser_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                result_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES file(id),
                FOREIGN KEY (parser_id) REFERENCES parser(id)
            )
        """))
    
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(test_db: Session, test_settings: Settings) -> Generator[TestClient, None, None]:
    """Create a test client with dependency overrides"""
    from app.main import app
    
    # Override dependencies
    app.dependency_overrides[get_session] = lambda: test_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_file() -> Generator[str, None, None]:
    """Create a sample PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        # Create a minimal PDF content (this is just for testing)
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
        tmp_file.write(pdf_content)
        tmp_file.flush()
        yield tmp_file.name
    
    # Clean up
    os.unlink(tmp_file.name)


@pytest.fixture
def sample_text_file() -> Generator[str, None, None]:
    """Create a sample text file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as tmp_file:
        tmp_file.write("This is a sample text file for testing.\nIt contains multiple lines.\nFor testing purposes.")
        tmp_file.flush()
        yield tmp_file.name
    
    # Clean up
    os.unlink(tmp_file.name)


@pytest.fixture
def sample_parsed_data() -> Dict[str, Any]:
    """Sample parsed data for testing"""
    return {
        "texts": [
            "This is the first paragraph of the document.",
            "This is the second paragraph with more content.",
            "This is the final paragraph of the test document."
        ],
        "path": [
            "/test/document.pdf",
            "/test/document.pdf", 
            "/test/document.pdf"
        ],
        "page": [1, 1, 2],
        "last_modified_datetime": [
            "2024-01-01T00:00:00",
            "2024-01-01T00:00:00",
            "2024-01-01T00:00:00"
        ]
    }


@pytest.fixture
def sample_chunked_data() -> Dict[str, Any]:
    """Sample chunked data for testing"""
    return {
        "doc_id": ["doc1_chunk1", "doc1_chunk2", "doc1_chunk3"],
        "contents": [
            "This is the first chunk of the document.",
            "This is the second chunk with more content.",
            "This is the final chunk of the test document."
        ],
        "path": [
            "/test/document.pdf",
            "/test/document.pdf",
            "/test/document.pdf"
        ],
        "start_end_idx": [
            [0, 45],
            [46, 95],
            [96, 145]
        ],
        "metadata": [
            {"page": 1, "source": "pdf"},
            {"page": 1, "source": "pdf"},
            {"page": 2, "source": "pdf"}
        ]
    }


@pytest.fixture
def sample_dataframe(sample_parsed_data: Dict[str, Any]) -> pd.DataFrame:
    """Create a sample DataFrame for testing"""
    return pd.DataFrame(sample_parsed_data)


@pytest.fixture
def mock_minio_service():
    """Mock MinIO service for testing"""
    from unittest.mock import Mock
    
    mock_service = Mock()
    mock_service.upload_file.return_value = "test-object-key"
    mock_service.download_file.return_value = Mock()
    mock_service.delete_file.return_value = True
    
    return mock_service


# Pytest hooks for better test organization
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location"""
    for item in items:
        # Mark tests in unit/ directory as unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark tests in integration/ directory as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark tests that use minio as requiring minio
        if "minio" in item.name.lower():
            item.add_marker(pytest.mark.minio)
