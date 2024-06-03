"""Routes for jobs API."""
import os
from typing import Any, Coroutine, Optional
import uuid

import asyncio
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.settings import settings
from server.web.api.jobs.utils import train_model, test_model

api_router = APIRouter()


class JobIn(BaseModel):
    """Job in"""

    name: str
    description: str
    owner_id: str
    model_id: uuid.UUID
    parameters: Optional[dict[str, Any]]
    # tags: list = []


class TrainModelIn(BaseModel):
    """Train model in"""

    job_id: uuid.UUID
    user_id: str
    dataset_id: uuid.UUID
    parameters: dict[str, Any] = {}
    name: str
    model_branch: str | None = None
    dataset_branch: str | None = None

class TestModelIn(BaseModel):
    """Test model in"""

    job_id: uuid.UUID
    user_id: str
    dataset_id: uuid.UUID
    parameters: dict[str, Any] = {}
    use_train_result_id: Optional[uuid.UUID] = None
    name: str
    model_branch: str | None = None
    dataset_branch: str | None = None


@api_router.get("", tags=["jobs"], summary="Get all jobs")
async def get_jobs(user_id: str) -> list[Job]:
    """Get all jobs."""
    if user_id is None:
        return await Job.objects.select_related("results").all()
    # Add results related to job
    return await Job.objects.select_related("results").all(owner_id=user_id)


@api_router.post("", tags=["jobs"], summary="Create a new job")
async def create_job(
    job_in: JobIn,
    req: Request
) -> None:
    """Create a new job."""
    job_id = uuid.uuid4()
    user_id = req.state.user_id
    # Find model and get path
    model = None
    try:
        model = await Model.objects.get(id=job_in.model_id, private=False)
        if model is None and user_id is not None:
            model = await Model.objects.get(id=job_in.model_id, private=True, owner_id=user_id)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Model {job_in.model_id} not found")
    except:
        raise HTTPException(
            status_code=404,
            detail=f"Model {job_in.model_id} does not exist",
        )
    parameters = job_in.parameters
    if parameters is None:
        parameters = model.parameters
    else:
        parameters = {**model.parameters, **parameters}

    await Job.objects.create(
        id=job_id,
        name=job_in.name,
        description=job_in.description,
        owner_id=user_id,
        model_id=job_in.model_id,
        model_name=model.name,
        parameters=parameters,
    )
    # Path is jobs_root/{job.id} folder


@api_router.post("/train", tags=["jobs", "models", "results"], summary="Run job to train model")
async def run_train_model(
    train_model_in: TrainModelIn,
    req: Request
) -> Any:
    """Run job to train model."""
    user_id = req.state.user_id
    dataset = await Dataset.objects.get(id=train_model_in.dataset_id, private=False)
    if dataset is None and user_id is not None:
        dataset = await Dataset.objects.get(id=train_model_in.dataset_id, private=True, owner_id=user_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {train_model_in.dataset_id} not found")
    job = await Job.objects.get(id=train_model_in.job_id)
    model = await Model.objects.get(id=job.model_id)
    loop = asyncio.get_event_loop()
    loop.create_task(
        train_model(
            dataset=dataset,
            job=job,
            model=model,
            result_name=train_model_in.name,
            parameters=train_model_in.parameters,
            model_branch=train_model_in.model_branch,
            dataset_branch=train_model_in.dataset_branch
        )
    )
    return "Training model"

@api_router.post("/test", tags=["jobs", "models", "results"], summary="Run job to test model")
async def run_test_model(
    test_model_in: TestModelIn,
    req: Request
) -> Any:
    """Run job to test model."""
    user_id = req.state.user_id
    dataset = await Dataset.objects.get(id=test_model_in.dataset_id, private=False)
    if dataset is None and user_id is not None:
        dataset = await Dataset.objects.get(id=test_model_in.dataset_id, private=True, owner_id=user_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {test_model_in.dataset_id} not found")
    job = await Job.objects.get(id=test_model_in.job_id)
    model = await Model.objects.get(id=job.model_id)

    model_path = None
    if test_model_in.use_train_result_id is not None:
        train_result = await Result.objects.get(id=test_model_in.use_train_result_id)
        model_path = settings.results_dir + "/" + train_result.pretrained_model

    # Check dataset type or structure
    # TODO: Check dataset type or structure
    if model_path is None:
        loop = asyncio.get_event_loop()
        loop.create_task(test_model(
            dataset=dataset,
            job=job,
            model=model,
            result_name=test_model_in.name,
            parameters=test_model_in.parameters,
            dataset_branch=test_model_in.dataset_branch,
            model_branch=test_model_in.model_branch
        ))
    else:
        loop = asyncio.get_event_loop()
        loop.create_task(test_model(
            dataset=dataset,
            job=job,
            model=model,
            result_name=test_model_in.name,
            parameters=test_model_in.parameters,
            pretrained_model=model_path,
            dataset_branch=test_model_in.dataset_branch,
            model_branch=test_model_in.model_branch
        ))
    return "Testing model"
