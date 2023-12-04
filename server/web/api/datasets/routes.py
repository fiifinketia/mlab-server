"""Routes for jobs API."""
import os
import aiofiles
from fastapi import APIRouter, HTTPException, Request, UploadFile, Form, File
# from server.db.models.jobs import Job
# from server.db.models.ml_models import Model
from server.db.models.datasets import Dataset
from server.web.api.datasets.dto import DatasetIn
from server.web.api.datasets.utils import upload_new_dataset
from server.settings import settings

api_router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # adjust the chunk size as desired


class DatasetInForm(DatasetIn):
    private: bool = Form(...)
    name: str = Form(...)
    description: str = Form(...)
    owner_id: str = Form(...)

@api_router.get("/", tags=["datasets"], summary="Get All datasets user has access to")
async def fetch_datasets(user_id: str = "") -> list[Dataset]:
    all_datasets = await Dataset.objects.all(private=False)
    user_datasets = None
    if user_id is not None:
        user_datasets = await Dataset.objects.all(private=True, owner_id=user_id)
        all_datasets.extend(user_datasets)
    return all_datasets

@api_router.get("/{dataset_id}", tags=["datasets"], summary="Get a dataset")
async def fetch_dataset(dataset_id: str) -> Dataset:
    """Get a dataset."""
    dataset = await Dataset.objects.get(id=dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset

@api_router.post("/", tags=["datasets"], summary="Upload a new dataset")
async def upload_dataset(file: UploadFile = File(...), data: DatasetInForm = Form(...)) -> Any:
    """Upload a new dataset."""
    try:

        filename = file.filename
        if filename is None:
            raise HTTPException(status_code=400, detail="No file provided")

        print(filename)
        print(data)

        filepath = os.path.join(settings.datasets_dir, filename)
        async with aiofiles.open(filepath, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                await buffer.write(chunk)

    
        # dataset = await upload_new_dataset(data)
        # Return dataset
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await file.close()
    # return dataset
    

