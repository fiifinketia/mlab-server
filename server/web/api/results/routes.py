"""Routes for results."""
import asyncio
import datetime
import os
from pathlib import Path
import uuid
import zipfile
import json
from typing import Any
import starlette
from fastapi import APIRouter, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel # pylint: disable=no-name-in-module
from server.db.models.datasets import Dataset
from server.db.models.ml_models import Model

from server.db.models.results import Result
from server.web.api.utils import get_files_in_path, job_get_dirs


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
    pretrained_model: str


@api_router.get("/{result_id}", tags=["results"], summary="Get a result", response_model=ResultResponse)
async def get_result(result_id: str, req: Request) -> ResultResponse:
    """Get a result."""
    uuid_result_id = uuid.UUID(result_id)
    user_id = req.state.user_id
    # INtiialize result as type Result and size as int
    result = await Result.objects.select_related("job").get(id=uuid_result_id, owner_id=user_id)
    model = await Model.objects.get(id=result.job.model_id)
    dataset = await Dataset.objects.get(id=result.dataset_id)
    files: list[ResultResponse.FileResponse] = []
    jobs_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
    result_dir = Path(f"{jobs_base_dir}/{str(result_id)}")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    result_files = get_files_in_path(result_dir)
    result_size = 0
    for file in result_files:
        size = os.path.getsize(f"{result_dir}/{file}")
        file_response = ResultResponse.FileResponse(
            name=file,
            size=os.path.getsize(f"{result_dir}/{file}"), # type: ignore
        )
        files.append(file_response)
        result_size += size
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
        pretrained_model=result.pretrained_model,
    )
    return result_response

@api_router.post("/submit", tags=["results", "jobs"], summary="Submit pm results for a job")
async def submit_pm_results(
    request: Request,
    error: bool = False,
) -> None:
    """Submit training results for a job."""
    user_id = request.state.user_id
    result: Result
    form = await request.form()
    result_id: uuid.UUID = uuid.UUID(form["result_id"]) # type: ignore
    result = await Result.objects.select_related("job").get(id=result_id, owner_id=user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Result {result_id} not found",
        )
    if error:
        result.status = "error"
        for key, value in form.items():
            # error file is a file with name error.txt
            if type(value) == starlette.datastructures.UploadFile:
                job_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
                file_path = Path(f"{job_base_dir}/{str(result_id)}/{value.filename}")
                os.makedirs(file_path.parent, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(value.file.read())

        result.modified = datetime.datetime.now()
        await result.update()
    else:
        form = await request.form()
        metrics = {}
        predictions = {} # type: ignore
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
                job_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
                file_path = Path(f"{job_base_dir}/{str(result_id)}/{file_name}")
                os.makedirs(file_path.parent, exist_ok=True)
                with file_path.open("wb") as f:
                    f.write(value.file.read())
        result.metrics = metrics
        result.status = "done"
        if pkg_name == "pymlab.train":
            result.pretrained_model = pretrained_model
        else:
            result.predictions = predictions

        result.modified = datetime.datetime.now()
        await result.update()
    result.job.ready = True
    result.job.modified = datetime.datetime.now()
    await result.job.update()

@api_router.get("/download/{result_id}", tags=["results"], summary="Download a result")
async def zip_files_for_download(
    result_id: str,
    req: Request
) -> Any:
    """Download a result."""
    user_id = req.state.user_id
    result_uuid = uuid.UUID(result_id)
    result = await Result.objects.select_related("job").get(id=result_uuid, owner_id=user_id)
    jobs_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
    result_dir = Path(f"{jobs_base_dir}/{str(result_id)}")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    zip_file_path = f"{result_id}.zip"
    zip_file = zipfile.ZipFile(zip_file_path, "w")
    result_files = get_files_in_path(result_dir)
    for file in result_files:
        # write file to zip without directory structure
        file_name = "results/" + file
        zip_file.write(
            f"{jobs_base_dir}/{str(result_id)}/{file}",
            arcname=file_name,
        )
    zip_file.close()
    return FileResponse(zip_file_path, filename=f"{result_id}.zip", media_type="application/zip")

@api_router.get("/download/{result_id}/{file_name:path}", tags=["results"], summary="Download a file from a result")
async def download_file(
    result_id: str,
    file_name: str,
    req: Request
) -> Any:
    """Download a file from a result."""
    user_id = req.state.user_id
    result_uuid = uuid.UUID(result_id)
    result = await Result.objects.select_related("job").get(id=result_uuid, owner_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    jobs_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
    file_path = Path(f"{jobs_base_dir}/{str(result_id)}/{file_name}")
    return FileResponse(file_path, filename=file_name)

# @api_router.get("/stream/{result_id}/{file_name}")
# async def stream_file(
#     result_id: str,
#     file_name: str,
#     websocket: WebSocket,
#     req: Request,
# ) -> None:
#     """Stream a file from a result."""
#     user_id = req.state.user_id
#     result_uuid = uuid.UUID(result_id)
#     result = await Result.objects.select_related("job").get(id=result_uuid, owner_id=user_id)
#     if result is None:
#         raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
#     jobs_base_dir, _, _ = job_get_dirs(result.job.id, "", "")
#     file_path = Path(f"{jobs_base_dir}/{str(result_id)}/{file_name}")
#     await websocket.accept()
#     while True:
#         await asyncio.sleep(0.1)
#         payload = next(file_path.open("r"))
#         await websocket.send_json(payload)
