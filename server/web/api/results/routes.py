import os
import uuid
import zipfile
from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any
from server.db.models.datasets import Dataset
from server.settings import settings
import pickle
import json

from server.db.models.results import Result


api_router = APIRouter()

class TrainResultsIn(BaseModel):
    """Train results in"""

    result_id: uuid.UUID
    files: list[UploadFile] = []
    metrics: dict[str, float] = {}
    history: Any = {}

@api_router.get("/{user_id}", tags=["results"], summary="Get all results for a user")
async def get_results(user_id: str) -> list[dict[str, Any]]:
    """Get all results for a user."""
    results = await Result.objects.select_related("job").all(owner_id=user_id)
    result_list = []
    for result in results:
        dataset = await Dataset.objects.get(id=result.dataset_id)
        result_new = {
            "id": result.id,
            "type": result.result_type,
            "job_name": result.job.name,
            "dataset_name": dataset.name,
            "model_name": result.job.model_name,
            "status": result.status,
            "created": result.created,
            "modified": result.modified,
        }
        result_list.append(result_new)
    return result_list

@api_router.get("/{user_id}/{job_id}", tags=["results"], summary="Get all results for a job")
async def get_job_results(user_id: str, job_id: str) -> list[Result]:
    """Get all results for a job."""
    return await Result.objects.select_related("job").all(owner_id=user_id, id=job_id)

@api_router.get("/{result_id}", tags=["results"], summary="Get a result")
async def get_result(result_id: str) -> Result:
    """Get a result."""
    result = await Result.objects.select_related("job").get(id=result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    return result

@api_router.post("/train", tags=["results", "jobs"], summary="Submit training results for a job")
async def submit_train_results(
    request: Request,
) -> None:
    """Submit training results for a job."""
    form = await request.form()
    metrics = {}
    history = {} # type: ignore
    form_files: list[UploadFile] = []
    for key, value in form.items():
        if key.startswith("metrics"):
            metrics = json.loads(value) # type: ignore
        elif key.startswith("history"):
            history = value # type: ignore
        elif key.startswith("files"):
            form_files.append(value) # type: ignore
    result_id: uuid.UUID = form["result_id"] # type: ignore
    train_results_in = TrainResultsIn(
        result_id=result_id,
        files=form_files,
        metrics=metrics,
        history=history,
    )
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

    history = train_results_in.history

    # Dump history into pickle file
    with open(f"{settings.results_dir}/{str(train_results_in.result_id)}/history.pkl", "wb") as f:
        pickle.dump(history, f)

    files.append("history.pkl")
    result.metrics = train_results_in.metrics
    result.files = files
    result.status = "done"
    await result.update()
    # Return 200 OK
    return None

@api_router.post("/download/{result_id}", tags=["results"], summary="Download a result")
async def zip_files_for_download(
    result_id: str,
) -> Any:
    """Download a result."""
    result = await Result.objects.select_related("job").get(id=result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    # Zip all files in result.files
    with zipfile.ZipFile(f"{settings.results_dir}/tmp/{result_id}.zip", "w") as zipf:
        zipdir(f"{settings.results_dir}/{result_id}", zipf)
    # Return zip file for download
    # Send response and delete zip file
    response = FileResponse(f"{settings.results_dir}/tmp/{result_id}.zip", media_type="application/octet-stream")
    os.remove(f"{settings.results_dir}/tmp/{result_id}.zip")
    return response

def zipdir(path: str, ziph: Any) -> None:
    """ ziph is zipfile handle"""
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), 
                       os.path.relpath(os.path.join(root, file), 
                                       os.path.join(path, '..')))

