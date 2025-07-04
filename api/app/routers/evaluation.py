from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select, desc
from datetime import datetime
import pandas as pd
import json
import numpy as np
from io import BytesIO

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationDetail,
    EvaluationSummary,
    EvaluationStatusUpdate,
    EvaluationMetrics,
    BenchmarkDatasetCreate,
    BenchmarkDatasetUpdate,
    BenchmarkDataset,
    BenchmarkDatasetDetail,
    BenchmarkDatasetSummary
)
from app.models.evaluation import Evaluation as EvaluationModel, BenchmarkDataset as BenchmarkDatasetModel
from app.models.retriever import Retriever
from app.services.evaluation_service import EvaluationService
from app.services.benchmark_service import BenchmarkService
from app.core.database import get_session


def convert_numpy_to_python(obj):
    """
    Recursively convert numpy arrays and other non-serializable objects to Python native types for JSON serialization.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_python(item) for item in obj)
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif hasattr(obj, 'dtype') and obj.dtype.kind in {'U', 'S'}:  # numpy string types
        return str(obj)
    elif pd.isna(obj):  # pandas NaN values
        return None
    else:
        return obj

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
        benchmark_dataset = session.get(BenchmarkDatasetModel, evaluation_create.benchmark_dataset_id)
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


@router.get("/benchmarks/", response_model=List[BenchmarkDatasetSummary])
async def list_benchmark_datasets(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    session: Session = Depends(get_session)
):
    """
    List available benchmark datasets with pagination and filtering.
    """
    try:
        statement = select(BenchmarkDatasetModel)
        
        if not include_inactive:
            statement = statement.where(BenchmarkDatasetModel.is_active == True)
        
        statement = statement.order_by(desc(BenchmarkDatasetModel.created_at)).offset(skip).limit(limit)
        datasets = session.exec(statement).all()
        
        return [
            BenchmarkDatasetSummary(
                id=dataset.id,
                name=dataset.name,
                description=dataset.description,
                domain=dataset.domain,
                language=dataset.language,
                version=dataset.version,
                total_queries=dataset.total_queries,
                is_active=dataset.is_active,
                created_at=dataset.created_at,
                updated_at=dataset.updated_at
            )
            for dataset in datasets
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list benchmark datasets: {str(e)}")


@router.get("/benchmarks/{dataset_id}", response_model=BenchmarkDatasetDetail)
async def get_benchmark_dataset(dataset_id: UUID, session: Session = Depends(get_session)):
    """
    Get detailed information about a specific benchmark dataset.
    """
    try:
        dataset = session.get(BenchmarkDatasetModel, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Benchmark dataset not found")
        
        # Get file information from MinIO
        file_info = {}
        try:
            qa_info = benchmark_service.minio_service.client.stat_object(
                bucket_name=benchmark_service.benchmark_bucket,
                object_name=dataset.qa_data_object_key
            )
            corpus_info = benchmark_service.minio_service.client.stat_object(
                bucket_name=benchmark_service.benchmark_bucket,
                object_name=dataset.corpus_data_object_key
            )
            
            file_info = {
                "qa_file_size": qa_info.size,
                "corpus_file_size": corpus_info.size,
                "qa_last_modified": qa_info.last_modified.isoformat() if qa_info.last_modified else None,
                "corpus_last_modified": corpus_info.last_modified.isoformat() if corpus_info.last_modified else None
            }
        except Exception as e:
            file_info = {"error": f"Could not retrieve file info: {str(e)}"}
        
        # Get sample data for preview
        sample_data = {}
        try:
            qa_data, corpus_data = await benchmark_service.download_benchmark_dataset(dataset)
            # Convert to dict records and handle numpy arrays
            qa_sample = qa_data.head(3).to_dict('records')
            corpus_sample = corpus_data.head(3).to_dict('records')
            
            # Debug: Let's see what types are in the data
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"QA sample types: {[type(v) for record in qa_sample for v in record.values()]}")
            logger.info(f"Corpus sample types: {[type(v) for record in corpus_sample for v in record.values()]}")
            
            sample_data = {
                "qa_sample": convert_numpy_to_python(qa_sample),
                "corpus_sample": convert_numpy_to_python(corpus_sample),
                "qa_columns": list(qa_data.columns),
                "corpus_columns": list(corpus_data.columns)
            }
            
            # Debug: Check after conversion
            logger.info(f"After conversion - QA sample types: {[type(v) for record in sample_data['qa_sample'] for v in record.values()]}")
            
        except Exception as e:
            sample_data = {"error": f"Could not retrieve sample data: {str(e)}"}
        
        # Prepare response data with conversion
        response_data = {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "domain": dataset.domain,
            "language": dataset.language,
            "version": dataset.version,
            "evaluation_metrics": convert_numpy_to_python(dataset.evaluation_metrics),
            "total_queries": dataset.total_queries,
            "qa_data_object_key": dataset.qa_data_object_key,
            "corpus_data_object_key": dataset.corpus_data_object_key,
            "is_active": dataset.is_active,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "file_info": convert_numpy_to_python(file_info),
            "sample_data": convert_numpy_to_python(sample_data)
        }
        
        return BenchmarkDatasetDetail(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get benchmark dataset: {str(e)}")


@router.post("/benchmarks", response_model=BenchmarkDataset, status_code=status.HTTP_201_CREATED)
async def upload_benchmark_dataset(
    qa_file: UploadFile = File(..., description="QA data file (parquet, CSV, or JSON)"),
    corpus_file: UploadFile = File(..., description="Corpus data file (parquet, CSV, or JSON)"),
    name: str = Form(..., description="Dataset name"),
    description: str = Form(None, description="Dataset description"),
    domain: str = Form(None, description="Dataset domain"),
    language: str = Form("en", description="Dataset language"),
    version: str = Form("1.0", description="Dataset version"),
    evaluation_metrics: str = Form(None, description="JSON string of evaluation metrics"),
    session: Session = Depends(get_session)
):
    """
    Upload a new benchmark dataset with QA and corpus data files.
    
    Files should contain:
    - QA data: columns ['qid', 'query', 'retrieval_gt', 'generation_gt']
    - Corpus data: columns ['doc_id', 'contents', 'metadata' (optional)]
    
    Supported file formats: .parquet, .csv, .json
    """
    qa_data = None
    corpus_data = None
    
    try:
        # Validate file types
        allowed_extensions = {'.parquet', '.csv', '.json'}
        
        def get_file_extension(filename: str) -> str:
            return '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        qa_ext = get_file_extension(qa_file.filename)
        corpus_ext = get_file_extension(corpus_file.filename)
        
        if qa_ext not in allowed_extensions or corpus_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {allowed_extensions}"
            )
        
        # Read QA data
        qa_content = await qa_file.read()
        qa_buffer = BytesIO(qa_content)
        
        try:
            if qa_ext == '.parquet':
                qa_data = pd.read_parquet(qa_buffer)
            elif qa_ext == '.csv':
                qa_data = pd.read_csv(qa_buffer)
            elif qa_ext == '.json':
                qa_data = pd.read_json(qa_buffer)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse QA file: {str(e)}")
        
        # Read corpus data
        corpus_content = await corpus_file.read()
        corpus_buffer = BytesIO(corpus_content)
        
        try:
            if corpus_ext == '.parquet':
                corpus_data = pd.read_parquet(corpus_buffer)
            elif corpus_ext == '.csv':
                corpus_data = pd.read_csv(corpus_buffer)
            elif corpus_ext == '.json':
                corpus_data = pd.read_json(corpus_buffer)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse corpus file: {str(e)}")
        
        # Validate data is loaded
        if qa_data is None or corpus_data is None:
            raise HTTPException(status_code=400, detail="Failed to load data files")
        
        # Parse evaluation metrics if provided
        eval_metrics = None
        if evaluation_metrics:
            try:
                eval_metrics = json.loads(evaluation_metrics)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for evaluation_metrics")
        
        # Upload dataset using benchmark service
        dataset = await benchmark_service.upload_benchmark_dataset(
            name=name,
            qa_data=qa_data,
            corpus_data=corpus_data,
            description=description,
            domain=domain,
            language=language,
            version=version,
            evaluation_metrics=eval_metrics
        )
        
        # Save to database
        session.add(dataset)
        session.commit()
        session.refresh(dataset)
        
        return BenchmarkDataset(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            domain=dataset.domain,
            language=dataset.language,
            version=dataset.version,
            evaluation_metrics=dataset.evaluation_metrics,
            total_queries=dataset.total_queries,
            qa_data_object_key=dataset.qa_data_object_key,
            corpus_data_object_key=dataset.corpus_data_object_key,
            is_active=dataset.is_active,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload benchmark dataset: {str(e)}")


@router.put("/benchmarks/{dataset_id}", response_model=BenchmarkDataset)
async def update_benchmark_dataset(
    dataset_id: UUID,
    update_data: BenchmarkDatasetUpdate,
    session: Session = Depends(get_session)
):
    """
    Update benchmark dataset metadata.
    
    This endpoint only updates metadata, not the actual data files.
    To update data files, upload a new dataset.
    """
    try:
        dataset = session.get(BenchmarkDatasetModel, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Benchmark dataset not found")
        
        # Update fields that are provided
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(dataset, field, value)
        
        dataset.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(dataset)
        
        return BenchmarkDataset(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            domain=dataset.domain,
            language=dataset.language,
            version=dataset.version,
            evaluation_metrics=dataset.evaluation_metrics,
            total_queries=dataset.total_queries,
            qa_data_object_key=dataset.qa_data_object_key,
            corpus_data_object_key=dataset.corpus_data_object_key,
            is_active=dataset.is_active,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update benchmark dataset: {str(e)}")


@router.delete("/benchmarks/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_benchmark_dataset(
    dataset_id: UUID,
    hard_delete: bool = False,
    session: Session = Depends(get_session)
):
    """
    Delete a benchmark dataset.
    
    By default performs soft delete (sets is_active=False).
    Set hard_delete=True to permanently remove the dataset and its files.
    """
    try:
        dataset = session.get(BenchmarkDatasetModel, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Benchmark dataset not found")
        
        # Check if dataset is being used in any evaluations
        eval_statement = select(EvaluationModel).where(EvaluationModel.benchmark_dataset_id == dataset_id)
        evaluations = session.exec(eval_statement).all()
        
        if evaluations and hard_delete:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot hard delete dataset: {len(evaluations)} evaluations are using this dataset"
            )
        
        if hard_delete:
            # Delete files from MinIO
            try:
                benchmark_service.minio_service.client.remove_object(
                    bucket_name=benchmark_service.benchmark_bucket,
                    object_name=dataset.qa_data_object_key
                )
                benchmark_service.minio_service.client.remove_object(
                    bucket_name=benchmark_service.benchmark_bucket,
                    object_name=dataset.corpus_data_object_key
                )
            except Exception as e:
                # Log but don't fail the deletion if MinIO cleanup fails
                import logging
                logging.warning(f"Failed to delete files from MinIO: {e}")
            
            # Delete from database
            session.delete(dataset)
        else:
            # Soft delete
            dataset.is_active = False
            dataset.updated_at = datetime.utcnow()
        
        session.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete benchmark dataset: {str(e)}")


async def run_evaluation_background(evaluation_id: UUID, benchmark_dataset_id: UUID, retriever_id: Optional[UUID]):
    """
    Background task to run evaluation
    """
    try:
        from app.core.database import SessionLocal
        
        session = SessionLocal()
        
        # Get required records
        evaluation = session.get(EvaluationModel, evaluation_id)
        benchmark_dataset = session.get(BenchmarkDatasetModel, benchmark_dataset_id)
        
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