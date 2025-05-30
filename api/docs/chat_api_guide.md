# Chat API Guide

The Chat API provides a conversational interface with retrieval-augmented generation (RAG) capabilities. It allows users to create chat sessions that are bound to specific retriever configurations, enabling context-aware AI responses based on indexed documents.

## Overview

### Key Features
- **Retrieval-Augmented Generation**: Responses are enhanced with relevant context from indexed documents
- **Conversation History**: Maintains context across multiple message exchanges
- **Flexible Configuration**: Customizable prompt engineering and retrieval parameters
- **Multiple Models**: Support for various OpenAI models
- **Source Attribution**: Shows which documents were used to generate responses

### Architecture
```
User Message → Retriever Query → Context Formatting → OpenAI API → AI Response
     ↓              ↓                    ↓              ↓           ↓
Save Message → Get Relevant → Build RAG Prompt → Generate → Save Response
               Documents
```

## API Endpoints

### 1. Create Chat Session
**POST** `/chat/`

Creates a new chat session bound to a retriever configuration.

```json
{
  "name": "My Research Chat",
  "retriever_config_id": "uuid-of-retriever",
  "metadata": {
    "project": "research-2024",
    "purpose": "document-analysis"
  }
}
```

**Response:**
```json
{
  "id": "chat-uuid",
  "name": "My Research Chat",
  "retriever_config_id": "uuid-of-retriever",
  "metadata": {...},
  "message_count": 0,
  "last_activity": "2024-02-11T10:00:00Z",
  "created_at": "2024-02-11T10:00:00Z",
  "updated_at": "2024-02-11T10:00:00Z"
}
```

### 2. Send Message
**POST** `/chat/{chat_id}`

Sends a message and receives an AI-generated response with retrieval context.

```json
{
  "message": "What are the key findings about climate change?",
  "model": "gpt-3.5-turbo",
  "stream": false,
  "context_config": {
    "top_k": 5,
    "system_prompt": "You are a scientific research assistant...",
    "filters": {
      "document_type": "research_paper"
    }
  }
}
```

**Response:**
```json
{
  "message_id": "message-uuid",
  "response": "Based on the research documents, the key findings about climate change include...",
  "sources": [
    {
      "content": "Climate models indicate that global temperatures...",
      "score": 0.89,
      "metadata": {
        "document_title": "Climate Research 2024",
        "page": 15
      },
      "doc_id": "doc-123"
    }
  ],
  "model_used": "gpt-3.5-turbo",
  "processing_time": 2.34,
  "token_usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 180,
    "total_tokens": 1430
  }
}
```

### 3. List Chats
**GET** `/chat/`

Returns all chat sessions for the authenticated user.

**Response:**
```json
[
  {
    "id": "chat-uuid",
    "name": "My Research Chat",
    "message_count": 15,
    "last_activity": "2024-02-11T10:30:00Z",
    "retriever_config_name": "Scientific Papers Index"
  }
]
```

### 4. Get Chat Details
**GET** `/chat/{chat_id}`

Returns complete chat information including message history.

**Response:**
```json
{
  "id": "chat-uuid",
  "name": "My Research Chat",
  "retriever_config_id": "retriever-uuid",
  "message_count": 4,
  "last_activity": "2024-02-11T10:30:00Z",
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "What are the key findings?",
      "metadata": {"llm_model": "gpt-3.5-turbo"},
      "created_at": "2024-02-11T10:25:00Z"
    },
    {
      "id": "msg-2", 
      "role": "assistant",
      "content": "Based on the research documents...",
      "metadata": {"llm_model": "gpt-3.5-turbo"},
      "created_at": "2024-02-11T10:25:15Z"
    }
  ],
  "retriever_config_name": "Scientific Papers Index"
}
```

### 5. Delete Chat
**DELETE** `/chat/{chat_id}`

Permanently deletes a chat session and all its messages.

## Configuration Options

### Context Configuration
The `context_config` parameter allows fine-tuning of the RAG behavior:

```json
{
  "top_k": 5,                    // Number of documents to retrieve
  "system_prompt": "You are...", // Custom system instruction
  "filters": {                   // Retrieval filters
    "document_type": "manual",
    "department": "engineering"
  }
}
```

### System Prompts
Customize the AI's behavior with system prompts:

```json
{
  "system_prompt": "You are a technical documentation assistant. Provide precise, step-by-step answers based on the provided manuals. Always cite specific sections when possible."
}
```

## Usage Examples

### Basic Chat Flow
```python
import requests

# 1. Create chat session
chat_response = requests.post("http://localhost:8000/chat/", json={
    "name": "Technical Support Chat",
    "retriever_config_id": "tech-docs-retriever-uuid"
})
chat_id = chat_response.json()["id"]

# 2. Send message
message_response = requests.post(f"http://localhost:8000/chat/{chat_id}", json={
    "message": "How do I configure the SSL certificate?",
    "model": "gpt-3.5-turbo",
    "context_config": {
        "top_k": 3,
        "system_prompt": "You are a technical support assistant."
    }
})

# 3. Get AI response
ai_response = message_response.json()["response"]
sources = message_response.json()["sources"]
```

### Advanced Configuration
```python
# Send message with custom configuration
response = requests.post(f"http://localhost:8000/chat/{chat_id}", json={
    "message": "What are the security best practices?",
    "model": "gpt-4",
    "context_config": {
        "top_k": 10,
        "system_prompt": "You are a cybersecurity expert. Focus on actionable security recommendations.",
        "filters": {
            "document_category": "security",
            "classification": "public"
        }
    }
})
```

## Error Handling

### Common Error Responses

**404 - Chat Not Found**
```json
{
  "detail": "Chat not found"
}
```

**400 - Retriever Not Active**
```json
{
  "detail": "Retriever is not active. Status: pending"
}
```

**500 - OpenAI API Error**
```json
{
  "detail": "Failed to process message: OpenAI API error"
}
```

## Best Practices

### 1. Retriever Selection
- Choose retrievers that are indexed with relevant documents for your use case
- Ensure retrievers are in "active" status before creating chats

### 2. Message Optimization
- Be specific in your queries for better retrieval results
- Use domain-specific terminology that matches your indexed documents

### 3. Context Configuration
- Start with `top_k: 5` and adjust based on response quality
- Use filters to narrow down document scope when needed
- Craft system prompts that align with your specific use case

### 4. Model Selection
- Use `gpt-3.5-turbo` for general conversations and quick responses
- Use `gpt-4` for complex analysis requiring deeper reasoning
- Consider cost implications of different model choices

### 5. Error Handling
- Always check response status codes
- Implement retry logic for transient failures
- Handle OpenAI API rate limits gracefully

## Performance Considerations

### Response Times
- Typical response time: 1-5 seconds
- Factors affecting speed:
  - Number of documents retrieved (`top_k`)
  - Complexity of the query
  - OpenAI model selected
  - Size of conversation history

### Token Usage
- Monitor token usage for cost control
- Longer conversations consume more tokens due to history
- Consider truncating very long conversations

### Scaling
- Each chat session maintains independent state
- Multiple concurrent chats are supported
- Consider implementing rate limiting for production use

## Troubleshooting

### Common Issues

**1. No Relevant Sources Found**
- Check if retriever contains relevant documents
- Verify document indexing was successful
- Try broader or different query terms

**2. Poor Response Quality**
- Adjust `top_k` value (try higher values)
- Refine system prompt for better instruction
- Use more specific queries

**3. Slow Response Times**
- Reduce `top_k` if too many documents are being retrieved
- Check retriever performance
- Consider using faster OpenAI model

### Debug Information
The API returns helpful debug information:
- `processing_time`: Total time for request processing
- `sources`: Documents that influenced the response
- `token_usage`: Detailed token consumption

## Security Considerations

- Chat content is stored in the database
- Ensure proper authentication before production use
- Consider data retention policies for chat history
- Implement proper access controls for sensitive documents
- Monitor API usage for abuse prevention

## Future Enhancements

Planned features:
- Streaming responses for real-time chat experience
- Export chat history functionality
- Advanced analytics and conversation insights
- Integration with more LLM providers
- Custom embedding models for retrieval 