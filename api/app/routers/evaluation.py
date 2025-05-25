from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate,
    EvaluationDetail,
    EvaluationSummary,
    EvaluationStatusUpdate,
    EvaluationMetrics
)

router = APIRouter(
    prefix="/eval",
    tags=["Evaluation"],
)


@router.post("/", response_model=Evaluation, status_code=status.HTTP_201_CREATED)
async def submit_evaluation_run(evaluation_create: EvaluationCreate):
    """
    Submit an evaluation run.
    
    Creates a new evaluation run for the specified retriever configuration.
    The evaluation will be queued and processed asynchronously.
    """
    # TODO: Implement evaluation run submission logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/", response_model=List[EvaluationSummary])
async def list_evaluation_runs():
    """
    List previous evaluation runs.
    
    Returns a list of all evaluation runs belonging to the authenticated user,
    including their current status and summary metrics.
    """
    # TODO: Implement evaluation run listing logic
    return []  # Return empty list as placeholder


@router.get("/{eval_id}", response_model=EvaluationDetail)
async def get_evaluation_run(eval_id: UUID):
    """
    Poll run status / fetch result.
    
    Returns detailed information about a specific evaluation run,
    including current status, progress, and results if completed.
    """
    # TODO: Implement single evaluation run retrieval logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{eval_id}/status", response_model=Evaluation)
async def update_evaluation_status(eval_id: UUID, status_update: EvaluationStatusUpdate):
    """
    Update evaluation status.
    
    Update the status, progress, and related metadata for an evaluation run.
    This endpoint is typically used by the evaluation service to report progress.
    """
    # TODO: Implement evaluation status update logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{eval_id}/metrics", response_model=EvaluationMetrics)
async def get_evaluation_metrics(eval_id: UUID):
    """
    Get evaluation metrics.
    
    Returns detailed evaluation metrics for a completed evaluation run,
    including precision, recall, F1 score, and custom metrics.
    """
    # TODO: Implement evaluation metrics retrieval logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.delete("/{eval_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation_run(eval_id: UUID):
    """
    Delete an evaluation run.
    
    Permanently delete an evaluation run and all its associated results.
    This operation cannot be undone.
    """
    # TODO: Implement evaluation run deletion logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/{eval_id}/retry", response_model=Evaluation)
async def retry_evaluation_run(eval_id: UUID):
    """
    Retry a failed evaluation run.
    
    Restart a failed evaluation run with the same configuration.
    This creates a new run instance with the same parameters.
    """
    # TODO: Implement evaluation retry logic
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/{eval_id}/stop", response_model=Evaluation)
async def stop_evaluation_run(eval_id: UUID):
    """
    Stop a running evaluation.
    
    Terminate a currently running evaluation run.
    Partial results may be preserved.
    """
    # TODO: Implement evaluation stop logic
    raise HTTPException(status_code=501, detail="Not implemented yet") 