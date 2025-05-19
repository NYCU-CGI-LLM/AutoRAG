from pydantic import BaseModel, Field, model_validator, ValidationInfo
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime

from .common import IDModel, TimestampModel, OrmBase, TaskStatusEnum

# --- BM25 Options ---
class BM25Options(OrmBase):
    tokenizer: str = Field(
        default="porter_stemmer",
        description="Tokenizer for BM25. E.g., 'porter_stemmer', 'ko_kiwi', or a HuggingFace tokenizer name."
    )

# --- Embedding Options ---
class EmbeddingModelConfig(OrmBase):
    model_config = {'protected_namespaces': ()} # Added to allow 'model_name'
    type: Literal["openai", "huggingface"] = "huggingface"
    model_name: str
    # Potentially other params like api_key_env_var for OpenAI

class VectorDBConfig(OrmBase):
    type: Literal["chroma", "faiss"] = "chroma" # Add more as supported by autorag
    embedding_model: EmbeddingModelConfig
    persist_path: str = Field(default="../index/vector_store", description="Relative path from variation's config dir to persist vector store.")
    # Other DB specific params, e.g., collection_name for Chroma

class EmbeddingOptions(OrmBase):
    # Option 1: API generates vectordb.yaml based on these simple fields
    # embedding_model_name: Optional[str] = None 
    # vector_store_type: Optional[Literal["chroma", "faiss"]] = None

    # Option 2: User provides the content for the variation's vectordb.yaml
    # The key in this dict will be the 'vectordb_name' to load from autorag.vectordb.load_vectordb_from_yaml
    vectordb_configs: Dict[str, VectorDBConfig]
    default_vectordb_config_name: str # Specifies which config in vectordb_configs is the default/primary

    @model_validator(mode='after')
    def check_default_config_in_configs(self) -> 'EmbeddingOptions':
        if not self.vectordb_configs:
            raise ValueError('vectordb_configs cannot be empty')
        if self.default_vectordb_config_name not in self.vectordb_configs:
            raise ValueError('default_vectordb_config_name must be a key in vectordb_configs')
        return self

# --- Indexer Configuration ---
class IndexerConfigBase(OrmBase):
    method: Literal["bm25", "embedding"]
    bm25_options: Optional[BM25Options] = None
    embedding_options: Optional[EmbeddingOptions] = None

    @model_validator(mode='after')
    def check_options_dependencies(self) -> 'IndexerConfigBase':
        if self.method == 'bm25':
            if self.embedding_options is not None:
                raise ValueError("embedding_options should not be provided if method is 'bm25'")
            if self.bm25_options is None:
                self.bm25_options = BM25Options()
        elif self.method == 'embedding':
            if self.bm25_options is not None:
                raise ValueError("bm25_options should not be provided if method is 'embedding'")
            if self.embedding_options is None:
                raise ValueError("embedding_options are required for embedding method")
        return self

# --- Variation Schemas ---
class VariationBase(OrmBase):
    name: str
    description: Optional[str] = None

class VariationCreate(VariationBase):
    indexer_config: IndexerConfigBase

class Variation(VariationBase, IDModel, TimestampModel):
    knowledge_base_id: UUID
    indexer_config: IndexerConfigBase
    status: TaskStatusEnum = TaskStatusEnum.PENDING # Status of the indexing job

class VariationSummary(VariationBase, IDModel):
    status: TaskStatusEnum
    method: str # 'bm25' or 'embedding' 