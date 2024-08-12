"""Routes for jobs API."""
from typing import Annotated, Any, Union
import uuid
from enum import Enum
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Depends

from server.db.models.jobs import Job
from server.web.api.jobs.dto import JobIn, TestModelIn, TrainModelIn
from server.web.api.jobs import service as jobs_service
from server.web.api.billing.service import BillingService
from server.web.api.billing.dto import CheckBillDTO, Action


api_router = APIRouter()

 # adjust the chunk size as desired

@api_router.get("", tags=["jobs"], summary="Get all jobs", response_model=list[Job])
async def get_jobs(req: Request) -> list[Job]:
    """Get all jobs."""
    user_id = req.state.user_id
    return await jobs_service.get_jobs(user_id)


@api_router.post("/stop", tags=["jobs"], summary="Stop all job processes")
async def stop_jobs(req: Request, job_id: uuid.UUID, billings_service: Annotated[BillingService, Depends(BillingService,use_cache=True)]) -> None:
    """Stop a jobs running processes"""
    user_id = req.state.user_id
    await jobs_service.stop_job(user_id, job_id)
    await billings_service.check(
        CheckBillDTO(action=Action.STOP_JOB, data=job_id),
        user_id
    )

@api_router.post("/close", tags=["jobs"], summary="Close a job")
async def close_job(
    job_id: uuid.UUID,
    req: Request,
    billings_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> None:
    """Close a job."""
    user_id = req.state.user_id

    await jobs_service.close_job(user_id, job_id)
    await billings_service.check(
        CheckBillDTO(action=Action.CLOSE_JOB, data=job_id),
        user_id
    )

@api_router.post("", tags=["jobs"], summary="Create a new job")
async def create_job(
    job_in: JobIn,
    req: Request,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> None:
    """Create a new job."""
    user_id = req.state.user_id
    # Find model and get path
    try:
        await jobs_service.create_job(user_id, job_in)
        await billing_service.check(
            CheckBillDTO(action=Action.CREATE_JOB, data=job_in.json()),
            user_id
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e)) from e

class RunJobType(str, Enum):
    TRAIN = "train"
    TEST = "test"

@api_router.post("/run/{job_type}", tags=["jobs", "models", "results"], summary="Run job to train model")
async def run_train_model(
    job_type: RunJobType,
    body: Union[TrainModelIn, TestModelIn],
    req: Request,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> Any:
    """Run job to train model."""
    user_id = req.state.user_id
    match job_type:
        case RunJobType.TRAIN:
            if not isinstance(body, TrainModelIn):
                raise HTTPException(status_code=400, detail="Invalid train model input")
            train = await jobs_service.train(user_id, body)
            await billing_service.check(
                CheckBillDTO(action=Action.RUN_JOB, data=body.json()),
                user_id
            )
            return train
        case RunJobType.TEST:
            if not isinstance(body, TestModelIn):
                raise HTTPException(status_code=400, detail="Invalid test model input")
            test = await jobs_service.test(user_id, body)
            await billing_service.check(
                CheckBillDTO(action=Action.RUN_JOB, data=body.json()),
                user_id
            )
            return test
        case _:
            raise HTTPException(status_code=400, detail="Invalid job type")


@api_router.post("/upload/test/{job_id}", tags=["jobs", "models", "results"], summary="Upload test data for model")
async def upload_test_data(
    file: Annotated[UploadFile, File(description="Test data file")],
    job_id: uuid.UUID,
    req: Request,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> str:
    """Upload test data for model."""
    user_id = req.state.user_id
    # Upload file and get path
    uploaded_file = await jobs_service.upload_file(file, job_id)
    await billing_service.check(
        CheckBillDTO(action=Action.UPLOAD_TEST_JOB, data=job_id),
        user_id
    )
    return uploaded_file
