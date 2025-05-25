from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from .common import OrmBase, IDModel, TimestampModel, TaskStatusEnum


class EvaluationBase(BaseModel):
    name: Optional[str] = Field(None, description="Evaluation run name")
    retriever_config_id: UUID = Field(..., description="Associated retriever configuration ID")
    evaluation_config: Dict[str, Any] = Field(..., description="Evaluation configuration parameters")
    dataset_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dataset configuration")


class EvaluationCreate(EvaluationBase):
    pass


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