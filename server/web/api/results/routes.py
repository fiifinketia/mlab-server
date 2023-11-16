import uuid
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Any
from server.settings import settings
import pickle

from server.db.models.results import Result


api_router = APIRouter()

class TrainResultsIn(BaseModel):
    """Train results in"""

    result_id: uuid.UUID
    files: list[UploadFile] = []
    metrics: dict[str, float] = {}
    history: Any = {}

@api_router.get("/{user_id}", tags=["results"], summary="Get all results for a user")
async def get_results(user_id: str) -> list[Result]:
    """Get all results for a user."""
    return await Result.objects.select_related("job").all(owner_id=user_id)

@api_router.get("/{user_id}/{job_id}", tags=["results"], summary="Get all results for a job")
async def get_job_results(user_id: str, job_id: str) -> list[Result]:
    """Get all results for a job."""
    return await Result.objects.select_related("job").all(owner_id=user_id, job_id=job_id)

@api_router.get("/{result_id}", tags=["results"], summary="Get a result")
async def get_result(result_id: str) -> Result:
    """Get a result."""
    result = await Result.objects.select_related("job").get(id=result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    return result

@api_router.post("/train", tags=["results", "jobs"], summary="Submit training results for a job")
async def submit_train_results(
    train_results_in: TrainResultsIn,
) -> None:
    """Submit training results for a job."""
    result = await Result.objects.select_related("job").get(id=train_results_in.result_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Result {train_results_in.result_id} not found",
        )

    files: list[str] = []

    # Save plot to results directory
    index = 0
    for file in train_results_in.files:
        file_type = ""
        if file.filename is not None:
            file_type = file.filename.split(".")[-1]
        else:
            file_type = ".png"
        file_name = str(train_results_in.result_id) + str(index) + file_type
        files.append(file_name)
        file_path = f"{settings.results_dir}/{str(train_results_in.result_id)}/{file_name}"
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        index += 1


    # Dump history into pickle file
    with open(f"{settings.results_dir}/{str(train_results_in.result_id)}/history.pkl", "wb") as f:
        pickle.dump(train_results_in.history, f)

    files.append("history.pkl")
    result.metrics = train_results_in.metrics
    result.files = files
    await result.update()
    # Return 200 OK
    return None
