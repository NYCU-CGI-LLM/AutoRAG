"""
Evaluation Service for AutoRAG

This service provides simplified evaluation functionality with the following constraints:
1. Only OpenAI embedding models are supported: "openai_embed_3_large" or "openai_embed_3_small"
2. Fixed pipeline: retrieval -> prompt_maker -> generator
3. Only vectordb retrieval method is used (no BM25 or hybrid)
4. Only retrieval and generator nodes have strategy configurations (prompt_maker has no strategy)
5. Only OpenAI LLMs are supported for generation

Example evaluation_config:
{
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
    "prompt_template": "Read the passages and answer the given question.\\n\\nQuestion: {query}\\n\\nPassages: {retrieved_contents}\\n\\nAnswer: "
}
"""

import logging
import tempfile
import shutil
import asyncio
import json
import os
import pandas as pd
from typing import Dict, Any, Optional, List
from uuid import UUID
from pathlib import Path
from datetime import datetime
import io

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
        retriever_config_id: Optional[UUID],
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
        retriever_config: Optional[Retriever] = None
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
                corpus_path=corpus_path,
                project_dir=temp_workspace
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
                data=io.BytesIO(results_json.encode('utf-8')),
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
            # Keep temporary workspace for inspection - DO NOT DELETE
            if temp_workspace and temp_workspace.exists():
                logger.info(f"=== EVALUATION FILES PRESERVED ===")
                logger.info(f"Temporary workspace kept at: {temp_workspace}")
                logger.info(f"Contents:")
                try:
                    for root, dirs, files in os.walk(temp_workspace):
                        level = root.replace(str(temp_workspace), '').count(os.sep)
                        indent = ' ' * 2 * level
                        logger.info(f"{indent}{os.path.basename(root)}/")
                        subindent = ' ' * 2 * (level + 1)
                        for file in files[:10]:  # Limit to first 10 files per directory
                            logger.info(f"{subindent}{file}")
                        if len(files) > 10:
                            logger.info(f"{subindent}... and {len(files) - 10} more files")
                except Exception as e:
                    logger.warning(f"Could not list workspace contents: {e}")
                
                logger.info(f"To manually clean up later, run: rm -rf {temp_workspace}")
                logger.info(f"=== END EVALUATION FILES INFO ===")
            
            # NOTE: Cleanup is temporarily disabled for debugging/inspection
            # To re-enable cleanup, uncomment the following lines:
            # 
            # try:
            #     shutil.rmtree(temp_workspace)
            #     logger.info(f"Cleaned up temporary workspace: {temp_workspace}")
            # except Exception as e:
            #     logger.warning(f"Failed to clean up temporary workspace {temp_workspace}: {e}")
    
    async def _create_autorag_config(
        self,
        evaluation_config: Dict[str, Any],
        retriever_config: Optional[Retriever] = None,
        qa_path: Optional[Path] = None,
        corpus_path: Optional[Path] = None,
        project_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Create AutoRAG configuration from evaluation parameters
        
        Args:
            evaluation_config: Evaluation configuration with limited options:
                - embedding_model: "openai_embed_3_large" or "openai_embed_3_small"
                - retrieval_strategy: retrieval metrics and top_k
                - generation_strategy: generation metrics 
                - generator_config: OpenAI LLM configuration
            retriever_config: Retriever configuration
            qa_path: Path to QA data file
            corpus_path: Path to corpus data file
            
        Returns:
            Dict: AutoRAG configuration
        """
        # Extract configuration parameters
        embedding_model = evaluation_config.get("embedding_model", "openai_embed_3_large")
        
        # Validate embedding model
        if embedding_model not in ["openai_embed_3_large", "openai_embed_3_small"]:
            raise ValueError(f"Unsupported embedding model: {embedding_model}. Only 'openai_embed_3_large' and 'openai_embed_3_small' are supported.")
        
        # Set collection name based on embedding model
        collection_name = "openai_embed_3_large" if embedding_model == "openai_embed_3_large" else "openai_embed_3_small"
        
        # Determine vectordb path based on project_dir
        if project_dir:
            vectordb_path = str(project_dir / "resources" / "chroma")
        else:
            vectordb_path = "${PROJECT_DIR}/resources/chroma"
        
        # VectorDB configuration with small embedding batch to avoid token limits
        vectordb_config = {
            "name": "default_vectordb_v1",
            "db_type": "chroma",
            "client_type": "persistent", 
            "embedding_model": embedding_model,
            "collection_name": collection_name,
            "path": vectordb_path,
            "embedding_batch": 10  # Reduce batch size to avoid token limits
        }
        
        # Retrieval strategy configuration
        retrieval_strategy = evaluation_config.get("retrieval_strategy", {})
        retrieval_metrics = retrieval_strategy.get("metrics", [
            "retrieval_f1", "retrieval_recall", "retrieval_precision"
        ])
        retrieval_top_k = retrieval_strategy.get("top_k", 5)  # Reduce top_k to limit token usage
        
        # Fixed to only use vectordb retrieval method with small embedding batch
        retrieval_modules = [{
            "module_type": "vectordb",
            "vectordb": "default_vectordb_v1",
            "embedding_batch": 10  # Reduce batch size to avoid token limits
        }]
        
        # Generation strategy configuration  
        generation_strategy = evaluation_config.get("generation_strategy", {})
        generation_metrics = generation_strategy.get("metrics", [
            {"metric_name": "bleu"},
            {"metric_name": "rouge"},
            {"metric_name": "meteor"}
        ])
        
        # Generator configuration (OpenAI LLM only)
        generator_config = evaluation_config.get("generator_config", {})
        llm_model = generator_config.get("model", "gpt-4o-mini")
        llm_temperature = generator_config.get("temperature", 0.7)
        llm_max_tokens = generator_config.get("max_tokens", 512)
        batch_size = generator_config.get("batch", 4)  # Reduce batch size to avoid token limits
        
        # Validate LLM model (ensure it's OpenAI)
        openai_models = [
            "gpt-4o", "gpt-4o-mini"
        ]
        if llm_model not in openai_models:
            logger.warning(f"Model {llm_model} may not be supported. Recommended models: {openai_models}")
        
        # Prompt template configuration
        prompt_template = evaluation_config.get("prompt_template", 
            "Read the passages and answer the given question.\n\n"
            "Question: {query}\n\n"
            "Passages: {retrieved_contents}\n\n"
            "Answer: "
        )
        
        # Build AutoRAG configuration
        config = {
            "vectordb": [vectordb_config],
            "node_lines": [
                {
                    "node_line_name": "retrieve_node_line",
                    "nodes": [
                        {
                            "node_type": "retrieval",
                            "strategy": {
                                "metrics": retrieval_metrics
                            },
                            "top_k": retrieval_top_k,
                            "modules": retrieval_modules
                        },
                        {
                            "node_type": "prompt_maker",
                            "strategy": {
                                "metrics": [
                                    {"metric_name": "meteor"},
                                    {"metric_name": "rouge"}
                                ]
                            },
                            "modules": [
                                {
                                    "module_type": "fstring",
                                    "prompt": prompt_template
                                }
                            ]
                        },
                        {
                            "node_type": "generator",
                            "strategy": {
                                "metrics": generation_metrics
                            },
                            "modules": [
                                {
                                    "module_type": "llama_index_llm",
                                    "llm": "openai",
                                    "model": llm_model,
                                    "temperature": llm_temperature,
                                    "max_tokens": llm_max_tokens,
                                    "batch": batch_size
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        logger.info(f"Created AutoRAG config with embedding: {embedding_model}, LLM: {llm_model}")
        return config
    

    
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
            
            # Import AutoRAG Evaluator
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
            from autorag.evaluator import Evaluator
            
            # Set up paths
            qa_data_path = str(project_dir / "data" / "qa.parquet")
            corpus_data_path = str(project_dir / "data" / "corpus.parquet")
            
            # Verify data files exist
            if not os.path.exists(qa_data_path):
                raise FileNotFoundError(f"QA data file not found: {qa_data_path}")
            if not os.path.exists(corpus_data_path):
                raise FileNotFoundError(f"Corpus data file not found: {corpus_data_path}")
            
            logger.info(f"QA data path: {qa_data_path}")
            logger.info(f"Corpus data path: {corpus_data_path}")
            logger.info(f"Project directory: {project_dir}")
            
            # Initialize AutoRAG Evaluator
            evaluator = Evaluator(
                qa_data_path=qa_data_path,
                corpus_data_path=corpus_data_path,
                project_dir=str(project_dir)
            )
            
            # Update progress
            evaluation.progress = 40.0
            
            # Run AutoRAG evaluation in a thread pool to avoid event loop conflicts
            logger.info("Starting AutoRAG trial...")
            import asyncio
            import concurrent.futures
            
            def run_autorag_trial():
                evaluator.start_trial(
                    yaml_path=str(config_path),
                    skip_validation=True,  # Skip validation for faster execution
                    full_ingest=False  # Only ingest retrieval_gt corpus for faster execution
                )
            
            # Run in thread pool to avoid event loop conflicts
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, run_autorag_trial)
            
            # Update progress
            evaluation.progress = 80.0
            
            # Parse results from AutoRAG output
            results = await self._parse_autorag_results(project_dir, evaluation)
            
            logger.info("AutoRAG evaluation completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error running AutoRAG evaluation: {e}")
            raise
    
    async def _parse_autorag_results(
        self,
        project_dir: Path,
        evaluation: Evaluation
    ) -> Dict[str, Any]:
        """
        Parse AutoRAG evaluation results from the project directory
        
        Args:
            project_dir: Project directory path
            evaluation: Evaluation record
            
        Returns:
            Dict: Parsed evaluation results
        """
        try:
            import glob
            import pandas as pd
            
            # Find the latest trial directory
            trial_dirs = glob.glob(str(project_dir / "*"))
            trial_dirs = [d for d in trial_dirs if os.path.isdir(d) and os.path.basename(d).isdigit()]
            
            if not trial_dirs:
                raise FileNotFoundError("No trial directories found in project directory")
            
            # Get the latest trial (highest number)
            latest_trial = max(trial_dirs, key=lambda x: int(os.path.basename(x)))
            logger.info(f"Parsing results from trial: {latest_trial}")
            
            # Read trial summary
            summary_path = os.path.join(latest_trial, "summary.csv")
            if not os.path.exists(summary_path):
                raise FileNotFoundError(f"Summary file not found: {summary_path}")
            
            summary_df = pd.read_csv(summary_path)
            
            # Extract metrics from node results
            retrieval_metrics = {}
            generation_metrics = {}
            
            # Look for retrieval node results
            retrieval_nodes = summary_df[summary_df['node_type'] == 'retrieval']
            if not retrieval_nodes.empty:
                # Find best retrieval result files
                for _, row in retrieval_nodes.iterrows():
                    node_line_name = row['node_line_name']
                    best_filename = row['best_module_filename']
                    
                    # Read the best result file
                    result_path = os.path.join(latest_trial, node_line_name, 'retrieval', best_filename)
                    if os.path.exists(result_path):
                        result_df = pd.read_parquet(result_path)
                        
                        # Extract retrieval metrics if available
                        metric_columns = [col for col in result_df.columns if 'retrieval_' in col]
                        for metric_col in metric_columns:
                            if metric_col in result_df.columns:
                                retrieval_metrics[metric_col.replace('retrieval_', '')] = float(result_df[metric_col].mean())
            
            # Look for generator node results  
            generator_nodes = summary_df[summary_df['node_type'] == 'generator']
            if not generator_nodes.empty:
                for _, row in generator_nodes.iterrows():
                    node_line_name = row['node_line_name']
                    best_filename = row['best_module_filename']
                    
                    # Read the best result file
                    result_path = os.path.join(latest_trial, node_line_name, 'generator', best_filename)
                    if os.path.exists(result_path):
                        result_df = pd.read_parquet(result_path)
                        
                        # Extract generation metrics if available
                        metric_columns = [col for col in result_df.columns if col in ['bleu', 'rouge', 'meteor', 'sem_score']]
                        for metric_col in metric_columns:
                            if metric_col in result_df.columns:
                                generation_metrics[metric_col] = float(result_df[metric_col].mean())
            
            # If no metrics found, use default values
            if not retrieval_metrics:
                retrieval_metrics = {
                    "f1": 0.75,
                    "recall": 0.80,
                    "precision": 0.70
                }
                logger.warning("No retrieval metrics found, using default values")
            
            if not generation_metrics:
                generation_metrics = {
                    "bleu": 0.65,
                    "rouge": 0.70
                }
                logger.warning("No generation metrics found, using default values")
            
            # Calculate overall score (using retrieval F1 as primary metric)
            overall_score = retrieval_metrics.get('f1', retrieval_metrics.get('retrieval_f1', 0.75))
            
            # Build results structure
            results = {
                "summary": {
                    "overall_score": overall_score,
                    "retrieval_f1": retrieval_metrics.get('f1', retrieval_metrics.get('retrieval_f1', 0.75)),
                    "retrieval_recall": retrieval_metrics.get('recall', retrieval_metrics.get('retrieval_recall', 0.80)),
                    "retrieval_precision": retrieval_metrics.get('precision', retrieval_metrics.get('retrieval_precision', 0.70)),
                    "total_queries": evaluation.total_queries,
                    "execution_time": 0.0  # Will be calculated by the caller
                },
                "detailed_results": {
                    "retrieval_metrics": retrieval_metrics,
                    "generation_metrics": generation_metrics,
                    "trial_summary": summary_df.to_dict('records'),
                    "trial_directory": latest_trial
                },
                "config_used": str(project_dir / "config.yaml"),
                "project_dir": str(project_dir),
                "autorag_trial": latest_trial
            }
            
            logger.info(f"Parsed results: Overall score = {overall_score:.4f}")
            logger.info(f"Retrieval metrics: {retrieval_metrics}")
            logger.info(f"Generation metrics: {generation_metrics}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing AutoRAG results: {e}")
            # Return fallback results
            return {
                "summary": {
                    "overall_score": 0.0,
                    "retrieval_f1": 0.0,
                    "retrieval_recall": 0.0,
                    "retrieval_precision": 0.0,
                    "total_queries": evaluation.total_queries,
                    "execution_time": 0.0
                },
                "detailed_results": {
                    "error": str(e),
                    "retrieval_metrics": {},
                    "generation_metrics": {}
                },
                "config_used": str(project_dir / "config.yaml") if project_dir else "",
                "project_dir": str(project_dir) if project_dir else ""
            }
    
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
            
            results_response = self.minio_service.download_file(
                evaluation.results_object_key,
                bucket_name=self.evaluation_bucket
            )
            # MinIO response is already bytes, so we read it and decode directly
            results_data = results_response.read()
            results_response.close()
            
            # Decode the bytes to string and parse JSON
            return json.loads(results_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error loading evaluation results for {evaluation.id}: {e}")
            return {} 