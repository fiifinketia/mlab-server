"""Routes for jobs API."""
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from server.db.models.jobs import Job
from server.web.api.jobs.dto import JobIn, TestModelIn, TrainModelIn
from server.web.api.jobs import service as jobs_service

api_router = APIRouter()

 # adjust the chunk size as desired

@api_router.get("", tags=["jobs"], summary="Get all jobs", response_model=list[Job])
async def get_jobs(req: Request) -> list[Job]:
    """Get all jobs."""
    user_id = req.state.user_id
    return await jobs_service.get_jobs(user_id)


@api_router.post("/stop", tags=["jobs"], summary="Stop all job processes")
async def stop_jobs(req: Request, job_id: uuid.UUID) -> None:
    """Stop a jobs running processes"""
    user_id = req.state.user_id
    return await jobs_service.stop_job(user_id, job_id)

@api_router.post("/close", tags=["jobs"], summary="Close a job")
async def close_job(
    job_id: uuid.UUID,
    req: Request
) -> None:
    """Close a job."""
    user_id = req.state.user_id
    return await jobs_service.close_job(user_id, job_id)

@api_router.post("", tags=["jobs"], summary="Create a new job")
async def create_job(
    job_in: JobIn,
    req: Request
) -> None:
    """Create a new job."""
    user_id = req.state.user_id
    # Find model and get path
    try:

        return await jobs_service.create_job(user_id, job_in)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/train", tags=["jobs", "models", "results"], summary="Run job to train model")
async def run_train_model(
    train_model_in: TrainModelIn,
    req: Request
) -> Any:
    """Run job to train model."""
    user_id = req.state.user_id
    # Check if job is ready
    return await jobs_service.train(user_id, train_model_in)

@api_router.post("/upload/test/{job_id}", tags=["jobs", "models", "results"], summary="Upload test data for model")
async def upload_test_data(
    file: Annotated[UploadFile, File(description="Test data file")],
    job_id: uuid.UUID,
) -> str:
    """Upload test data for model."""
    return await jobs_service.upload_file(file, job_id)

@api_router.post("/test", tags=["jobs", "models", "results"], summary="Run job to test model")
async def run_test_model(
    test_model_in: TestModelIn,
    req: Request
) -> Any:
    """Run job to test model."""
    user_id = req.state.user_id
    # Check if job is ready
    return await jobs_service.test(user_id, test_model_in)
