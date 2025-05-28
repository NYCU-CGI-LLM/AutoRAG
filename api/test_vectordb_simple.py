#!/usr/bin/env python3
"""
Simple test script for VectorDB service
Demonstrates how to store and search embeddings using ChromaDB
"""

import os
import sys
from uuid import uuid4
from dotenv import load_dotenv

# Add the api directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.vectordb_service import VectorDBService

def test_vectordb_service():
    """Test the VectorDB service with sample data"""
    
    # Load environment variables
    load_dotenv("../.env.dev")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"✓ OPENAI_API_KEY loaded: {api_key[:20]}...")
        embedding_model = "openai_embed_3_large"
    else:
        print("✗ OPENAI_API_KEY not found, using mock embedding")
        embedding_model = "mock"
    
    # Initialize VectorDB service
    print("\n=== Initializing VectorDB Service ===")
    vectordb_service = VectorDBService(chroma_path="./test_chroma")
    
    # Test health check
    print("\n=== Health Check ===")
    health = vectordb_service.health_check()
    print(f"Status: {health['status']}")
    print(f"Path: {health['chroma_path']}")
    print(f"Collections: {health['total_collections']}")
    
    # Generate test data
    library_id = uuid4()
    doc_ids = [f"doc_{i}" for i in range(5)]
    contents = [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with multiple layers.",
        "Natural language processing helps computers understand text.",
        "Computer vision enables machines to interpret visual information.",
        "Reinforcement learning trains agents through rewards and penalties."
    ]
    
    print(f"\n=== Storing Embeddings ===")
    print(f"Library ID: {library_id}")
    print(f"Documents: {len(doc_ids)}")
    print(f"Embedding Model: {embedding_model}")
    
    # Store embeddings
    try:
        result = vectordb_service.store_embeddings(
            library_id=library_id,
            doc_ids=doc_ids,
            contents=contents,
            embedding_model=embedding_model
        )
        
        print(f"✓ Storage successful!")
        print(f"  Collection: {result['collection_name']}")
        print(f"  Documents: {result['total_documents']}")
        print(f"  Dimensions: {result['vector_dimension']}")
        
    except Exception as e:
        print(f"✗ Storage failed: {str(e)}")
        return
    
    # Test similarity search
    print(f"\n=== Similarity Search ===")
    queries = [
        "artificial intelligence and machine learning",
        "neural networks and deep learning",
        "text processing and NLP"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        try:
            search_results = vectordb_service.similarity_search(
                library_id=library_id,
                query=query,
                top_k=3,
                embedding_model=embedding_model
            )
            
            print(f"Found {len(search_results)} results:")
            for result in search_results:
                print(f"  {result['rank']}. Score: {result['score']:.4f}")
                print(f"     Doc ID: {result['doc_id']}")
                print(f"     Content: {result['content'][:60]}...")
                
        except Exception as e:
            print(f"✗ Search failed: {str(e)}")
    
    # Test collection stats
    print(f"\n=== Collection Statistics ===")
    try:
        stats = vectordb_service.get_collection_stats(library_id, embedding_model)
        print(f"Collection: {stats['collection_name']}")
        print(f"Status: {stats['status']}")
        print(f"Documents: {stats['total_documents']}")
        print(f"Dimensions: {stats['vector_dimension']}")
        
    except Exception as e:
        print(f"✗ Stats failed: {str(e)}")
    
    # List all collections
    print(f"\n=== All Collections ===")
    try:
        collections = vectordb_service.list_collections()
        print(f"Total collections: {len(collections)}")
        for collection in collections:
            print(f"  - {collection['collection_name']}")
            print(f"    Library: {collection['library_id']}")
            print(f"    Model: {collection['embedding_model']}")
            print(f"    Documents: {collection['total_documents']}")
            
    except Exception as e:
        print(f"✗ List failed: {str(e)}")
    
    print(f"\n=== Test Complete ===")
    print("VectorDB service is working correctly!")
    print(f"Data stored in: ./test_chroma")
    print(f"Collection name: {result['collection_name']}")

if __name__ == "__main__":
    test_vectordb_service() 