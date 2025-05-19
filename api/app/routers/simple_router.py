from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult

from app.celery_app import app as celery_app # Import the Celery app instance
from app.tasks.simple_tasks import reverse_string_task
from app.schemas.task import ReverseRequest, TaskResponse

router = APIRouter(
    prefix="/utils",
    tags=["Utilities"],
)

@router.post("/reverse", response_model=TaskResponse, status_code=202)
async def submit_reverse_string(request: ReverseRequest):
    """Submits a task to reverse a string."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    task = reverse_string_task.delay(request.text)
    return TaskResponse(task_id=task.id, status=task.status)

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Retrieves the status and result of a Celery task."""
    task_result = AsyncResult(task_id, app=celery_app)
    
    response_data = {
        "task_id": task_id,
        "status": task_result.status,
    }

    if task_result.successful():
        response_data["result"] = task_result.result
    elif task_result.failed():
        # task_result.traceback might be too verbose or sensitive for an API response
        # Consider logging it and returning a generic error message or task_result.result (which is the exception)
        response_data["error"] = str(task_result.result) # or a more generic error message
        # If you want to return a 500 error for failed tasks:
        # raise HTTPException(status_code=500, detail=f"Task failed: {str(task_result.result)}")
    elif task_result.status == 'PENDING':
        response_data["result"] = None
    elif task_result.status == 'STARTED':
        response_data["result"] = None # Or some info if available, e.g., task_result.info
    else:
        # Other states like RETRY, REVOKED
        response_data["result"] = None

    return TaskResponse(**response_data) 