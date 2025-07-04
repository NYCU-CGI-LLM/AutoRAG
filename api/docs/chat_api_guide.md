# Chat API Guide

The Chat API provides a conversational interface with retrieval-augmented generation (RAG) capabilities. It allows users to create chat sessions that are bound to specific retriever configurations, enabling context-aware AI responses based on indexed documents.

## Overview

### Key Features
- **Retrieval-Augmented Generation**: Responses are enhanced with relevant context from indexed documents
- **Conversation History**: Maintains context across multiple message exchanges
- **Flexible Configuration**: Customizable LLM parameters and retrieval settings per chat
- **Parameter Inheritance**: Chat-level defaults with per-message overrides
- **Multiple Models**: Support for various OpenAI models with different settings
- **Source Attribution**: Shows which documents were used to generate responses

### Architecture
```
User Message → Retriever Query → Context Formatting → OpenAI API → AI Response
     ↓              ↓                    ↓              ↓           ↓
Save Message → Get Relevant → Build RAG Prompt → Generate → Save Response
               Documents                ↑              ↑
                                   Config      Parameters
                                   Defaults    Overrides
```

## API Endpoints

### 1. Create Chat Session
**POST** `/chat/`

Creates a new chat session bound to a retriever configuration with customizable LLM and retrieval parameters.

**Request Body:**
```json
{
  "name": "My Research Chat",
  "retriever_id": "uuid-of-retriever",
  "metadata": {
    "project": "research-2024",
    "purpose": "document-analysis"
  },
  // LLM Configuration (optional - defaults shown)
  "llm_model": "gpt-3.5-turbo",      // OpenAI model to use
  "temperature": 0.7,                // Creativity/randomness (0.0-2.0)
  "top_p": 1.0,                      // Nucleus sampling (0.0-1.0)
  
  // Retrieval Configuration (optional)
  "top_k": 5                         // Number of documents to retrieve (1-20)
}
```

**Response:**
```json
{
  "id": "chat-uuid",
  "name": "My Research Chat",
  "retriever_id": "uuid-of-retriever",
  "metadata": {...},
  "message_count": 0,
  "last_activity": "2024-02-11T10:00:00Z",
  "created_at": "2024-02-11T10:00:00Z", 
  "updated_at": "2024-02-11T10:00:00Z",
  "config": {
    "llm_model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "top_p": 1.0,
    "top_k": 5
  }
}
```

### 2. Send Message
**POST** `/chat/{chat_id}`

Sends a message and receives an AI-generated response with retrieval context. Message parameters override chat defaults if provided.

**Request Body:**
```json
{
  "message": "What are the key findings about climate change?",
  
  // Optional parameter overrides (uses chat defaults if not provided)
  "model": "gpt-4",              // Override LLM model for this message
  "temperature": 0.3,            // Override temperature for this message
  "top_p": 0.9,                 // Override top_p for this message
  "top_k": 8,                   // Override retrieval count for this message
  
  "stream": false,
  "context_config": {
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
  "model_used": "gpt-4",
  "processing_time": 2.34,
  "token_usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 180,
    "total_tokens": 1430
  },
  "config_used": {
    "model": "gpt-4",
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 8,
    "stream": false
  }
}
```

### 3. List Chats
**GET** `/chat/`

Returns all chat sessions for the authenticated user with their configurations.

**Response:**
```json
[
  {
    "id": "chat-uuid",
    "name": "My Research Chat",
    "message_count": 15,
    "last_activity": "2024-02-11T10:30:00Z",
    "retriever_config_name": "Scientific Papers Index",
    "config": {
      "llm_model": "gpt-4",
      "temperature": 0.3,
      "top_p": 0.9,
      "top_k": 8
    }
  }
]
```

### 4. Get Chat Details
**GET** `/chat/{chat_id}`

Returns complete chat information including message history and configuration.

**Response:**
```json
{
  "id": "chat-uuid",
  "name": "My Research Chat",
  "retriever_id": "retriever-uuid",
  "message_count": 4,
  "last_activity": "2024-02-11T10:30:00Z",
  "config": {
    "llm_model": "gpt-4",
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 8
  },
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "What are the key findings?",
      "metadata": {"llm_model": "gpt-4"},
      "created_at": "2024-02-11T10:25:00Z"
    },
    {
      "id": "msg-2", 
      "role": "assistant",
      "content": "Based on the research documents...",
      "metadata": {"llm_model": "gpt-4"},
      "created_at": "2024-02-11T10:25:15Z"
    }
  ],
  "retriever_config_name": "Scientific Papers Index"
}
```

## Configuration Parameters

### LLM Parameters

#### Model Selection
Supported OpenAI models:
- `gpt-3.5-turbo`: Fast, cost-effective for general conversations
- `gpt-4`: More capable, better reasoning for complex tasks
- `gpt-4-turbo`: Latest GPT-4 with improved performance

#### Temperature (0.0 - 2.0)
Controls creativity and randomness:
- `0.0-0.3`: Very focused, deterministic responses (good for factual Q&A)
- `0.4-0.7`: Balanced creativity and consistency (default: 0.7)
- `0.8-1.2`: More creative and varied responses
- `1.3-2.0`: Highly creative, unpredictable (use carefully)

#### Top P (0.0 - 1.0)
Nucleus sampling for token selection:
- `0.1-0.8`: More focused vocabulary
- `0.9-1.0`: Full vocabulary range (default: 1.0)

### Retrieval Parameters

#### Top K (1 - 20)
Number of documents to retrieve for context:
- `1-3`: Minimal context for creative tasks
- `4-6`: Balanced retrieval (default: 5)
- `7-15`: Comprehensive context for research
- `16-20`: Maximum context (may exceed token limits)

## Configuration Patterns

### Research & Analysis
```json
{
  "llm_model": "gpt-4",
  "temperature": 0.2,    // Very focused
  "top_p": 0.8,
  "top_k": 10           // Comprehensive context
}
```

### Creative Writing
```json
{
  "llm_model": "gpt-3.5-turbo",
  "temperature": 1.0,    // Creative
  "top_p": 0.95,
  "top_k": 3            // Light context for freedom
}
```

### Balanced Chat
```json
{
  "llm_model": "gpt-3.5-turbo",
  "temperature": 0.7,    // Default balanced
  "top_p": 1.0,
  "top_k": 5            // Standard retrieval
}
```

### Technical Support
```json
{
  "llm_model": "gpt-4",
  "temperature": 0.1,    // Very precise
  "top_p": 0.9,
  "top_k": 8            // Good technical context
}
```

## Usage Examples

### Creating Chats with Different Configurations

```python
import requests

# Research-focused chat
research_chat = requests.post("http://localhost:8000/chat/", json={
    "name": "Scientific Research Assistant",
    "retriever_id": "science-papers-uuid",
    "llm_model": "gpt-4",
    "temperature": 0.2,
    "top_k": 10
})

# Creative writing chat
creative_chat = requests.post("http://localhost:8000/chat/", json={
    "name": "Creative Writing Helper", 
    "retriever_id": "literature-uuid",
    "llm_model": "gpt-3.5-turbo",
    "temperature": 1.1,
    "top_k": 3
})
```

### Sending Messages with Overrides

```python
chat_id = "your-chat-uuid"

# Use chat defaults
default_response = requests.post(f"http://localhost:8000/chat/{chat_id}", json={
    "message": "What are the main findings?"
})

# Override for creative response
creative_response = requests.post(f"http://localhost:8000/chat/{chat_id}", json={
    "message": "Write a creative summary of the findings",
    "temperature": 1.2,    # Override for more creativity
    "top_k": 3            # Override for less context
})

# Override for precise analysis
precise_response = requests.post(f"http://localhost:8000/chat/{chat_id}", json={
    "message": "What are the exact methodologies used?",
    "model": "gpt-4",      # Override to better model
    "temperature": 0.1,    # Override for precision
    "top_k": 12           # Override for more context
})
```

## Best Practices

### 1. Chat Configuration Strategy
- Set chat defaults based on your primary use case
- Use conservative settings for factual work (low temperature, high top_k)
- Use creative settings for brainstorming (high temperature, low top_k)

### 2. Parameter Override Patterns
- Override temperature for specific creative/analytical needs
- Override model for complex reasoning vs. speed requirements  
- Override top_k based on context needs per message

### 3. Model Selection Guidelines
- **GPT-3.5-turbo**: Daily conversations, summaries, general Q&A
- **GPT-4**: Complex analysis, reasoning, technical explanations
- **GPT-4-turbo**: When you need the latest capabilities

### 4. Temperature Guidelines
- **0.0-0.3**: Factual Q&A, technical documentation, precise analysis
- **0.4-0.7**: General conversation, balanced responses
- **0.8-1.2**: Creative writing, brainstorming, varied responses
- **1.3+**: Experimental, highly creative content

### 5. Top K Guidelines
- **1-3**: Creative tasks where context might constrain creativity
- **4-6**: General conversation and Q&A
- **7-12**: Research and analysis requiring comprehensive context
- **13+**: Deep research requiring maximum available context

## Error Handling

### Configuration Validation Errors
```json
{
  "detail": [
    {
      "loc": ["temperature"],
      "msg": "ensure this value is less than or equal to 2.0",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### Model Not Available
```json
{
  "detail": "Model 'gpt-5' is not available. Supported models: gpt-3.5-turbo, gpt-4"
}
```

## Performance Considerations

### Response Times by Configuration
- **GPT-3.5-turbo**: 1-3 seconds typical
- **GPT-4**: 3-8 seconds typical
- **High top_k (10+)**: +1-2 seconds for retrieval
- **Temperature**: No significant impact on speed

### Token Usage Optimization
- Higher top_k = more prompt tokens
- Longer conversations = more context tokens
- Monitor `token_usage` in responses for cost control

### Cost-Performance Balance
- **Development/Testing**: gpt-3.5-turbo with moderate settings
- **Production**: Mix of models based on query complexity
- **High-volume**: Optimize top_k and use conversation truncation

## Troubleshooting

### Configuration Issues
1. **Parameters not taking effect**: Check parameter ranges and data types
2. **Unexpected responses**: Verify temperature and top_p settings
3. **Missing context**: Increase top_k or check retriever performance

### Performance Issues
1. **Slow responses**: Reduce top_k, use gpt-3.5-turbo
2. **High costs**: Monitor token usage, optimize configurations
3. **Quality issues**: Experiment with temperature and model selection

The Chat API's flexible configuration system allows you to fine-tune the AI behavior for any use case while maintaining consistency through chat-level defaults and enabling flexibility through per-message overrides. 