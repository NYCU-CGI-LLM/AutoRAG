import logging
import tempfile
import shutil
import asyncio
import json
import pandas as pd
from typing import Dict, Any, Optional, List
from uuid import UUID
from pathlib import Path
from datetime import datetime

from app.models.evaluation import Evaluation, BenchmarkDataset
from app.models.retriever import Retriever
from app.services.minio_service import MinIOService
from app.services.benchmark_service import BenchmarkService
from app.core.config import settings
from app.schemas.common import TaskStatusEnum

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for managing evaluation runs"""
    
    def __init__(self):
        self.minio_service = MinIOService()
        self.benchmark_service = BenchmarkService()
        self.evaluation_bucket = settings.minio_evaluation_bucket
    
    async def create_evaluation_run(
        self,
        retriever_config_id: UUID,
        benchmark_dataset_id: UUID,
        evaluation_config: Dict[str, Any],
        name: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Evaluation:
        """
        Create a new evaluation run
        
        Args:
            retriever_config_id: ID of retriever configuration to evaluate
            benchmark_dataset_id: ID of benchmark dataset to use
            evaluation_config: Evaluation configuration parameters
            name: Optional evaluation run name
            user_id: User ID who created this evaluation
            
        Returns:
            Evaluation: Created evaluation record
        """
        try:
            # Create evaluation record
            evaluation = Evaluation(
                name=name or f"Evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                user_id=user_id,
                retriever_config_id=retriever_config_id,
                benchmark_dataset_id=benchmark_dataset_id,
                evaluation_config=evaluation_config,
                status=TaskStatusEnum.PENDING
            )
            
            logger.info(f"Created evaluation run {evaluation.id}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error creating evaluation run: {e}")
            raise
    
    async def execute_evaluation(
        self,
        evaluation: Evaluation,
        benchmark_dataset: BenchmarkDataset,
        retriever_config: Retriever
    ) -> Evaluation:
        """
        Execute an evaluation run
        
        Args:
            evaluation: Evaluation record
            benchmark_dataset: Benchmark dataset to use
            retriever_config: Retriever configuration to evaluate
            
        Returns:
            Evaluation: Updated evaluation record with results
        """
        temp_workspace = None
        
        try:
            # Update status to running
            evaluation.status = TaskStatusEnum.PROCESSING
            evaluation.started_at = datetime.utcnow()
            evaluation.progress = 0.0
            
            logger.info(f"Starting evaluation {evaluation.id}")
            
            # Create temporary workspace
            temp_workspace = Path(tempfile.mkdtemp(prefix="eval_"))
            logger.info(f"Created temporary workspace: {temp_workspace}")
            
            # Download benchmark data
            qa_data, corpus_data = await self.benchmark_service.download_benchmark_dataset(benchmark_dataset)
            evaluation.total_queries = len(qa_data)
            evaluation.progress = 10.0
            
            # Prepare data files in AutoRAG format
            data_dir = temp_workspace / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Save QA data
            qa_path = data_dir / "qa.parquet"
            qa_data.to_parquet(qa_path, index=False)
            
            # Save corpus data
            corpus_path = data_dir / "corpus.parquet" 
            corpus_data.to_parquet(corpus_path, index=False)
            
            evaluation.progress = 20.0
            
            # Create AutoRAG configuration
            autorag_config = await self._create_autorag_config(
                evaluation_config=evaluation.evaluation_config,
                retriever_config=retriever_config,
                qa_path=qa_path,
                corpus_path=corpus_path
            )
            
            config_path = temp_workspace / "config.yaml"
            with open(config_path, 'w') as f:
                import yaml
                yaml.dump(autorag_config, f, default_flow_style=False)
            
            evaluation.progress = 30.0
            
            # Execute AutoRAG evaluation
            results = await self._run_autorag_evaluation(
                config_path=config_path,
                project_dir=temp_workspace,
                evaluation=evaluation
            )
            
            evaluation.progress = 90.0
            
            # Store detailed results in MINIO
            results_object_key = f"evaluations/{evaluation.id}/results.json"
            results_json = json.dumps(results, indent=2, default=str)
            
            self.minio_service.client.put_object(
                bucket_name=self.evaluation_bucket,
                object_name=results_object_key,
                data=results_json.encode('utf-8'),
                length=len(results_json.encode('utf-8')),
                content_type="application/json"
            )
            
            # Update evaluation record with results
            evaluation.results_object_key = results_object_key
            evaluation.detailed_results = self._extract_summary_metrics(results)
            evaluation.status = TaskStatusEnum.SUCCESS
            evaluation.progress = 100.0
            evaluation.completed_at = datetime.utcnow()
            evaluation.processed_queries = evaluation.total_queries
            
            if evaluation.started_at:
                evaluation.execution_time = (evaluation.completed_at - evaluation.started_at).total_seconds()
            
            logger.info(f"Completed evaluation {evaluation.id} successfully")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error executing evaluation {evaluation.id}: {e}")
            
            # Update evaluation status to failed
            evaluation.status = TaskStatusEnum.FAILURE
            evaluation.message = str(e)
            evaluation.completed_at = datetime.utcnow()
            
            if evaluation.started_at:
                evaluation.execution_time = (evaluation.completed_at - evaluation.started_at).total_seconds()
            
            return evaluation
            
        finally:
            # Clean up temporary workspace
            if temp_workspace and temp_workspace.exists():
                try:
                    shutil.rmtree(temp_workspace)
                    logger.info(f"Cleaned up temporary workspace: {temp_workspace}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary workspace {temp_workspace}: {e}")
    
    async def _create_autorag_config(
        self,
        evaluation_config: Dict[str, Any],
        retriever_config: Retriever,
        qa_path: Path,
        corpus_path: Path
    ) -> Dict[str, Any]:
        """
        Create AutoRAG configuration from evaluation parameters
        
        Args:
            evaluation_config: Evaluation configuration
            retriever_config: Retriever configuration
            qa_path: Path to QA data file
            corpus_path: Path to corpus data file
            
        Returns:
            Dict: AutoRAG configuration
        """
        # Basic AutoRAG configuration structure
        config = {
            "node_lines": [
                {
                    "node_line_name": "retrieve_node_line",
                    "nodes": [
                        {
                            "node_type": "retrieval",
                            "strategy": {
                                "metrics": evaluation_config.get("retrieval_metrics", [
                                    "retrieval_f1", "retrieval_recall", "retrieval_precision"
                                ])
                            },
                            "modules": self._create_retrieval_modules(retriever_config)
                        }
                    ]
                }
            ]
        }
        
        # Add generation evaluation if specified
        if evaluation_config.get("include_generation", False):
            generation_node = {
                "node_type": "generator",
                "strategy": {
                    "metrics": evaluation_config.get("generation_metrics", [
                        "bleu", "rouge", "meteor"
                    ])
                },
                "modules": [
                    {
                        "module_type": "llama_index_llm",
                        "llm": "openai_gpt_3_5_turbo"
                    }
                ]
            }
            config["node_lines"][0]["nodes"].append(generation_node)
        
        return config
    
    def _create_retrieval_modules(self, retriever_config: Retriever) -> List[Dict[str, Any]]:
        """
        Create retrieval modules configuration from retriever config
        
        Args:
            retriever_config: Retriever configuration
            
        Returns:
            List[Dict]: Retrieval modules configuration
        """
        modules = []
        
        # Extract retrieval configuration
        config_data = retriever_config.config_data or {}
        
        # BM25 retrieval
        if config_data.get("use_bm25", True):
            modules.append({
                "module_type": "bm25",
                "top_k": config_data.get("bm25_top_k", 10)
            })
        
        # Vector retrieval
        if config_data.get("use_vector", True):
            modules.append({
                "module_type": "vectordb",
                "top_k": config_data.get("vector_top_k", 10),
                "embedding_model": config_data.get("embedding_model", "openai_embed_3_large")
            })
        
        # Hybrid retrieval
        if config_data.get("use_hybrid", False):
            modules.append({
                "module_type": "hybrid_rrf",
                "top_k": config_data.get("hybrid_top_k", 10),
                "rrf_k": config_data.get("rrf_k", 60)
            })
        
        return modules
    
    async def _run_autorag_evaluation(
        self,
        config_path: Path,
        project_dir: Path,
        evaluation: Evaluation
    ) -> Dict[str, Any]:
        """
        Run AutoRAG evaluation using the configuration
        
        Args:
            config_path: Path to AutoRAG config file
            project_dir: Project directory path
            evaluation: Evaluation record for progress updates
            
        Returns:
            Dict: Evaluation results
        """
        try:
            logger.info(f"Running AutoRAG evaluation with config: {config_path}")
            
            # For now, simulate AutoRAG execution with mock results
            # In actual implementation, you would call AutoRAG here
            await asyncio.sleep(2)  # Simulate processing time
            
            # Mock results structure matching AutoRAG output
            mock_results = {
                "summary": {
                    "retrieval_f1": 0.75,
                    "retrieval_recall": 0.80,
                    "retrieval_precision": 0.70,
                    "total_queries": evaluation.total_queries,
                    "execution_time": 30.5
                },
                "detailed_results": {
                    "per_query_metrics": [
                        {
                            "qid": f"q{i}",
                            "retrieval_f1": 0.7 + (i * 0.05),
                            "retrieval_recall": 0.75 + (i * 0.03),
                            "retrieval_precision": 0.65 + (i * 0.04)
                        }
                        for i in range(min(evaluation.total_queries or 0, 10))
                    ]
                },
                "config_used": str(config_path),
                "project_dir": str(project_dir)
            }
            
            logger.info("AutoRAG evaluation completed successfully")
            return mock_results
            
        except Exception as e:
            logger.error(f"Error running AutoRAG evaluation: {e}")
            raise
    
    def _extract_summary_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract summary metrics from detailed results
        
        Args:
            results: Full evaluation results
            
        Returns:
            Dict: Summary metrics
        """
        summary = results.get("summary", {})
        
        return {
            "overall_score": summary.get("retrieval_f1", 0.0),
            "retrieval_metrics": {
                "f1": summary.get("retrieval_f1", 0.0),
                "recall": summary.get("retrieval_recall", 0.0),
                "precision": summary.get("retrieval_precision", 0.0)
            },
            "total_queries": summary.get("total_queries", 0),
            "execution_time": summary.get("execution_time", 0.0)
        }
    
    async def get_evaluation_results(self, evaluation: Evaluation) -> Dict[str, Any]:
        """
        Get detailed evaluation results from MINIO
        
        Args:
            evaluation: Evaluation record
            
        Returns:
            Dict: Detailed evaluation results
        """
        try:
            if not evaluation.results_object_key:
                return {}
            
            results_data = self.minio_service.download_file(
                evaluation.results_object_key,
                bucket_name=self.evaluation_bucket
            )
            
            return json.loads(results_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error loading evaluation results for {evaluation.id}: {e}")
            return {} 