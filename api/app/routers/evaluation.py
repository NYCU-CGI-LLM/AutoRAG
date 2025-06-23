from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
from datetime import datetime

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationDetail,
    EvaluationSummary,
    EvaluationStatusUpdate,
    EvaluationMetrics,
    EvaluationConfigSchema,
    EvaluationConfigExample
)
from app.models.evaluation import Evaluation as EvaluationModel, BenchmarkDataset
from app.models.retriever import Retriever
from app.services.evaluation_service import EvaluationService
from app.services.benchmark_service import BenchmarkService
from app.core.database import get_session

router = APIRouter(
    prefix="/eval",
    tags=["Evaluation"],
)

evaluation_service = EvaluationService()
benchmark_service = BenchmarkService()


@router.post("/", response_model=Evaluation, status_code=status.HTTP_201_CREATED)
async def submit_evaluation_run(
    evaluation_create: EvaluationCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Submit an evaluation run.
    
    Creates a new evaluation run with the specified benchmark dataset and evaluation config.
    The evaluation will be queued and processed asynchronously.
    """
    try:
        # Validate benchmark dataset exists
        benchmark_dataset = session.get(BenchmarkDataset, evaluation_create.benchmark_dataset_id)
        if not benchmark_dataset:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark dataset {evaluation_create.benchmark_dataset_id} not found"
            )
        
        # Create evaluation run (no retriever_config_id needed)
        evaluation = await evaluation_service.create_evaluation_run(
            retriever_config_id=None,  # Not needed anymore
            benchmark_dataset_id=evaluation_create.benchmark_dataset_id,
            evaluation_config=evaluation_create.evaluation_config,
            name=evaluation_create.name
        )
        
        # Save to database
        session.add(evaluation)
        session.commit()
        session.refresh(evaluation)
        
        # Queue evaluation for background processing
        background_tasks.add_task(
            run_evaluation_background,
            evaluation.id,
            benchmark_dataset.id,
            None  # No retriever ID needed
        )
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit evaluation: {str(e)}")


@router.get("/", response_model=List[EvaluationSummary])
async def list_evaluation_runs(session: Session = Depends(get_session)):
    """
    List previous evaluation runs.
    
    Returns a list of all evaluation runs belonging to the authenticated user,
    including their current status and summary metrics.
    """
    try:
        statement = select(EvaluationModel).order_by(EvaluationModel.created_at.desc())
        evaluations = session.exec(statement).all()
        
        # Convert to summary format
        summaries = []
        for eval_record in evaluations:
            # Get retriever name
            retriever = session.get(Retriever, eval_record.retriever_config_id)
            retriever_name = retriever.name if retriever else "Unknown"
            
            # Extract overall score
            overall_score = None
            if eval_record.detailed_results:
                overall_score = eval_record.detailed_results.get("overall_score")
            
            summary = EvaluationSummary(
                id=eval_record.id,
                name=eval_record.name,
                status=eval_record.status,
                progress=eval_record.progress,
                created_at=eval_record.created_at,
                retriever_config_name=retriever_name,
                overall_score=overall_score
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list evaluations: {str(e)}")


@router.get("/{eval_id}", response_model=EvaluationDetail)
async def get_evaluation_run(eval_id: UUID, session: Session = Depends(get_session)):
    """
    Poll run status / fetch result.
    
    Returns detailed information about a specific evaluation run,
    including current status, progress, and results if completed.
    """
    try:
        evaluation = session.get(EvaluationModel, eval_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Get retriever name
        retriever = session.get(Retriever, evaluation.retriever_config_id)
        retriever_name = retriever.name if retriever else "Unknown"
        
        # Convert detailed results to EvaluationResult format
        results = []
        if evaluation.detailed_results:
            # Extract retrieval metrics
            retrieval_metrics = evaluation.detailed_results.get("retrieval_metrics", {})
            for metric_name, value in retrieval_metrics.items():
                results.append({
                    "metric_name": f"retrieval_{metric_name}",
                    "value": value,
                    "description": f"Retrieval {metric_name.upper()} score"
                })
        
        # Get detailed results if available
        detailed_results = None
        if evaluation.status == "success":
            detailed_results = await evaluation_service.get_evaluation_results(evaluation)
        
        return EvaluationDetail(
            id=evaluation.id,
            name=evaluation.name,
            retriever_config_id=evaluation.retriever_config_id,
            evaluation_config=evaluation.evaluation_config,
            dataset_config=evaluation.dataset_config,
            status=evaluation.status,
            progress=evaluation.progress,
            message=evaluation.message,
            total_queries=evaluation.total_queries,
            processed_queries=evaluation.processed_queries,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at,
            retriever_config_name=retriever_name,
            results=results,
            detailed_results=detailed_results,
            execution_time=evaluation.execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation: {str(e)}")


@router.put("/{eval_id}/status", response_model=Evaluation, include_in_schema=False)
async def update_evaluation_status(
    eval_id: UUID, 
    status_update: EvaluationStatusUpdate,
    session: Session = Depends(get_session)
):
    """
    Update evaluation status.
    
    Update the status, progress, and related metadata for an evaluation run.
    This endpoint is typically used by the evaluation service to report progress.
    """
    try:
        evaluation = session.get(EvaluationModel, eval_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Update fields
        evaluation.status = status_update.status
        if status_update.progress is not None:
            evaluation.progress = status_update.progress
        if status_update.message is not None:
            evaluation.message = status_update.message
        if status_update.processed_queries is not None:
            evaluation.processed_queries = status_update.processed_queries
        
        evaluation.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(evaluation)
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update evaluation status: {str(e)}")


@router.delete("/{eval_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_evaluation_run(eval_id: UUID, session: Session = Depends(get_session)):
    """
    Delete an evaluation run.
    
    Permanently delete an evaluation run and all its associated results.
    This operation cannot be undone.
    """
    try:
        evaluation = session.get(EvaluationModel, eval_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        # Delete results from MINIO if they exist
        if evaluation.results_object_key:
            try:
                evaluation_service.minio_service.delete_file(
                    evaluation.results_object_key,
                    bucket_name=evaluation_service.evaluation_bucket
                )
            except Exception as e:
                # Log but don't fail the deletion if MINIO cleanup fails
                import logging
                logging.warning(f"Failed to delete results from MINIO: {e}")
        
        # Delete from database
        session.delete(evaluation)
        session.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete evaluation: {str(e)}")


@router.post("/benchmarks/sample", response_model=List[dict], include_in_schema=False)
async def create_sample_benchmarks(session: Session = Depends(get_session)):
    """
    Create sample benchmark datasets for testing.
    
    This endpoint creates sample benchmark datasets and stores them in MINIO.
    """
    try:
        # Create sample benchmarks
        sample_datasets = await benchmark_service.create_sample_benchmarks()
        
        # Save to database
        for dataset in sample_datasets:
            session.add(dataset)
        
        session.commit()
        
        return [
            {
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description,
                "total_queries": dataset.total_queries,
                "domain": dataset.domain,
                "language": dataset.language
            }
            for dataset in sample_datasets
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sample benchmarks: {str(e)}")


@router.get("/benchmarks/", response_model=List[dict])
async def list_benchmark_datasets(session: Session = Depends(get_session)):
    """
    List available benchmark datasets.
    """
    try:
        statement = select(BenchmarkDataset).where(BenchmarkDataset.is_active == True)
        datasets = session.exec(statement).all()
        
        return [
            {
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description,
                "total_queries": dataset.total_queries,
                "domain": dataset.domain,
                "language": dataset.language,
                "version": dataset.version,
                "created_at": dataset.created_at
            }
            for dataset in datasets
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list benchmark datasets: {str(e)}")


@router.get("/test/list-datasets", response_model=dict)
async def test_list_available_datasets(session: Session = Depends(get_session)):
    """
    Test endpoint to list available benchmark datasets and retriever configs.
    
    Helps identify the IDs needed for testing.
    """
    try:
        # Get benchmark datasets
        benchmark_statement = select(BenchmarkDataset).where(BenchmarkDataset.is_active == True)
        benchmark_datasets = session.exec(benchmark_statement).all()
        
        # Get retriever configs
        retriever_statement = select(Retriever)
        retrievers = session.exec(retriever_statement).all()
        
        return {
            "benchmark_datasets": [
                {
                    "id": str(dataset.id),
                    "name": dataset.name,
                    "description": dataset.description,
                    "qa_object_key": dataset.qa_object_key,
                    "corpus_object_key": dataset.corpus_object_key
                }
                for dataset in benchmark_datasets
            ],
            "retriever_configs": [
                {
                    "id": str(retriever.id),
                    "name": retriever.name,
                    "description": retriever.description,
                    "config_type": retriever.config_type
                }
                for retriever in retrievers
            ],
            "sample_evaluation_config": {
                "embedding_model": "openai_embed_3_large",
                "retrieval_strategy": {
                    "metrics": ["retrieval_f1", "retrieval_recall"],
                    "top_k": 10
                },
                "generation_strategy": {
                    "metrics": [
                        {"metric_name": "bleu"},
                        {"metric_name": "rouge"}
                    ]
                },
                "generator_config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 512,
                    "batch": 16
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list test data: {str(e)}"
        )


@router.post("/test/config-only", response_model=dict)
async def test_config_generation_only(evaluation_config: dict):
    """
    Test endpoint to generate AutoRAG config only.
    
    This endpoint only tests the config generation process without downloading data.
    Useful for quickly validating evaluation_config format.
    """
    try:
        # Generate AutoRAG config without data dependencies
        autorag_config = await evaluation_service._create_autorag_config(
            evaluation_config=evaluation_config
        )
        
        # Return test results
        return {
            "status": "success",
            "message": "Successfully generated AutoRAG config",
            "config_info": {
                "embedding_model": autorag_config.get("vectordb", [{}])[0].get("embedding_model"),
                "collection_name": autorag_config.get("vectordb", [{}])[0].get("collection_name"),
                "vectordb_path": autorag_config.get("vectordb", [{}])[0].get("path"),
                "node_count": len(autorag_config.get("node_lines", [{}])[0].get("nodes", [])),
                "retrieval_modules": [
                    module.get("module_type") 
                    for module in autorag_config.get("node_lines", [{}])[0].get("nodes", [{}])[0].get("modules", [])
                ],
                "generation_modules": [
                    module.get("module_type") 
                    for module in autorag_config.get("node_lines", [{}])[0].get("nodes", [{}])[-1].get("modules", [])
                ]
            },
            "generated_config": autorag_config,
            "note": "VectorDB path uses placeholder '${PROJECT_DIR}' since no project_dir was provided"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Config generation failed: {str(e)}"
        )


@router.post("/test/save-files", response_model=dict)
async def test_save_files_to_disk(
    benchmark_dataset_id: UUID,
    evaluation_config: dict,
    session: Session = Depends(get_session)
):
    """
    Test endpoint to save benchmark data and config to disk for inspection.
    
    This endpoint downloads data, generates config, and saves them to a temporary
    directory that won't be automatically cleaned up, so you can inspect the files.
    """
    try:
        # Validate benchmark dataset exists
        benchmark_dataset = session.get(BenchmarkDataset, benchmark_dataset_id)
        if not benchmark_dataset:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark dataset {benchmark_dataset_id} not found"
            )
        
        # Download benchmark data
        qa_data, corpus_data = await benchmark_service.download_benchmark_dataset(benchmark_dataset)
        
        # Create persistent temp directory first (won't be auto-cleaned)
        import tempfile
        from pathlib import Path
        import yaml
        
        temp_dir = Path(tempfile.mkdtemp(prefix="eval_debug_"))
        data_dir = temp_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Create resources directory for vectordb
        resources_dir = temp_dir / "resources"
        resources_dir.mkdir(exist_ok=True)
        
        # Generate AutoRAG config with correct project_dir
        autorag_config = await evaluation_service._create_autorag_config(
            evaluation_config=evaluation_config,
            project_dir=temp_dir
        )
        
        # Save data files
        qa_path = data_dir / "qa.parquet"
        corpus_path = data_dir / "corpus.parquet"
        config_path = temp_dir / "config.yaml"
        
        qa_data.to_parquet(qa_path, index=False)
        corpus_data.to_parquet(corpus_path, index=False)
        
        # Save config file
        with open(config_path, 'w') as f:
            yaml.dump(autorag_config, f, default_flow_style=False)
        
        # Create a summary file
        summary_path = temp_dir / "summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Evaluation Debug Files\n")
            f.write(f"=====================\n\n")
            f.write(f"Benchmark Dataset: {benchmark_dataset.name}\n")
            f.write(f"Dataset ID: {benchmark_dataset_id}\n")
            f.write(f"QA Records: {len(qa_data)}\n")
            f.write(f"Corpus Records: {len(corpus_data)}\n")
            f.write(f"Generated at: {datetime.utcnow()}\n\n")
            f.write(f"VectorDB Path: {autorag_config.get('vectordb', [{}])[0].get('path', 'N/A')}\n")
            f.write(f"Embedding Model: {autorag_config.get('vectordb', [{}])[0].get('embedding_model', 'N/A')}\n\n")
            f.write(f"Files:\n")
            f.write(f"- qa.parquet: QA data ({qa_path})\n")
            f.write(f"- corpus.parquet: Corpus data ({corpus_path})\n")
            f.write(f"- config.yaml: AutoRAG config ({config_path})\n")
            f.write(f"- summary.txt: This file ({summary_path})\n")
            f.write(f"- resources/: Directory for vectordb and other resources\n\n")
            f.write(f"To clean up this directory later, run:\n")
            f.write(f"rm -rf {temp_dir}\n")
        
        # Return file paths and info
        return {
            "status": "success",
            "message": "Files saved to disk for inspection",
            "file_paths": {
                "temp_directory": str(temp_dir),
                "qa_data": str(qa_path),
                "corpus_data": str(corpus_path),
                "config_file": str(config_path),
                "summary_file": str(summary_path),
                "vectordb_path": autorag_config.get('vectordb', [{}])[0].get('path', 'N/A')
            },
            "data_info": {
                "qa_records": len(qa_data),
                "corpus_records": len(corpus_data),
                "qa_columns": list(qa_data.columns),
                "corpus_columns": list(corpus_data.columns)
            },
            "config_info": {
                "vectordb_path": autorag_config.get('vectordb', [{}])[0].get('path', 'N/A'),
                "embedding_model": autorag_config.get('vectordb', [{}])[0].get('embedding_model'),
                "collection_name": autorag_config.get('vectordb', [{}])[0].get('collection_name')
            },
            "cleanup_command": f"rm -rf {temp_dir}",
            "note": "This directory will NOT be automatically cleaned up. Use the cleanup_command to remove it when done."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save files: {str(e)}"
        )


@router.post("/test/download-and-config", response_model=dict)
async def test_download_and_config(
    benchmark_dataset_id: UUID,
    evaluation_config: dict,
    session: Session = Depends(get_session)
):
    """
    Test endpoint to download benchmark data and generate AutoRAG config.
    
    This endpoint helps test the data download and config generation process
    without running the full evaluation. Data is processed in memory only.
    """
    try:
        # Validate benchmark dataset exists
        benchmark_dataset = session.get(BenchmarkDataset, benchmark_dataset_id)
        if not benchmark_dataset:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark dataset {benchmark_dataset_id} not found"
            )
        
        # Download benchmark data
        qa_data, corpus_data = await benchmark_service.download_benchmark_dataset(benchmark_dataset)
        
        # Generate AutoRAG config (no need for temp files for testing)
        autorag_config = await evaluation_service._create_autorag_config(
            evaluation_config=evaluation_config
        )
        
        # Return test results
        return {
            "status": "success",
            "message": "Successfully downloaded data and generated config",
            "data_info": {
                "qa_records": len(qa_data),
                "corpus_records": len(corpus_data),
                "qa_columns": list(qa_data.columns),
                "corpus_columns": list(corpus_data.columns)
            },
            "config_info": {
                "embedding_model": autorag_config.get("vectordb", [{}])[0].get("embedding_model"),
                "collection_name": autorag_config.get("vectordb", [{}])[0].get("collection_name"),
                "vectordb_path": autorag_config.get("vectordb", [{}])[0].get("path"),
                "node_count": len(autorag_config.get("node_lines", [{}])[0].get("nodes", [])),
                "retrieval_modules": [
                    module.get("module_type") 
                    for module in autorag_config.get("node_lines", [{}])[0].get("nodes", [{}])[0].get("modules", [])
                ],
                "generation_modules": [
                    module.get("module_type") 
                    for module in autorag_config.get("node_lines", [{}])[0].get("nodes", [{}])[-1].get("modules", [])
                ]
            },
            "generated_config": autorag_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Test failed: {str(e)}"
        )


@router.get("/config/examples", response_model=EvaluationConfigExample)
async def get_evaluation_config_examples():
    """
    Get evaluation configuration examples.
    
    Returns examples of basic and advanced evaluation configurations
    that can be used when submitting evaluation runs.
    """
    return EvaluationConfigExample()


@router.get("/config/schema", response_model=EvaluationConfigSchema)
async def get_evaluation_config_schema():
    """
    Get evaluation configuration schema.
    
    Returns the schema for evaluation configuration with default values.
    """
    return EvaluationConfigSchema()


async def run_evaluation_background(evaluation_id: UUID, benchmark_dataset_id: UUID, retriever_id: Optional[UUID]):
    """
    Background task to run evaluation
    """
    try:
        from app.core.database import SessionLocal
        
        session = SessionLocal()
        
        # Get required records
        evaluation = session.get(EvaluationModel, evaluation_id)
        benchmark_dataset = session.get(BenchmarkDataset, benchmark_dataset_id)
        
        # Get retriever if ID is provided
        retriever = None
        if retriever_id:
            retriever = session.get(Retriever, retriever_id)
        
        if not all([evaluation, benchmark_dataset]):
            raise Exception("Required records not found")
        
        # Execute evaluation
        updated_evaluation = await evaluation_service.execute_evaluation(
            evaluation=evaluation,
            benchmark_dataset=benchmark_dataset,
            retriever_config=retriever
        )
        
        # Update database
        session.merge(updated_evaluation)
        session.commit()
        
        session.close()
        
    except Exception as e:
        import logging
        logging.error(f"Background evaluation task failed: {e}")
        
        # Update evaluation status to failed
        try:
            from app.core.database import SessionLocal
            session = SessionLocal()
            evaluation = session.get(EvaluationModel, evaluation_id)
            if evaluation:
                evaluation.status = "failure"
                evaluation.message = str(e)
                session.commit()
            session.close()
        except Exception as db_error:
            logging.error(f"Failed to update evaluation status: {db_error}") 