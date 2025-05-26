# API Usage Examples

This document provides examples of how to use the new REST API endpoints for the RAG system.

## Library Management

### Create a Library
```bash
curl -X POST "http://localhost:8000/library" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Document Library",
    "description": "A collection of technical documents",
    "metadata": {"category": "technical"}
  }'
```

### List All Libraries
```bash
curl -X GET "http://localhost:8000/library"
```

### Upload a File to Library
```bash
curl -X POST "http://localhost:8000/library/{library_id}/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### List Files in Library
```bash
curl -X GET "http://localhost:8000/library/{library_id}/file"
```

## Retriever Service

### Create a Retriever Configuration
```bash
curl -X POST "http://localhost:8000/retriever" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dense Retriever Config",
    "description": "Configuration for dense vector retrieval",
    "library_id": "550e8400-e29b-41d4-a716-446655440000",
    "config": {
      "embedding_model": "text-embedding-ada-002",
      "chunk_size": 512,
      "overlap": 50,
      "similarity_metric": "cosine"
    }
  }'
```

### List Retriever Configurations
```bash
curl -X GET "http://localhost:8000/retriever"
```

### Get Retriever Configuration Details
```bash
curl -X GET "http://localhost:8000/retriever/{retriever_config_id}"
```

### Query a Retriever
```bash
curl -X POST "http://localhost:8000/retriever/{retriever_config_id}/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main features of the system?",
    "top_k": 5,
    "filters": {"document_type": "manual"}
  }'
```

## Chat Service

### Create a Chat Session
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technical Support Chat",
    "retriever_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {"session_type": "support"}
  }'
```

### Send a Message
```bash
curl -X POST "http://localhost:8000/chat/{chat_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I configure the system?",
    "model": "gpt-4",
    "stream": false,
    "context_config": {"max_context_length": 2000}
  }'
```

### Get Chat History
```bash
curl -X GET "http://localhost:8000/chat/{chat_id}"
```

### List All Chats
```bash
curl -X GET "http://localhost:8000/chat"
```

## Evaluation Service

### Submit an Evaluation Run
```bash
curl -X POST "http://localhost:8000/eval" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Retrieval Quality Evaluation",
    "retriever_config_id": "550e8400-e29b-41d4-a716-446655440000",
    "evaluation_config": {
      "metrics": ["precision", "recall", "f1_score", "ndcg"],
      "k_values": [1, 3, 5, 10]
    },
    "dataset_config": {
      "dataset_type": "qa_pairs",
      "dataset_size": 100
    }
  }'
```

### Check Evaluation Status
```bash
curl -X GET "http://localhost:8000/eval/{eval_id}"
```

### List Evaluation Runs
```bash
curl -X GET "http://localhost:8000/eval"
```

### Get Evaluation Metrics
```bash
curl -X GET "http://localhost:8000/eval/{eval_id}/metrics"
```

## Response Examples

### Library Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Document Library",
  "description": "A collection of technical documents",
  "metadata": {"category": "technical"},
  "file_count": 5,
  "total_size": 2048576,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Chat Message Response
```json
{
  "message_id": "660e8400-e29b-41d4-a716-446655440001",
  "response": "To configure the system, you need to...",
  "sources": [
    {
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "score": 0.95,
      "content": "Configuration steps..."
    }
  ],
  "model_used": "gpt-4",
  "processing_time": 1.25,
  "token_usage": {
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225
  }
}
```

### Evaluation Result Response
```json
{
  "precision": 0.85,
  "recall": 0.78,
  "f1_score": 0.81,
  "ndcg": 0.89,
  "mrr": 0.82,
  "map_score": 0.80,
  "custom_metrics": {
    "semantic_similarity": 0.88,
    "response_relevance": 0.86
  }
}
``` 