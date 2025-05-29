# Qdrant

Qdrant is a high-performance vector similarity search engine and database.
It offers a robust, production-ready service with an intuitive API that allows users to store, search, and manage vectors, along with additional payloads.

Qdrant supports advanced filtering, making it ideal for applications involving neural network or semantic-based matching, faceted search, and more.
Its capabilities are particularly beneficial for developing applications that require efficient and scalable vector search solutions.

## Configuration

To use the Qdrant vector database, you need to configure it in your YAML configuration file. Here's an example configuration with automatic dimension detection and payload support:

```yaml
- name: openai_qdrant
  db_type: qdrant
  embedding_model: openai_embed_3_large
  collection_name: openai_embed_3_large
  client_type: docker
  embedding_batch: 50
  similarity_metric: cosine
  store_text: true  # Enable payload text storage
  # dimension parameter is optional - will be auto-detected from embedding_model
```

Or you can explicitly specify the dimension if needed:

```yaml
- name: openai_qdrant
  db_type: qdrant
  embedding_model: openai_embed_3_large
  collection_name: openai_embed_3_large
  client_type: docker
  embedding_batch: 50
  similarity_metric: cosine
  dimension: 3072  # Explicitly specify dimension
  store_text: true  # Store original text in payload
```

### **Enhanced Payload Support**

**NEW FEATURE**: Qdrant now supports rich payload storage, allowing you to store original text content and metadata alongside vector embeddings. This reduces dependency on external storage and enables richer search results.

```yaml
# Full configuration with payload features
- name: enhanced_qdrant
  db_type: qdrant
  embedding_model: openai_embed_3_large
  collection_name: enhanced_collection
  client_type: docker
  similarity_metric: cosine
  store_text: true          # Store original text in payload
  ingest_batch: 64          # Batch size for uploading
  parallel: 2               # Parallel upload threads
  max_retries: 3            # Max retry attempts
```

Here is a simple example of a YAML configuration file that uses the Qdrant vector database and the OpenAI:

```yaml
vectordb:
  - name: openai_qdrant
    db_type: qdrant
    embedding_model: openai_embed_3_large
    collection_name: openai_embed_3_large
    client_type: docker
    embedding_batch: 50
    similarity_metric: cosine
    # No need to specify dimension - will be auto-detected
node_lines:
- node_line_name: retrieve_node_line  # Arbitrary node line name
  nodes:
    - node_type: retrieval
      strategy:
        metrics: [retrieval_f1, retrieval_recall, retrieval_precision]
      top_k: 3
      modules:
        - module_type: vectordb
          vectordb: openai_qdrant
- node_line_name: post_retrieve_node_line  # Arbitrary node line name
  nodes:
    - node_type: prompt_maker
      strategy:
        metrics: [bleu, meteor, rouge]
      modules:
        - module_type: fstring
          prompt: "Read the passages and answer the given question. \n Question: {query} \n Passage: {retrieved_contents} \n Answer : "
    - node_type: generator
      strategy:
        metrics: [bleu, rouge]
      modules:
        - module_type: llama_index_llm
          llm: openai
          model: [ gpt-4o-mini ]
```

1. `embedding_model: str`
   - Purpose: Specifies the name or identifier of the embedding model to be used.
   - Example: "openai_embed_3_large"
   - Note: This should correspond to a valid embedding model that your system can use to generate vector embeddings. For more information see [custom your embedding model](https://docs.auto-rag.com/local_model.html#configure-the-embedding-model) documentation.

2. `collection_name: str`
   - Purpose: Sets the name of the Qdrant collection where the vectors will be stored.
   - Example: "my_vector_collection"
   - Note: If the collection doesn't exist, it will be created. If it exists, it will be loaded.

3. `embedding_batch: int = 100`
   - Purpose: Determines the number of embeddings to process in a single batch.
   - Default: 100
   - Note: Adjust this based on your system's memory and processing capabilities. Larger batches may be faster but require more memory.

4. `similarity_metric: str = "cosine"`
   - Purpose: Specifies the metric used to calculate similarity between vectors.
   - Default: "cosine"
   - Options: "cosine", "l2" (Euclidean distance), "ip" (Inner Product)
   - Note: Choose the metric that best suits your use case and data characteristics.
     - Not support "manhattan"

5. `client_type = "docker"`
    - Purpose: Specifies the type of client you're using to connect to Weaviate.
    - Default: "docker"
    - Options: "docker", "cloud"
    - Note: Choose the appropriate client type based on your deployment.
      - [docker quick start](https://qdrant.tech/documentation/quickstart/)
      - [cloud quick start](https://qdrant.tech/documentation/quickstart-cloud/)

6. `url: str = "http://localhost:6333"`
   - Purpose: The URL of the Qdrant server.
   - Default: "http://localhost:6333"
   - Note: Use only `client_type: docker`. You can see full information at [here](https://qdrant.tech/documentation/quickstart/)

7. `host: str`
   - Purpose: The host of the Qdrant server.
   - Default: ""
   - Note: Use only `client_type: cloud`. You can see full information at [here](https://qdrant.tech/documentation/quickstart-cloud/)

8. `api_key: str`
   - Purpose: The API key for authentication with the Qdrant server.
   - Default: ""
   - Note: Use only `client_type: cloud`. You can see full information at [here](https://qdrant.tech/documentation/quickstart-cloud/)

9. `dimension: Optional[int] = None`
   - Purpose: Specifies the dimension of the vector embeddings.
   - Default: None (auto-detected from embedding model)
   - Note: **New Feature**: If not specified, the dimension will be automatically detected by running a test embedding with the specified model. This eliminates the need to manually match dimensions with embedding models. You can still explicitly specify the dimension if needed for compatibility or performance reasons.
   - Auto-detection examples:
     - `text-embedding-ada-002` → 1536 dimensions
     - `text-embedding-3-small` → 1536 dimensions  
     - `text-embedding-3-large` → 3072 dimensions

10. `ingest_batch: int = 64`
    - Purpose: Determines the number of vectors to ingest in a single batch.
    - Default: 64
    - Note: Adjust this based on your system's memory and processing capabilities. Larger batches may be faster but require more memory.

11. `parallel: int = 1`
    - Purpose: Determines the number of parallel requests to the Qdrant server.
    - Default: 1
    - Note: Adjust this based on your system's processing capabilities. Increasing parallel requests can improve performance.

12. `max_retries: int = 3`
    - Purpose: Specifies the maximum number of retries for failed requests to the Qdrant server.
    - Default: 3
    - Note: Set this based on your system's network reliability and the expected failure rate.

13. `store_text: bool = True`
    - Purpose: **NEW**: Controls whether to store original text content in Qdrant payload.
    - Default: True
    - Note: When enabled, stores the original document text alongside vectors in Qdrant's payload field. This allows for:
      - Self-contained document storage
      - Rich search results with immediate text access
      - Reduced dependency on external content storage
      - Enhanced metadata capabilities
    - Benefits:
      - ✅ Faster content retrieval (no external lookups needed)
      - ✅ Rich metadata storage (titles, authors, tags, etc.)
      - ✅ Automatic indexing metadata (timestamps, model info)
      - ✅ Self-contained collections

### **Payload Data Structure**

When `store_text: true` is enabled, each Qdrant point stores the following payload:

```json
{
  "text": "Original document content...",
  "text_length": 1250,
  "indexed_at": "2024-01-15T10:30:00Z",
  "embedding_model": "openai_embed_3_large",
  "collection_name": "my_collection",
  
  // Custom metadata from your documents
  "title": "Document Title",
  "author": "Author Name", 
  "category": "technology",
  "page": 5,
  "source_file": "/path/to/source.pdf",
  "tags": ["AI", "vector-search"],
  
  // Any other metadata you provide
  "custom_field": "custom_value"
}
```

#### Usage

Here's a brief overview of how to use the main functions of the Qdrant vector database:

1. **Adding Vectors with Payload**:
   ```python
   # Basic addition (vectors only)
   await qdrant_db.add(ids, texts)
   
   # Enhanced addition with metadata
   metadata_list = [
       {"title": "Doc 1", "author": "John", "category": "tech"},
       {"title": "Doc 2", "author": "Jane", "category": "science"}
   ]
   await qdrant_db.add(ids, texts, metadata_list)
   ```
   This method adds new vectors to the database with optional rich metadata stored in payload.

2. **Basic Querying**:
   ```python
   ids, distances = await qdrant_db.query(queries, top_k)
   ```
   Performs standard similarity search returning IDs and scores.

3. **Enhanced Querying with Payload**:
   ```python
   results_with_payload, scores = await qdrant_db.query_with_payload(queries, top_k)
   
   # Access rich results
   for result, score in zip(results_with_payload[0], scores[0]):
       doc_id = result["id"]
       payload = result["payload"]
       original_text = payload.get("text", "")
       title = payload.get("title", "Unknown")
       author = payload.get("author", "Unknown")
       print(f"{title} by {author}: {original_text[:100]}...")
   ```
   Returns comprehensive results with all stored metadata and text content.

4. **Fetching Vectors**:
   ```python
   vectors = await qdrant_db.fetch(ids)
   ```
   Retrieves the vectors associated with the given IDs.

5. **Fetching with Payload**:
   ```python
   documents = await qdrant_db.fetch_with_payload(ids)
   
   # Access complete document data
   for doc in documents:
       print(f"ID: {doc['id']}")
       print(f"Vector dimension: {len(doc['vector'])}")
       print(f"Text: {doc['payload'].get('text', 'No text')}")
       print(f"Metadata: {doc['payload']}")
   ```
   Retrieves complete document information including vectors and all metadata.

6. **Checking Existence**:
   ```python
   exists = await qdrant_db.is_exist(ids)
   ```
   Checks if the given IDs exist in the database.

7. **Deleting Vectors**:
   ```python
   await qdrant_db.delete(ids)
   ```
   Deletes the vectors associated with the given IDs from the database.

8. **Deleting the Collection**:
   ```python
   qdrant_db.delete_collection()
   ```
   Deletes the collection from the Qdrant server.

### **Payload vs External Storage Comparison**

| Feature | Qdrant Payload | External Index Table |
|---------|----------------|---------------------|
| **Storage** | Self-contained in Qdrant | Separate database |
| **Query Speed** | ✅ Fast (single query) | ⚠️ Slower (join required) |
| **Metadata Richness** | ✅ Unlimited JSON | ⚠️ Schema constraints |
| **Text Access** | ✅ Immediate | ❌ Requires file lookup |
| **Scalability** | ✅ Distributed with Qdrant | ⚠️ Depends on DB |
| **Data Consistency** | ✅ Atomic operations | ⚠️ Eventual consistency |
| **Storage Overhead** | ⚠️ Higher (duplicated text) | ✅ Lower (references only) |

### **When to Use Payload Storage**

**✅ Recommended for:**
- Rich metadata requirements (authors, categories, tags)
- Fast search with immediate content access
- Self-contained applications
- Distributed deployments
- Dynamic metadata schemas

**⚠️ Consider alternatives for:**
- Very large documents (>10KB per chunk)
- Minimal metadata needs
- Storage cost optimization
- Legacy system integration
