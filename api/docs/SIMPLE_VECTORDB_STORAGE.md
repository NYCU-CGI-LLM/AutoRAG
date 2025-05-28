# Simple Vector Database Storage Strategy

## 🎯 架构概述

基于当前需求，采用简化的单层存储架构：**ChromaDB + PostgreSQL**

```
┌─────────────────────────────────────────────────────────────┐
│                   简化存储架构                                │
├─────────────────────────────────────────────────────────────┤
│ 🌡️ ChromaDB (Vector Storage)                               │
│    • 存储: embedding向量 + doc_id + metadata                │
│    • 用途: 相似性搜索、语义检索                               │
│    • 位置: ./resources/chroma/                              │
├─────────────────────────────────────────────────────────────┤
│ 📊 PostgreSQL (Metadata Management)                        │
│    • 存储: 文档关系、索引配置、统计信息                        │
│    • 用途: 管理embedding与业务数据的关联                       │
│    • 不存储: 实际的embedding向量                             │
└─────────────────────────────────────────────────────────────┘
```

## 🗄️ ChromaDB存储设计

### 1. Collection命名策略

```python
# 按业务和模型分组
collection_name = f"{library_id}_{embedding_model}"

# 示例
"library_123_openai_embed_3_large"
"library_456_openai_embed_3_large" 
"library_123_bge_m3"
```

### 2. 数据存储格式

```python
# ChromaDB中的数据结构
{
    "ids": ["doc_uuid_1", "doc_uuid_2", ...],
    "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
    "metadatas": [
        {
            "doc_id": "doc_uuid_1",
            "library_id": "library_123", 
            "chunk_index": 0,
            "content_hash": "sha256_hash",
            "embedding_model": "openai_embed_3_large",
            "created_at": "2024-01-01T12:00:00Z",
            "content_preview": "This is the first 100 chars..."  # 便于调试
        },
        ...
    ],
    "documents": [
        "完整的文档内容...",  # 可选：存储原文便于检索
        ...
    ]
}
```

### 3. 配置文件

```yaml
# config/vectordb.yaml
vectordb:
  - name: api_chroma
    db_type: chroma
    client_type: persistent
    embedding_model: openai_embed_3_large
    collection_name: "{library_id}_{embedding_model}"  # 动态生成
    path: ${PROJECT_DIR}/resources/chroma
    similarity_metric: cosine
    embedding_batch: 100
```

## 🔗 与PostgreSQL的关联

### 1. 数据库表设计

```sql
-- 扩展现有的indexer表，添加vector相关字段
ALTER TABLE indexer ADD COLUMN IF NOT EXISTS collection_name VARCHAR(255);
ALTER TABLE indexer ADD COLUMN IF NOT EXISTS vector_dimension INTEGER;
ALTER TABLE indexer ADD COLUMN IF NOT EXISTS total_vectors INTEGER DEFAULT 0;

-- 创建embedding统计表
CREATE TABLE IF NOT EXISTS embedding_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    library_id UUID NOT NULL REFERENCES library(id) ON DELETE CASCADE,
    indexer_id UUID NOT NULL REFERENCES indexer(id) ON DELETE CASCADE,
    collection_name VARCHAR(255) NOT NULL,
    embedding_model VARCHAR(255) NOT NULL,
    total_documents INTEGER DEFAULT 0,
    vector_dimension INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(library_id, indexer_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_embedding_stats_library ON embedding_stats(library_id);
CREATE INDEX IF NOT EXISTS idx_embedding_stats_collection ON embedding_stats(collection_name);
```

### 2. 关联关系

```python
# 数据流向
1. 用户上传文档 → File表
2. 解析文档 → FileParseResult表  
3. 分块处理 → FileChunkResult表
4. 创建embedding → ChromaDB + embedding_stats表
5. 检索查询 → ChromaDB搜索 + PostgreSQL关联
```

## 🚀 API实现

### 1. 存储Embedding

```python
class VectorDBService:
    def __init__(self):
        self.chroma_client = self._init_chroma()
    
    def store_embeddings(
        self,
        library_id: UUID,
        doc_ids: List[str],
        contents: List[str],
        embedding_model: str = "openai_embed_3_large"
    ) -> Dict[str, Any]:
        """存储embedding到ChromaDB"""
        
        # 1. 生成collection名称
        collection_name = f"lib_{library_id}_{embedding_model}"
        
        # 2. 获取或创建collection
        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 3. 准备metadata
        metadatas = []
        for i, (doc_id, content) in enumerate(zip(doc_ids, contents)):
            metadatas.append({
                "doc_id": doc_id,
                "library_id": str(library_id),
                "chunk_index": i,
                "embedding_model": embedding_model,
                "created_at": datetime.utcnow().isoformat(),
                "content_preview": content[:100] + "..." if len(content) > 100 else content
            })
        
        # 4. 添加到ChromaDB (自动生成embedding)
        collection.add(
            ids=doc_ids,
            documents=contents,  # ChromaDB会自动生成embedding
            metadatas=metadatas
        )
        
        # 5. 更新PostgreSQL统计
        self._update_embedding_stats(
            library_id, collection_name, embedding_model, len(doc_ids)
        )
        
        return {
            "collection_name": collection_name,
            "total_documents": len(doc_ids),
            "embedding_model": embedding_model
        }
```

### 2. 相似性搜索

```python
def similarity_search(
    self,
    library_id: UUID,
    query: str,
    top_k: int = 10,
    embedding_model: str = "openai_embed_3_large",
    filters: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """在指定library中搜索相似文档"""
    
    # 1. 构建collection名称
    collection_name = f"lib_{library_id}_{embedding_model}"
    
    # 2. 获取collection
    try:
        collection = self.chroma_client.get_collection(collection_name)
    except Exception:
        return []  # Collection不存在
    
    # 3. 构建查询过滤器
    where_filter = {"library_id": str(library_id)}
    if filters:
        where_filter.update(filters)
    
    # 4. 执行搜索
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    # 5. 格式化结果
    search_results = []
    for i in range(len(results["ids"][0])):
        search_results.append({
            "doc_id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1 - results["distances"][0][i],  # 转换为相似度分数
            "rank": i + 1
        })
    
    return search_results
```

### 3. 管理API

```python
@router.get("/v1/library/{library_id}/embeddings/stats")
async def get_embedding_stats(
    library_id: UUID,
    session: Session = Depends(get_session)
):
    """获取library的embedding统计信息"""
    
    stats = session.exec(
        select(EmbeddingStats).where(EmbeddingStats.library_id == library_id)
    ).all()
    
    return {
        "library_id": library_id,
        "collections": [
            {
                "collection_name": stat.collection_name,
                "embedding_model": stat.embedding_model,
                "total_documents": stat.total_documents,
                "vector_dimension": stat.vector_dimension,
                "created_at": stat.created_at
            }
            for stat in stats
        ]
    }

@router.post("/v1/library/{library_id}/embeddings/search")
async def search_embeddings(
    library_id: UUID,
    request: SearchRequest,
    vectordb_service: VectorDBService = Depends()
):
    """在library中搜索相似文档"""
    
    results = vectordb_service.similarity_search(
        library_id=library_id,
        query=request.query,
        top_k=request.top_k,
        embedding_model=request.embedding_model,
        filters=request.filters
    )
    
    return {
        "query": request.query,
        "library_id": library_id,
        "total_results": len(results),
        "results": results
    }
```

## 📁 文件组织结构

```
api/
├── app/
│   ├── services/
│   │   ├── vectordb_service.py      # ChromaDB操作服务
│   │   └── embedding_service.py     # Embedding管理服务
│   ├── models/
│   │   └── embedding_stats.py       # Embedding统计模型
│   └── routers/
│       └── embeddings.py            # Embedding相关API
├── config/
│   └── vectordb.yaml               # ChromaDB配置
└── resources/
    └── chroma/                      # ChromaDB数据存储目录
        ├── lib_123_openai_embed_3_large/
        ├── lib_456_openai_embed_3_large/
        └── ...
```

## 🔧 配置示例

```python
# app/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # ChromaDB Configuration
    chroma_path: str = Field("./resources/chroma", env="CHROMA_PATH")
    default_embedding_model: str = Field("openai_embed_3_large", env="DEFAULT_EMBEDDING_MODEL")
    embedding_batch_size: int = Field(100, env="EMBEDDING_BATCH_SIZE")
```

## 💡 使用建议

### 1. Collection管理策略

```python
# 按library分离，避免数据混淆
collection_name = f"lib_{library_id}_{embedding_model}"

# 优势：
- 数据隔离：不同library的数据完全分离
- 权限控制：可以基于library_id控制访问
- 性能优化：搜索范围限定在特定library
- 易于管理：可以独立删除某个library的所有embedding
```

### 2. 性能优化

```python
# 批量操作
def batch_add_embeddings(doc_ids: List[str], contents: List[str], batch_size: int = 100):
    for i in range(0, len(doc_ids), batch_size):
        batch_ids = doc_ids[i:i+batch_size]
        batch_contents = contents[i:i+batch_size]
        collection.add(ids=batch_ids, documents=batch_contents)

# 异步处理大量数据
async def async_embedding_creation(library_id: UUID, file_chunks: List[Dict]):
    # 后台任务处理大量embedding创建
    pass
```

### 3. 监控和维护

```python
# 定期清理和优化
def maintenance_tasks():
    # 1. 清理孤立的collection
    # 2. 压缩数据库
    # 3. 更新统计信息
    # 4. 检查数据一致性
    pass
```

## 📈 扩展考虑

当数据量增长时，可以考虑：

1. **水平分片** - 按时间或hash分割collection
2. **读写分离** - 使用多个ChromaDB实例
3. **升级到Qdrant** - 更好的性能和集群支持
4. **添加缓存层** - Redis缓存热门查询结果

但目前的简化架构足以支撑大多数API服务的需求。 