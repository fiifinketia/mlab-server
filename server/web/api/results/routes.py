"""Routes for results."""
import datetime
import os
import uuid
import zipfile
import json
from typing import Any
import starlette
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel # pylint: disable=no-name-in-module
from server.db.models.datasets import Dataset
from server.db.models.ml_models import Model
from server.settings import settings

from server.db.models.results import Result
from server.web.api.utils import job_get_dirs


api_router = APIRouter()

@api_router.get("/user", tags=["results"], summary="Get all results for a user")
async def get_results(req: Request) -> list[dict[str, Any]]:
    """Get all results for a user."""
    user_id = req.state.user_id
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
    )
    return result_response

@api_router.post("/submit", tags=["results", "jobs"], summary="Submit pm results for a job")
async def submit_pm_results(
    request: Request,
    error: bool = False,
) -> None:
    """Submit training results for a job."""
    result: Result
    if error:
        form = await request.form()
        result_id: uuid.UUID = uuid.UUID(form["result_id"]) # type: ignore
        result = await Result.objects.select_related("job").get(id=result_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Result {result_id} not found",
            )
        result.status = "error"
        error_form_files: list[str] = []
        for key, value in form.items():
            # error file is a file with name error.txt
            if type(value) == starlette.datastructures.UploadFile:
                error_form_files.append(value.filename if value.filename is not None else "error.txt")
                job_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
                file_path = f"{job_base_dir}/{str(result_id)}/{value.filename}"
                with open(file_path, "wb") as f:
                    f.write(value.file.read())

        result.files = error_form_files
        result.modified = datetime.datetime.now()
        await result.update()
    else:
        form = await request.form()
        metrics = {}
        predictions = {} # type: ignore
        form_files: list[str] = []
        for key, value in form.items():
            if key.startswith("metrics"):
                metrics = json.loads(value) # type: ignore
            elif key.startswith("pretrained_model"):
                pretrained_model = str(value)
            elif key.startswith("predictions"):
                predictions = json.loads(value) # type: ignore
            elif key.startswith("pkg_name"):
                pkg_name = str(value)
            elif isinstance(value, starlette.datastructures.UploadFile):
                file_name = value.filename if value.filename is not None else key
                form_files.append(file_name)
                job_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
                file_path = f"{job_base_dir}/{str(result_id)}/{file_name}"
                with open(file_path, "wb") as f:
                    f.write(value.file.read())
        result_id: uuid.UUID = uuid.UUID(form["result_id"]) # type: ignore
        result = await Result.objects.select_related("job").get(id=result_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Result {result_id} not found",
            )

        result.files.extend(form_files)
        result.metrics = metrics
        result.status = "done"
        if pkg_name == "pymlab.train":
            result.pretrained_model = pretrained_model
        else:
            result.predictions = predictions

        result.modified = datetime.datetime.now()
        await result.update()
        # Return 200 OK

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
