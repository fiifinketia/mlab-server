"""Routes for jobs API."""
import datetime
from enum import Enum
import os
from pathlib import Path
from typing import Annotated, Any, Optional
import uuid

import asyncio
import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.settings import settings
from server.web.api.jobs.utils import setup_environment, stop_job_processes, train_model, test_model, remove_job_env
from server.web.api.utils import job_get_dirs

api_router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # adjust the chunk size as desired

class JobWithResults(Job):
    """Job with results"""
    results: list[Result] = []

class JobIn(BaseModel):
    """Job in"""

    name: str
    description: str
    owner_id: str
    model_id: uuid.UUID
    parameters: Optional[dict[str, Any]]
    dataset_id: uuid.UUID
    # tags: list = []


class TrainModelIn(BaseModel):
    """Train model in"""

    job_id: uuid.UUID
    parameters: dict[str, Any] = {}
    name: str
    model_branch: str | None = None
    dataset_branch: str | None = None

class ModelType(str,Enum):
    default = "default"
    pretrained = "pretrained"
    custom = "custom"

class DatasetType(str,Enum):
    default = "default"
    upload = "upload"
class UseModel(BaseModel):
    type: ModelType
    result_id: Optional[str]
    branch: Optional[str]

class UseDataset(BaseModel):
    type: DatasetType
    branch: Optional[str]
    path: Optional[str]
class TestModelIn(BaseModel):
    """Test model in"""
    name: str
    job_id: uuid.UUID
    parameters: dict[str, Any] = {}
    model: UseModel
    dataset: UseDataset


@api_router.get("", tags=["jobs"], summary="Get all jobs", response_model=list[Job])
async def get_jobs(req: Request) -> list[Job]:
    """Get all jobs."""
    user_id = req.state.user_id
    if user_id is None:
        return await Job.objects.select_related("results").all()
    # Add results related to job
    return await Job.objects.select_related("results").all(owner_id=user_id, closed=False)

@api_router.post("/stop", tags=["jobs"], summary="Stop all job processes")
async def stop_jobs(req: Request, job_id: uuid.UUID) -> None:
    """Stop a jobs running processes"""
    user_id = req.state.user_id
    job = await Job.objects.get(id=job_id)
    if job.owner_id!= user_id:
        raise HTTPException(status_code=403, detail=f"User does not have permission to stop job {job_id}")
    try:
        stop_job_processes(job_id)
        job.ready = True
        job.modified = datetime.datetime.now()
        await job.update()
        # update jobb results with status running
        job_results_running = await Result.objects.filter(job=job, status="running").all()
        for result in job_results_running:
            result.status = "stopped"
            result.modified = datetime.datetime.now()
            await result.update()
    except:
        HTTPException(status_code=400, detail=f"Failed to stop job {job_id}")

@api_router.post("/close", tags=["jobs"], summary="Close a job")
async def close_job(
    job_id: uuid.UUID,
    req: Request
) -> None:
    """Close a job."""
    user_id = req.state.user_id
    job = await Job.objects.get(id=job_id)
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail=f"User does not have permission to close job {job_id}")
    if not job.ready:
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not ready, might still be running")
    # Close job
    dataset = await Dataset.objects.get(id=job.dataset_id)
    model = await Model.objects.get(id=job.model_id)
    # check if job has any of its results with status running
    job_results_running = await Result.objects.filter(job=job, status="running").all()
    if len(job_results_running) > 0:
        raise HTTPException(status_code=400, detail=f"Job {job_id} has running processes, please stop them first")
    try:
        remove_job_env(job_id=job_id, dataset_name=dataset.git_name, model_name=model.git_name)
    except:
        HTTPException(status_code=400, detail=f"Failed to remove job environment")
    job.closed = True
    job.modified = datetime.datetime.now()
    await job.update()

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
        dataset = await Dataset.objects.get(id=job_in.dataset_id, private=False)
        if model is None and user_id is not None:
            model = await Model.objects.get(id=job_in.model_id, private=True, owner_id=user_id)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Model {job_in.model_id} not found")
        if dataset is None and user_id is not None:
            dataset = await Dataset.objects.get(id=job_in.dataset_id, private=True, owner_id=user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail=f"Dataset {job_in.dataset_id} not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500) from e
    parameters = job_in.parameters
    if parameters is None:
        parameters = model.parameters
    else:
        parameters = {**model.parameters, **parameters}
    # Set job creation limit for user/org
    user_jobs = await Job.objects.filter(owner_id=user_id, closed=False).count()
    if user_jobs >= settings.job_limit:
        raise HTTPException(
            status_code=403,
            detail=f"User has reached the job limit of {settings.job_limit}",
        )

    await Job.objects.create(
        id=job_id,
        name=job_in.name,
        description=job_in.description,
        owner_id=user_id,
        model_id=job_in.model_id,
        dataset_id=job_in.dataset_id,
        model_name=model.name,
        parameters=parameters,
    )
    # Setup Enviroment for job
    asyncio.create_task(
        setup_environment(
            job_id=job_id,
            model_name=model.git_name,
            dataset_name=dataset.git_name,
        )
    )



@api_router.post("/train", tags=["jobs", "models", "results"], summary="Run job to train model")
async def run_train_model(
    train_model_in: TrainModelIn,
    req: Request
) -> Any:
    """Run job to train model."""
    user_id = req.state.user_id
    user_token = req.state.user_token
    # Check if job is ready
    job = await Job.objects.get(id=train_model_in.job_id, owner_id=user_id)
    if not job.ready:
        raise HTTPException(status_code=400, detail=f"Job {train_model_in.job_id} is not ready")
    job = await Job.objects.get(id=train_model_in.job_id)
    dataset = await Dataset.objects.get(id=job.dataset_id, private=False)
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
            dataset_branch=train_model_in.dataset_branch,
            user_token=user_token
        )
    )
    job.ready = False
    job.modified = datetime.datetime.now()
    await job.update()
    return "Training model"

@api_router.post("/upload/test/{job_id}", tags=["jobs", "models", "results"], summary="Upload test data for model")
async def upload_test_data(
    file: Annotated[UploadFile, File(description="Test data file")],
    job_id: uuid.UUID,
) -> str:
    """Upload test data for model."""
    dataset_id = uuid.uuid4()
    filename = file.filename
    if filename is None:
        raise HTTPException(status_code=400, detail="No file provided")
    _, dataset_dir, _ = job_get_dirs(job_id=job_id, dataset_name=str(dataset_id), model_name="")
    filepath = Path(f"{dataset_dir}/{filename}")
    try:
        async with aiofiles.open(filepath, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                await buffer.write(chunk)
    # Catch any errors and delete the file
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await file.close()
    return str(dataset_id)

@api_router.post("/test", tags=["jobs", "models", "results"], summary="Run job to test model")
async def run_test_model(
    test_model_in: TestModelIn,
    req: Request
) -> Any:
    """Run job to test model."""
    user_id = req.state.user_id
    user_token = req.state.user_token
    # Check if job is ready
    job = await Job.objects.get(id=test_model_in.job_id, owner_id=user_id)
    if not job.ready:
        raise HTTPException(status_code=400, detail=f"Job {test_model_in.job_id} is not ready")
    job = await Job.objects.get(id=test_model_in.job_id)

    if test_model_in.dataset.path is None:
        dataset = await Dataset.objects.get(id=job.dataset_id, private=False)
        if dataset is None and user_id is not None:
            dataset = await Dataset.objects.get(id=job.dataset_id, private=True, owner_id=user_id)
            if dataset is None:
                raise HTTPException(status_code=404, detail=f"Dataset {job.dataset_id} not found")
        _,dataset_path,_ = job_get_dirs(job_id=job.id, dataset_name=dataset.git_name, model_name="")
    else:
        _,dataset_path,_ = job_get_dirs(job_id=job.id, dataset_name=str(test_model_in.dataset.path), model_name="")

    match test_model_in.model.type:
        case ModelType.default:
            model = await Model.objects.get(id=job.model_id, private=False)
            if model is None and user_id is not None:
                model = await Model.objects.get(id=job.model_id, private=True, owner_id=user_id)
                if model is None:
                    raise HTTPException(status_code=404, detail=f"Model {job.model_id} not found")
            _,_,model_path = job_get_dirs(job_id=job.id, dataset_name="", model_name=model.git_name)
            pretrained_model_path = f"{model_path}/{model.default_model}"
        case ModelType.pretrained:
            result_id = uuid.UUID(test_model_in.model.result_id)
            train_result = await Result.objects.get(id=result_id)
            job_base_dir,_,_ = job_get_dirs(job_id=job.id, dataset_name="", model_name="")
            pretrained_model_path = f"{job_base_dir}/{str(train_result.id)}/{train_result.pretrained_model}"
        case ModelType.custom:
            # model = await Model.objects.get(id=job.model_id)
            # pretrained_model_path = settings.results_dir + "/" + model.path
            raise HTTPException(status_code=400, detail="Custom model not supported yet")
    loop = asyncio.get_event_loop()
    loop.create_task(test_model(
        dataset_path=dataset_path,
        job=job,
        model=model,
        result_name=test_model_in.name,
        parameters=test_model_in.parameters,
        pretrained_model=pretrained_model_path,
        dataset_branch=test_model_in.dataset.branch,
        model_branch=test_model_in.model.branch,
        user_token=user_token,
        dataset_type=test_model_in.dataset.type,
        model_type=test_model_in.model.type,
    ))
    job.ready = False
    job.modified = datetime.datetime.now()
    await job.update()
    return "Testing model"

# TODO: Add stop job route
