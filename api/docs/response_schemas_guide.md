# API Response Schemas Guide

This document defines what schemas to return for each HTTP status code across all API endpoints.

## Standard HTTP Status Codes & Schemas

### Success Responses (2xx)
- **200 OK**: Successful GET requests
- **201 Created**: Successful POST requests (resource creation)
- **204 No Content**: Successful DELETE requests

### Client Error Responses (4xx)
- **400 Bad Request**: ValidationErrorResponse
- **401 Unauthorized**: ErrorResponse
- **403 Forbidden**: ErrorResponse
- **404 Not Found**: NotFoundErrorResponse
- **409 Conflict**: ConflictErrorResponse
- **413 Payload Too Large**: ErrorResponse
- **422 Unprocessable Entity**: ValidationErrorResponse

### Server Error Responses (5xx)
- **500 Internal Server Error**: ServerErrorResponse
- **501 Not Implemented**: ErrorResponse
- **503 Service Unavailable**: ErrorResponse

---

## Library Service Endpoints

### POST /library
**Create a new library**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 201 | `Library` | Library created successfully |
| 400 | `ValidationErrorResponse` | Invalid input data |
| 409 | `ConflictErrorResponse` | Library name already exists |
| 500 | `ServerErrorResponse` | Database or server error |

**Example Success Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "library_name": "My Document Library",
  "description": "A collection of technical documents",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Example Error Response (400):**
```json
{
  "error": "validation_error",
  "message": "Validation failed for input data",
  "details": [
    {
      "code": "required_field",
      "message": "Library name is required",
      "field": "library_name"
    }
  ]
}
```

### GET /library
**List all libraries**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `List[Library]` | List of libraries (can be empty) |
| 500 | `ServerErrorResponse` | Database or server error |

### GET /library/{library_id}
**Get single library details with files**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `LibraryDetail` | Library details with files |
| 404 | `NotFoundErrorResponse` | Library not found |
| 500 | `ServerErrorResponse` | Database or server error |

### POST /library/{library_id}/file
**Upload file to library**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 201 | `FileUploadResponse` | File uploaded successfully |
| 400 | `ValidationErrorResponse` | Invalid file or missing library_id |
| 404 | `NotFoundErrorResponse` | Library not found |
| 413 | `ErrorResponse` | File too large |
| 415 | `ErrorResponse` | Unsupported file type |
| 500 | `ServerErrorResponse` | Upload or server error |

### GET /library/{library_id}/file
**List files in library**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `List[FileInfo]` | List of files (can be empty) |
| 404 | `NotFoundErrorResponse` | Library not found |
| 500 | `ServerErrorResponse` | Database or server error |

### DELETE /library/{library_id}
**Delete library**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 204 | No Content | Library deleted successfully |
| 404 | `NotFoundErrorResponse` | Library not found |
| 409 | `ConflictErrorResponse` | Library has dependencies |
| 500 | `ServerErrorResponse` | Database or server error |

### DELETE /library/{library_id}/file/{file_id}
**Delete file from library**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 204 | No Content | File deleted successfully |
| 404 | `NotFoundErrorResponse` | Library or file not found |
| 500 | `ServerErrorResponse` | Database or server error |

---

## Retriever Service Endpoints

### POST /retriever
**Create retriever configuration**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 201 | `RetrieverConfig` | Retriever config created successfully |
| 400 | `ValidationErrorResponse` | Invalid configuration |
| 404 | `NotFoundErrorResponse` | Referenced library not found |
| 500 | `ServerErrorResponse` | Server error |

### GET /retriever
**List retriever configurations**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `List[RetrieverConfig]` | List of configs (can be empty) |
| 500 | `ServerErrorResponse` | Database or server error |

### GET /retriever/{retriever_config_id}
**Get retriever configuration details**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `RetrieverConfigDetail` | Retriever config details |
| 404 | `NotFoundErrorResponse` | Config not found |
| 500 | `ServerErrorResponse` | Database or server error |

### POST /retriever/{retriever_config_id}/query
**Query retriever**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `RetrieverQueryResponse` | Query results |
| 400 | `ValidationErrorResponse` | Invalid query parameters |
| 404 | `NotFoundErrorResponse` | Config not found |
| 503 | `ErrorResponse` | Retriever service unavailable |
| 500 | `ServerErrorResponse` | Server error |

### DELETE /retriever/{retriever_config_id}
**Delete retriever configuration**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 204 | No Content | Config deleted successfully |
| 404 | `NotFoundErrorResponse` | Config not found |
| 409 | `ConflictErrorResponse` | Config has dependencies |
| 500 | `ServerErrorResponse` | Server error |

---

## Chat Service Endpoints

### POST /chat
**Create chat session**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 201 | `Chat` | Chat session created successfully |
| 400 | `ValidationErrorResponse` | Invalid chat data |
| 404 | `NotFoundErrorResponse` | Referenced retriever config not found |
| 500 | `ServerErrorResponse` | Server error |

### GET /chat
**List chat sessions**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `List[ChatSummary]` | List of chat sessions (can be empty) |
| 500 | `ServerErrorResponse` | Database or server error |

### GET /chat/{chat_id}
**Get chat details**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `ChatDetail` | Chat details with messages |
| 404 | `NotFoundErrorResponse` | Chat not found |
| 500 | `ServerErrorResponse` | Database or server error |

### POST /chat/{chat_id}
**Send message to chat**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `MessageResponse` | AI response to message |
| 400 | `ValidationErrorResponse` | Invalid message data |
| 404 | `NotFoundErrorResponse` | Chat not found |
| 429 | `ErrorResponse` | Rate limit exceeded |
| 503 | `ErrorResponse` | AI service unavailable |
| 500 | `ServerErrorResponse` | Server error |

### DELETE /chat/{chat_id}
**Delete chat session**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 204 | No Content | Chat deleted successfully |
| 404 | `NotFoundErrorResponse` | Chat not found |
| 500 | `ServerErrorResponse` | Server error |

---

## Evaluation Service Endpoints

### POST /eval
**Submit evaluation run**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 201 | `Evaluation` | Evaluation run created successfully |
| 400 | `ValidationErrorResponse` | Invalid evaluation config |
| 404 | `NotFoundErrorResponse` | Referenced retriever config not found |
| 500 | `ServerErrorResponse` | Server error |

### GET /eval
**List evaluation runs**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `List[EvaluationSummary]` | List of evaluation runs (can be empty) |
| 500 | `ServerErrorResponse` | Database or server error |

### GET /eval/{eval_id}
**Get evaluation run details**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `EvaluationDetail` | Evaluation run details |
| 404 | `NotFoundErrorResponse` | Evaluation run not found |
| 500 | `ServerErrorResponse` | Database or server error |

### GET /eval/{eval_id}/metrics
**Get evaluation metrics**

| Status Code | Schema | Description |
|-------------|--------|-------------|
| 200 | `EvaluationMetrics` | Evaluation metrics |
| 404 | `NotFoundErrorResponse` | Evaluation run not found |
| 422 | `ErrorResponse` | Evaluation not completed yet |
| 500 | `ServerErrorResponse` | Server error |

---

## Error Response Examples

### ValidationErrorResponse (400)
```json
{
  "error": "validation_error",
  "message": "Validation failed for input data",
  "details": [
    {
      "code": "required_field",
      "message": "Field is required",
      "field": "library_name"
    },
    {
      "code": "invalid_format",
      "message": "Invalid UUID format",
      "field": "retriever_config_id"
    }
  ]
}
```

### NotFoundErrorResponse (404)
```json
{
  "error": "not_found",
  "message": "Library not found",
  "resource_type": "library",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### ConflictErrorResponse (409)
```json
{
  "error": "conflict",
  "message": "Library name already exists",
  "conflicting_field": "library_name"
}
```

### ServerErrorResponse (500)
```json
{
  "error": "internal_server_error",
  "message": "An internal server error occurred",
  "request_id": "req_123456789"
}
```

---

## Implementation Notes

1. **Consistency**: Use the same error schema types across all endpoints
2. **Documentation**: FastAPI will automatically generate OpenAPI docs with these schemas
3. **Validation**: Pydantic automatically validates response data against schemas
4. **Error Handling**: Implement proper exception handlers for each error type
5. **Request ID**: Include request IDs in error responses for easier debugging 