from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel, TaskStatusEnum


class EvaluationBase(BaseModel):
    name: Optional[str] = Field(None, description="Evaluation run name")
    retriever_config_id: Optional[UUID] = Field(None, description="Associated retriever configuration ID (optional)")
    evaluation_config: Dict[str, Any] = Field(..., description="Evaluation configuration parameters")
    dataset_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dataset configuration")


class EvaluationCreate(BaseModel):
    name: Optional[str] = Field(None, description="Evaluation run name")
    benchmark_dataset_id: UUID = Field(..., description="Benchmark dataset ID to use for evaluation")
    evaluation_config: Dict[str, Any] = Field(
        default_factory=lambda: EvaluationConfigSchema().model_dump(),
        description="Evaluation configuration parameters",
        example={
            "embedding_model": "openai_embed_3_large",
            "retrieval_strategy": {
                "metrics": ["retrieval_f1", "retrieval_recall", "retrieval_precision"],
                "top_k": 10
            },
            "generation_strategy": {
                "metrics": [
                    {"metric_name": "bleu"},
                    {"metric_name": "rouge"},
                    {"metric_name": "meteor"}
                ]
            },
            "generator_config": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 512,
                "batch": 16
            },
            "prompt_template": "Read the passages and answer the given question.\n\nQuestion: {query}\n\nPassages: {retrieved_contents}\n\nAnswer: "
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Evaluation Run",
                "benchmark_dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "evaluation_config": {
                    "embedding_model": "openai_embed_3_large",
                    "retrieval_strategy": {
                        "metrics": ["retrieval_f1", "retrieval_recall", "retrieval_precision"],
                        "top_k": 10
                    },
                    "generation_strategy": {
                        "metrics": [
                            {"metric_name": "bleu"},
                            {"metric_name": "rouge"},
                            {"metric_name": "meteor"}
                        ]
                    },
                    "generator_config": {
                        "model": "gpt-4o-mini",
                        "temperature": 0.7,
                        "max_tokens": 512,
                        "batch": 16
                    },
                    "prompt_template": "Read the passages and answer the given question.\n\nQuestion: {query}\n\nPassages: {retrieved_contents}\n\nAnswer: "
                }
            }
        }


class EvaluationConfigSchema(BaseModel):
    """
    Simplified evaluation configuration schema for AutoRAG
    """
    # Embedding model selection (restricted to OpenAI models)
    embedding_model: str = Field(
        default="openai_embed_3_large",
        description="Embedding model to use",
        pattern="^(openai_embed_3_large|openai_embed_3_small)$"
    )
    

    
    # Retrieval strategy configuration
    retrieval_strategy: Dict[str, Any] = Field(
        default={
            "metrics": ["retrieval_f1", "retrieval_recall", "retrieval_precision"],
            "top_k": 10
        },
        description="Retrieval evaluation strategy"
    )
    
    # Generation strategy configuration
    generation_strategy: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "metrics": [
                {"metric_name": "bleu"},
                {"metric_name": "rouge"},
                {"metric_name": "meteor"}
            ]
        },
        description="Generation evaluation strategy"
    )
    
    # Generator configuration (OpenAI LLM only)
    generator_config: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 512,
            "batch": 16
        },
        description="OpenAI LLM configuration"
    )
    
    # Prompt template
    prompt_template: Optional[str] = Field(
        default="Read the passages and answer the given question.\n\n"
                "Question: {query}\n\n"
                "Passages: {retrieved_contents}\n\n"
                "Answer: ",
        description="Prompt template for generation"
    )


class EvaluationConfigExample(BaseModel):
    """Example evaluation configuration"""
    example_basic: EvaluationConfigSchema = Field(
        default_factory=lambda: EvaluationConfigSchema(),
        description="Basic evaluation configuration"
    )
    
    example_advanced: EvaluationConfigSchema = Field(
        default_factory=lambda: EvaluationConfigSchema(
            embedding_model="openai_embed_3_small",
            retrieval_strategy={
                "metrics": ["retrieval_f1", "retrieval_recall", "retrieval_precision", "retrieval_ndcg"],
                "top_k": 15
            },
            generation_strategy={
                "metrics": [
                    {"metric_name": "bleu"},
                    {"metric_name": "rouge"},
                    {"metric_name": "meteor"},
                    {"metric_name": "sem_score", "embedding_model": "openai"}
                ]
            },
            generator_config={
                "model": "gpt-4o",
                "temperature": 0.3,
                "max_tokens": 1024,
                "batch": 8
            },
            prompt_template="You are a helpful assistant. Answer the following question based on the provided context.\n\n"
                           "Question: {query}\n\n"
                           "Context:\n{retrieved_contents}\n\n"
                           "Please provide a comprehensive and accurate answer:"
        ),
        description="Advanced evaluation configuration"
    )


class Evaluation(EvaluationBase, IDModel, TimestampModel):
    status: TaskStatusEnum = Field(default=TaskStatusEnum.PENDING, description="Evaluation status")
    progress: Optional[float] = Field(default=0.0, description="Evaluation progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    total_queries: Optional[int] = Field(None, description="Total number of queries to evaluate")
    processed_queries: Optional[int] = Field(default=0, description="Number of processed queries")
    
    class Config:
        from_attributes = True


class EvaluationResult(BaseModel):
    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    description: Optional[str] = Field(None, description="Metric description")


class EvaluationDetail(Evaluation):
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name")
    results: List[EvaluationResult] = Field(default_factory=list, description="Evaluation results")
    detailed_results: Optional[Dict[str, Any]] = Field(None, description="Detailed evaluation results")
    execution_time: Optional[float] = Field(None, description="Total execution time in seconds")


class EvaluationSummary(BaseModel):
    id: UUID = Field(..., description="Evaluation ID")
    name: Optional[str] = Field(None, description="Evaluation name")
    status: TaskStatusEnum = Field(..., description="Evaluation status")
    progress: Optional[float] = Field(None, description="Progress percentage")
    created_at: datetime = Field(..., description="Creation timestamp")
    retriever_config_name: Optional[str] = Field(None, description="Retriever configuration name")
    overall_score: Optional[float] = Field(None, description="Overall evaluation score")


class EvaluationStatusUpdate(BaseModel):
    status: TaskStatusEnum = Field(..., description="Current evaluation status")
    progress: Optional[float] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    processed_queries: Optional[int] = Field(None, description="Number of processed queries")


class EvaluationMetrics(BaseModel):
    precision: Optional[float] = Field(None, description="Precision score")
    recall: Optional[float] = Field(None, description="Recall score")
    f1_score: Optional[float] = Field(None, description="F1 score")
    ndcg: Optional[float] = Field(None, description="NDCG score")
    mrr: Optional[float] = Field(None, description="Mean Reciprocal Rank")
    map_score: Optional[float] = Field(None, description="Mean Average Precision")
    custom_metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Custom metrics")


# Benchmark Dataset Schemas
class BenchmarkDatasetBase(BaseModel):
    name: str = Field(..., description="Benchmark dataset name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Dataset description", max_length=500)
    domain: Optional[str] = Field(None, description="Domain/topic of the dataset", max_length=50)
    language: str = Field(default="en", description="Dataset language code", max_length=10)
    version: str = Field(default="1.0", description="Dataset version", max_length=20)
    evaluation_metrics: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "retrieval": ["retrieval_f1", "retrieval_recall", "retrieval_precision"],
            "generation": ["bleu", "rouge", "meteor"]
        },
        description="Default evaluation metrics for this dataset"
    )


class BenchmarkDatasetCreate(BenchmarkDatasetBase):
    """Schema for creating a new benchmark dataset via file upload"""
    pass


class BenchmarkDatasetUpdate(BaseModel):
    """Schema for updating benchmark dataset metadata"""
    name: Optional[str] = Field(None, description="Benchmark dataset name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Dataset description", max_length=500)
    domain: Optional[str] = Field(None, description="Domain/topic of the dataset", max_length=50)
    language: Optional[str] = Field(None, description="Dataset language code", max_length=10)
    version: Optional[str] = Field(None, description="Dataset version", max_length=20)
    evaluation_metrics: Optional[Dict[str, Any]] = Field(None, description="Default evaluation metrics")
    is_active: Optional[bool] = Field(None, description="Whether the dataset is active")


class BenchmarkDataset(BenchmarkDatasetBase, IDModel, TimestampModel):
    """Complete benchmark dataset with all fields"""
    total_queries: int = Field(..., description="Total number of queries in dataset")
    qa_data_object_key: str = Field(..., description="MinIO object key for QA data")
    corpus_data_object_key: str = Field(..., description="MinIO object key for corpus data")
    is_active: bool = Field(default=True, description="Whether this dataset is active/available")
    
    class Config:
        from_attributes = True


class BenchmarkDatasetDetail(BenchmarkDataset):
    """Detailed benchmark dataset with additional statistics"""
    file_info: Optional[Dict[str, Any]] = Field(None, description="File size and metadata information")
    sample_data: Optional[Dict[str, Any]] = Field(None, description="Sample QA and corpus data for preview")


class BenchmarkDatasetSummary(BaseModel):
    """Summary view of benchmark dataset for listing"""
    id: UUID = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    domain: Optional[str] = Field(None, description="Dataset domain")
    language: str = Field(..., description="Dataset language")
    version: str = Field(..., description="Dataset version")
    total_queries: int = Field(..., description="Total number of queries")
    is_active: bool = Field(..., description="Whether dataset is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp") 