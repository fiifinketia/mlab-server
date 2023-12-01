"""Routes for jobs API."""
import os
from typing import Any, Optional
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.settings import settings
from server.web.api.jobs.utils import run_model

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


@api_router.get("/", tags=["jobs"], summary="Get all jobs")
async def get_jobs(user_id: str) -> list[Job]:
    """Get all jobs."""
    if user_id is None:
        return await Job.objects.select_related("results").all()
    # Add results related to job
    return await Job.objects.select_related("results").all(owner_id=user_id)


@api_router.post("/", tags=["jobs"], summary="Create a new job")
async def create_job(
    job_in: JobIn,
) -> None:
    """Create a new job."""
    job_id = uuid.uuid4()
    try:
        os.chdir(settings.jobs_dir)
    except FileNotFoundError:
        os.makedirs(settings.jobs_dir)
        os.chdir(settings.jobs_dir)
    # convert job.id to string
    str_job_id = str(job_id)
    os.mkdir(str_job_id)
    # Update job path for job
    # Copy config.txt for model and add to job folder
    os.chdir(str_job_id)
    # Find model and get path
    model = None
    try:
        model = await Model.objects.get(id=job_in.model_id)
    except:
        raise HTTPException(
            status_code=404,
            detail=f"Model {job_in.model_id} does not exist",
        )
    model_path = os.path.join(settings.models_dir, model.path)
    os.system(f"cp {model_path}/config.txt .")
    path = f"/{str_job_id}"
    parameters = job_in.parameters
    if parameters is None:
        parameters = model.parameters
    else:
        parameters = {**model.parameters, **parameters}

    await Job.objects.create(
        id=job_id,
        name=job_in.name,
        description=job_in.description,
        path=path,
        # tags=job_in.tags,
        owner_id=job_in.owner_id,
        model_id=job_in.model_id,
        model_name=model.name,
        parameters=parameters,
    )
    # Path is jobs_root/{job.id} folder


@api_router.post("/train", tags=["jobs", "models", "results"], summary="Run job to train model")
async def train_model(
    train_model_in: TrainModelIn,
) -> Any:
    """Run job to train model."""
    # If dataset_id is defined then file and dataset_name is ignored
    # Else upload new dataset file for user
    dataset = await Dataset.objects.get(id=train_model_in.dataset_id)
    job = await Job.objects.get(id=train_model_in.job_id)
    # Check dataset type or structure
    # TODO: Check dataset type or structure
    res = await run_in_threadpool(run_model, dataset, job, train_model_in.parameters)
    return res
