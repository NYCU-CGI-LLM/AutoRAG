from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

from app.schemas.common import TaskStatusEnum


class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Evaluation(SQLModel, table=True):
    __tablename__ = "evaluations"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Basic information
    name: Optional[str] = Field(default=None, description="Evaluation run name")
    user_id: Optional[str] = Field(default=None, description="User ID who created this evaluation")
    
    # Related entities
    retriever_config_id: Optional[UUID] = Field(default=None, description="Associated retriever configuration ID (optional)")
    benchmark_dataset_id: Optional[UUID] = Field(default=None, description="Benchmark dataset ID")
    
    # Configuration
    evaluation_config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Evaluation configuration parameters")
    dataset_config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Dataset configuration")
    
    # Status and progress
    status: TaskStatusEnum = Field(default=TaskStatusEnum.PENDING, description="Evaluation status")
    progress: float = Field(default=0.0, description="Evaluation progress percentage")
    message: Optional[str] = Field(default=None, description="Status message")
    
    # Query processing
    total_queries: Optional[int] = Field(default=None, description="Total number of queries to evaluate")
    processed_queries: int = Field(default=0, description="Number of processed queries")
    
    # Results storage
    results_object_key: Optional[str] = Field(default=None, description="MINIO object key for detailed results")
    detailed_results: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Summary of evaluation results")
    
    # Performance metrics
    execution_time: Optional[float] = Field(default=None, description="Total execution time in seconds")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None, description="When evaluation actually started")
    completed_at: Optional[datetime] = Field(default=None, description="When evaluation completed")


class BenchmarkDataset(SQLModel, table=True):
    __tablename__ = "benchmark_datasets"
    
    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # Basic information
    name: str = Field(..., description="Benchmark dataset name")
    description: Optional[str] = Field(default=None, description="Dataset description")
    version: str = Field(default="1.0", description="Dataset version")
    
    # Dataset metadata
    domain: Optional[str] = Field(default=None, description="Domain/topic of the dataset")
    language: str = Field(default="en", description="Dataset language")
    total_queries: int = Field(..., description="Total number of queries in dataset")
    
    # Storage information
    qa_data_object_key: str = Field(..., description="MINIO object key for QA data")
    corpus_data_object_key: str = Field(..., description="MINIO object key for corpus data")
    
    # Configuration
    evaluation_metrics: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Default evaluation metrics for this dataset")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    is_active: bool = Field(default=True, description="Whether this dataset is active/available") 