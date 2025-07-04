import pytest
import logging
from unittest.mock import Mock, patch, MagicMock

from autorag.vectordb.qdrant import Qdrant
from autorag.vectordb.pinecone import Pinecone

logger = logging.getLogger("AutoRAG")


@pytest.fixture
def mock_embedding():
    """Mock embedding model that returns consistent dimensions"""
    mock = Mock()
    # Simulate openai_embed_3_large with 3072 dimensions
    mock.get_query_embedding.return_value = [0.1] * 3072
    return mock


@pytest.fixture  
def mock_qdrant_client():
    """Mock Qdrant client"""
    mock = Mock()
    mock.collection_exists.return_value = False
    mock.create_collection.return_value = None
    mock.get_collection.return_value = Mock()
    return mock


@pytest.fixture
def mock_pinecone_client():
    """Mock Pinecone client"""  
    mock = Mock()
    mock.has_index.return_value = False
    mock.create_index.return_value = None
    mock.Index.return_value = Mock()
    return mock


class TestQdrantAutoDimension:
    """Test auto-dimension detection for Qdrant"""
    
    @patch('autorag.vectordb.qdrant.QdrantClient')
    @patch('autorag.vectordb.base.EmbeddingModel')
    def test_auto_detect_dimension_new_collection(self, mock_embedding_class, mock_client_class):
        """Test that Qdrant auto-detects dimension for new collections"""
        # Setup mocks
        mock_embedding = Mock()
        mock_embedding.get_query_embedding.return_value = [0.1] * 3072
        mock_embedding_class.load.return_value = lambda: mock_embedding
        
        mock_client = Mock()
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = None
        mock_client.get_collection.return_value = Mock()
        mock_client_class.return_value = mock_client
        
        # Initialize Qdrant without dimension parameter
        qdrant = Qdrant(
            embedding_model="openai_embed_3_large",
            collection_name="test_collection"
        )
        
        # Verify that create_collection was called with auto-detected dimension
        mock_client.create_collection.assert_called_once()
        create_call_args = mock_client.create_collection.call_args
        vectors_config = create_call_args[1]['vectors_config']
        assert vectors_config.size == 3072  # Auto-detected dimension
    
    @patch('autorag.vectordb.qdrant.QdrantClient')
    @patch('autorag.vectordb.base.EmbeddingModel')
    def test_explicit_dimension_override(self, mock_embedding_class, mock_client_class):
        """Test that explicitly specified dimension is respected"""
        # Setup mocks
        mock_embedding = Mock()
        mock_embedding_class.load.return_value = lambda: mock_embedding
        
        mock_client = Mock()
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = None
        mock_client.get_collection.return_value = Mock()
        mock_client_class.return_value = mock_client
        
        # Initialize Qdrant with explicit dimension
        qdrant = Qdrant(
            embedding_model="openai_embed_3_large",
            collection_name="test_collection",
            dimension=1536  # Explicitly specify different dimension
        )
        
        # Verify that create_collection was called with explicit dimension
        mock_client.create_collection.assert_called_once()
        create_call_args = mock_client.create_collection.call_args
        vectors_config = create_call_args[1]['vectors_config']
        assert vectors_config.size == 1536  # Explicit dimension


class TestPineconeAutoDimension:
    """Test auto-dimension detection for Pinecone"""
    
    @patch('autorag.vectordb.pinecone.Pinecone_client')
    @patch('autorag.vectordb.base.EmbeddingModel')
    def test_auto_detect_dimension_new_index(self, mock_embedding_class, mock_client_class):
        """Test that Pinecone auto-detects dimension for new indexes"""
        # Setup mocks
        mock_embedding = Mock()
        mock_embedding.get_query_embedding.return_value = [0.1] * 3072
        mock_embedding_class.load.return_value = lambda: mock_embedding
        
        mock_client = Mock()
        mock_client.has_index.return_value = False
        mock_client.create_index.return_value = None
        mock_client.Index.return_value = Mock()
        mock_client_class.return_value = mock_client
        
        # Initialize Pinecone without dimension parameter
        pinecone = Pinecone(
            embedding_model="openai_embed_3_large",
            index_name="test_index",
            api_key="test_key"
        )
        
        # Verify that create_index was called with auto-detected dimension
        mock_client.create_index.assert_called_once()
        create_call_args = mock_client.create_index.call_args
        assert create_call_args[1]['dimension'] == 3072  # Auto-detected dimension
    
    @patch('autorag.vectordb.pinecone.Pinecone_client')
    @patch('autorag.vectordb.base.EmbeddingModel') 
    def test_explicit_dimension_override_pinecone(self, mock_embedding_class, mock_client_class):
        """Test that explicitly specified dimension is respected in Pinecone"""
        # Setup mocks
        mock_embedding = Mock()
        mock_embedding_class.load.return_value = lambda: mock_embedding
        
        mock_client = Mock()
        mock_client.has_index.return_value = False
        mock_client.create_index.return_value = None
        mock_client.Index.return_value = Mock()
        mock_client_class.return_value = mock_client
        
        # Initialize Pinecone with explicit dimension
        pinecone = Pinecone(
            embedding_model="openai_embed_3_large",
            index_name="test_index",
            api_key="test_key",
            dimension=1536  # Explicitly specify different dimension
        )
        
        # Verify that create_index was called with explicit dimension
        mock_client.create_index.assert_called_once()
        create_call_args = mock_client.create_index.call_args
        assert create_call_args[1]['dimension'] == 1536  # Explicit dimension


if __name__ == "__main__":
    # Simple smoke test
    print("Testing auto-dimension detection feature...")
    print("✅ Test file created successfully!")
    print("Run with: pytest tests/autorag/vectordb/test_auto_dimension.py -v") 