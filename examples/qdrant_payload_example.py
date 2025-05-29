#!/usr/bin/env python3
"""
Qdrant Payload Example - Enhanced AutoRAG Integration

This example demonstrates how to use Qdrant with payload support in AutoRAG,
storing both vectors and rich metadata including original text content.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any

# Set up environment
os.environ["OPENAI_API_KEY"] = "your-openai-key-here"  # Replace with your key

from autorag.vectordb.qdrant import Qdrant


async def demonstrate_qdrant_payload():
    """Comprehensive example of Qdrant with payload support"""
    
    print("🚀 AutoRAG Qdrant Payload Example")
    print("=" * 50)
    
    # Sample documents with rich metadata
    documents = [
        {
            "id": "doc_001",
            "text": "Qdrant is a vector search engine optimized for large scale deployments.",
            "metadata": {
                "title": "Qdrant Introduction",
                "category": "technology",
                "author": "Qdrant Team",
                "page": 1,
                "source_file": "/docs/qdrant_intro.pdf",
                "tags": ["vector-search", "scalability", "performance"]
            }
        },
        {
            "id": "doc_002", 
            "text": "Machine learning models benefit from efficient vector similarity search.",
            "metadata": {
                "title": "ML and Vector Search",
                "category": "machine-learning",
                "author": "AI Researcher",
                "page": 3,
                "source_file": "/docs/ml_vectors.pdf",
                "tags": ["machine-learning", "similarity", "vectors"]
            }
        },
        {
            "id": "doc_003",
            "text": "AutoRAG provides an easy-to-use interface for building retrieval systems.",
            "metadata": {
                "title": "AutoRAG Framework",
                "category": "framework",
                "author": "AutoRAG Team",
                "page": 1,
                "source_file": "/docs/autorag_guide.pdf", 
                "tags": ["autorag", "retrieval", "framework"]
            }
        }
    ]
    
    try:
        print("📊 Step 1: Initialize Qdrant with payload support")
        
        # Initialize Qdrant with payload support enabled
        qdrant = Qdrant(
            embedding_model="mock",  # Use mock for demo (replace with "openai_embed_3_large" if you have API key)
            collection_name="autorag_payload_demo",
            store_text=True,  # Enable text storage in payload
            client_type="docker",
            url="http://localhost:6333"
        )
        
        print(f"✅ Collection: {qdrant.collection_name}")
        print(f"✅ Text storage: {qdrant.store_text}")
        
        print("\n📝 Step 2: Add documents with rich metadata")
        
        # Prepare data for indexing
        doc_ids = [doc["id"] for doc in documents]
        texts = [doc["text"] for doc in documents]
        metadata_list = [doc["metadata"] for doc in documents]
        
        # Add documents with metadata
        await qdrant.add(doc_ids, texts, metadata_list)
        
        print(f"✅ Indexed {len(documents)} documents with payload")
        for doc in documents:
            print(f"   - {doc['id']}: '{doc['text'][:50]}...'")
        
        print("\n🔍 Step 3: Basic vector search")
        
        # Perform basic search
        queries = ["vector search technology"]
        ids, scores = await qdrant.query(queries, top_k=2)
        
        print(f"Query: '{queries[0]}'")
        print("Basic search results:")
        for i, (doc_id, score) in enumerate(zip(ids[0], scores[0])):
            print(f"  {i+1}. {doc_id} (score: {score:.4f})")
        
        print("\n🎯 Step 4: Enhanced search with payload")
        
        # Search with payload data
        results_with_payload, scores = await qdrant.query_with_payload(queries, top_k=3)
        
        print(f"Enhanced search results for: '{queries[0]}'")
        for i, (result, score) in enumerate(zip(results_with_payload[0], scores[0])):
            payload = result["payload"]
            print(f"\n  📄 Result {i+1} (score: {score:.4f})")
            print(f"     ID: {result['id']}")
            print(f"     Title: {payload.get('title', 'Unknown')}")
            print(f"     Category: {payload.get('category', 'Unknown')}")
            print(f"     Author: {payload.get('author', 'Unknown')}")
            print(f"     Text: {payload.get('text', 'No text stored')[:100]}...")
            print(f"     Tags: {', '.join(payload.get('tags', []))}")
            print(f"     Source: {payload.get('source_file', 'Unknown')}")
        
        print("\n📚 Step 5: Fetch documents with payload")
        
        # Fetch specific documents with all their data
        fetch_ids = ["doc_001", "doc_003"]
        fetched_docs = await qdrant.fetch_with_payload(fetch_ids)
        
        print(f"Fetched documents: {fetch_ids}")
        for doc in fetched_docs:
            payload = doc["payload"]
            print(f"\n  📖 Document: {doc['id']}")
            print(f"     Full text: {payload.get('text', 'No text')}")
            print(f"     Metadata: {dict(list(payload.items())[:3])}...")  # Show first 3 metadata items
            print(f"     Vector dim: {len(doc['vector'])}")
        
        print("\n📈 Step 6: Search by category (metadata filtering)")
        
        # Note: This would require Qdrant filtering, which can be added as an enhancement
        print("💡 Future enhancement: Filter search by metadata categories")
        print("   Example: Find all 'technology' category documents")
        print("   This requires implementing Qdrant filtering in query methods")
        
        print("\n✨ Summary of Qdrant Payload Benefits:")
        print("  ✅ Store original text alongside vectors")
        print("  ✅ Rich metadata storage (title, author, tags, etc.)")
        print("  ✅ Automatic indexing metadata (timestamp, model info)")
        print("  ✅ Enhanced search results with full context")
        print("  ✅ Reduced dependency on external Index Result Table")
        print("  ✅ Self-contained document storage")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def demonstrate_index_workflow():
    """Show how the enhanced Qdrant works with AutoRAG indexing"""
    
    print("\n" + "=" * 50)
    print("🔧 AutoRAG Indexing Workflow with Qdrant Payload")
    print("=" * 50)
    
    # Simulate the indexing workflow
    sample_chunk_data = {
        "doc_ids": ["chunk_001", "chunk_002", "chunk_003"],
        "contents": [
            "Introduction to vector databases and their applications in modern AI systems.",
            "Qdrant provides high-performance vector similarity search with payload support.",
            "AutoRAG framework simplifies the development of retrieval-augmented generation systems."
        ],
        "metadata_list": [
            {
                "path": "/documents/ai_intro.pdf",
                "start_end_idx": [0, 512],
                "page": 1,
                "chapter": "Introduction"
            },
            {
                "path": "/documents/qdrant_guide.pdf", 
                "start_end_idx": [1024, 1536],
                "page": 5,
                "chapter": "Vector Search"
            },
            {
                "path": "/documents/autorag_docs.pdf",
                "start_end_idx": [512, 1024], 
                "page": 2,
                "chapter": "Framework Overview"
            }
        ]
    }
    
    print("📝 Input Data:")
    for i, (doc_id, content) in enumerate(zip(sample_chunk_data["doc_ids"], sample_chunk_data["contents"])):
        metadata = sample_chunk_data["metadata_list"][i]
        print(f"  - {doc_id}: {content[:50]}...")
        print(f"    Source: {metadata['path']} (page {metadata['page']})")
    
    print("\n⚙️ Indexing Process:")
    print("  1. vectordb_index() calls qdrant.add(ids, texts, metadata_list)")
    print("  2. Qdrant stores:")
    print("     - Vector embeddings for similarity search")
    print("     - Original text in payload['text']")
    print("     - Document metadata in payload")
    print("     - Indexing metadata (timestamp, model, etc.)")
    print("  3. Index Result Table stores:")
    print("     - Basic indexing information")
    print("     - Collection name and configuration")
    print("     - Reference to retriever")
    
    print("\n🎯 Benefits of this approach:")
    print("  ✅ Self-contained: Each Qdrant point has full document info")
    print("  ✅ Rich search: Can return text + metadata in one query")
    print("  ✅ Flexible: Easy to add new metadata fields")
    print("  ✅ Efficient: Reduces need for separate content lookups")


async def main():
    """Main demo function"""
    print("AutoRAG Enhanced Qdrant Integration Demo")
    print("Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
    print()
    
    # Run payload demonstration
    success = await demonstrate_qdrant_payload()
    
    if success:
        print("\n🎉 Payload demo completed successfully!")
    else:
        print("\n❌ Payload demo failed - check Qdrant connection")
    
    # Show indexing workflow
    demonstrate_index_workflow()
    
    print("\n" + "=" * 50)
    print("Demo complete! 🚀")


if __name__ == "__main__":
    asyncio.run(main()) 