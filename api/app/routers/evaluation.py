from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select, desc
from datetime import datetime

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationDetail,
    EvaluationSummary,
    EvaluationStatusUpdate,
    EvaluationMetrics
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
        statement = select(EvaluationModel).order_by(desc(EvaluationModel.created_at))
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
                    evaluation.results_object_key
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
        from datetime import datetime
        logging.error(f"Background evaluation task failed: {e}")
        
        # Update evaluation status to failed
        try:
            from app.core.database import SessionLocal
            from app.schemas.common import TaskStatusEnum
            session = SessionLocal()
            evaluation = session.get(EvaluationModel, evaluation_id)
            if evaluation:
                evaluation.status = TaskStatusEnum.FAILURE
                evaluation.message = str(e)
                evaluation.updated_at = datetime.utcnow()
                session.commit()
            session.close()
        except Exception as db_error:
            logging.error(f"Failed to update evaluation status: {db_error}") 