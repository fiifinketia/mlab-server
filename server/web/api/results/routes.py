import datetime
import os
import uuid
import zipfile
from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any
from server.db.models.datasets import Dataset
from server.db.models.ml_models import Model
from server.settings import settings
import pickle
import json
import starlette

from server.db.models.results import Result


api_router = APIRouter()

class TrainResultsIn(BaseModel):
    """Train results in"""

    result_id: uuid.UUID
    files: list[UploadFile] = []
    metrics: Any = {}
    history: Any = {}

@api_router.get("/user/{user_id}", tags=["results"], summary="Get all results for a user")
async def get_results(user_id: str) -> list[dict[str, Any]]:
    """Get all results for a user."""
    results = await Result.objects.select_related("job").all(owner_id=user_id)
    result_list = []
    for result in results:
        dataset = await Dataset.objects.get(id=result.dataset_id)
        model = await Model.objects.get(id=result.job.model_id)
        result_new = {
            "id": result.id,
            "type": result.result_type,
            "job_name": result.job.name,
            "dataset_name": dataset.name,
            "model_name": model.name,
            "model_version": model.version,
            "model_description": model.description,
            "status": result.status,
            "created": result.created,
            "modified": result.modified,
        }
        result_list.append(result_new)
    return result_list

# @api_router.get("/{user_id}/{job_id}", tags=["results"], summary="Get all results for a job")
# async def get_job_results(user_id: str, job_id: str) -> list[Result]:
#     """Get all results for a job."""
#     return await Result.objects.select_related("job").all(owner_id=user_id, id=job_id)
class ResultResponse(BaseModel):
    """Result response"""

    class FileResponse(BaseModel):
        """File"""

        name: str
        size: int
    size: int
    id: uuid.UUID
    owner_id: str
    result_type: str
    job: Any
    dataset_id: uuid.UUID
    status: str
    created: Any
    modified: Any
    metrics: Any
    files: list[FileResponse]
    parameters: dict[str, Any]
    model_name: str
    model_version: str
    model_description: str
    dataset_name: str
    dataset_description: str
    dataset_content: str


@api_router.get("/{result_id}", tags=["results"], summary="Get a result")
async def get_result(result_id: str) -> ResultResponse:
    """Get a result."""
    uuid_result_id = uuid.UUID(result_id)
    # INtiialize result as type Result and size as int
    result = await Result.objects.select_related("job").get(id=uuid_result_id)
    model = await Model.objects.get(id=result.job.model_id)
    dataset = await Dataset.objects.get(id=result.dataset_id)
    files: list[ResultResponse.FileResponse] = []
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    result_size = 0
    for file in result.files:
        file_response = ResultResponse.FileResponse(
            name=file,
            size=os.path.getsize(f"{settings.results_dir}/{str(result_id)}/{file}"),
        )
        files.append(file_response)
        result_size += os.path.getsize(f"{settings.results_dir}/{str(result_id)}/{file}")
    result_response = ResultResponse(
        size=result_size,
        id=result.id,
        owner_id=result.owner_id,
        result_type=result.result_type,
        job=result.job,
        dataset_id=result.dataset_id,
        status=result.status,
        created=result.created,
        modified=result.modified,
        metrics=result.metrics,
        files=files,
        parameters=result.parameters,
        model_name=model.name,
        model_version=model.version,
        model_description=model.description,
        dataset_name=dataset.name,
        dataset_description=dataset.description,
        dataset_content=dataset.content_type,
    )
    return result_response

@api_router.post("/train", tags=["results", "jobs"], summary="Submit training results for a job")
async def submit_train_results(
    request: Request,
    error: bool = False,
) -> None:
    """Submit training results for a job."""
    if error:
        form = await request.form()
        result_id: uuid.UUID = form["result_id"] # type: ignore
        result = await Result.objects.select_related("job").get(id=result_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Result {result_id} not found",
            )
        result.status = "error"
        error_form_files: list[starlette.datastructures.UploadFile] = []
        for key, value in form.items():
            if type(value) == starlette.datastructures.UploadFile:
                error_form_files.append(value)
        files: list[str] = result.files
        # Save plot to results directory
        index = 0
        for file in error_form_files:
            file_name = ""
            if file.filename is not None:
                file_name = file.filename
            else:
                file_name = str(result_id) + str(index) + ".png"
            files.append(file_name)
            file_path = f"{settings.results_dir}/{str(result_id)}/{file_name}"
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            index += 1
        result.files = files
        result.modified = datetime.datetime.now()
        await result.update()
    else:
        form = await request.form()
        metrics = {}
        history = {} # type: ignore
        form_files: list[UploadFile] = []
        for key, value in form.items():
            if key.startswith("metrics"):
                metrics = json.loads(value) # type: ignore
            elif key.startswith("history"):
                history = value # type: ignore
                # 'starlette.datastructures.UploadFile'
            elif type(value) == starlette.datastructures.UploadFile:
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

        new_files: list[str] = result.files

        # Save plot to results directory
        index = 0
        for file in train_results_in.files:
            file_name = ""
            if file.filename is not None:
                file_name = file.filename
            else:
                file_name = str(train_results_in.result_id) + str(index) + ".png"
            new_files.append(file_name)
            file_path = f"{settings.results_dir}/{str(train_results_in.result_id)}/{file_name}"
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            index += 1

        history = train_results_in.history

        # Dump history into pickle file
        with open(f"{settings.results_dir}/{str(train_results_in.result_id)}/history.pkl", "wb") as f:
            pickle.dump(history, f)

        new_files.append("history.pkl")
        result.metrics = train_results_in.metrics
        result.files = new_files
        result.status = "done"
        result.modified = datetime.datetime.now()
        await result.update()
        # Return 200 OK
        return None

@api_router.get("/download/{result_id}", tags=["results"], summary="Download a result")
async def zip_files_for_download(
    result_id: str,
) -> Any:
    """Download a result."""
    result_uuid = uuid.UUID(result_id)
    result = await Result.objects.select_related("job").get(id=result_uuid)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    # Zip all files in result.files
    zip_file_path = f"{result_id}.zip"
    zip_file = zipfile.ZipFile(zip_file_path, "w")
    for file in result.files:
        # write file to zip without directory structure
        file_name = "results/" + file
        zip_file.write(
            f"{settings.results_dir}/{str(result_id)}/{file}",
            arcname=file_name,
        )
    zip_file.close()
    return FileResponse(zip_file_path, filename=f"{result_id}.zip", media_type="application/zip")

@api_router.get("/download/{result_id}/{file_name}", tags=["results"], summary="Download a file from a result")
async def download_file(
    result_id: str,
    file_name: str,
) -> Any:
    """Download a file from a result."""
    result_uuid = uuid.UUID(result_id)
    result = await Result.objects.select_related("job").get(id=result_uuid)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    # Zip all files in result.files
    file_path = f"{settings.results_dir}/{str(result_id)}/{file_name}"
    return FileResponse(file_path, filename=file_name)