"""Routes for jobs API."""
import os
import uuid
from fastapi import APIRouter, HTTPException, Form
from pydantic import ValidationError
# from server.db.models.jobs import Job
# from server.db.models.ml_models import Model
from server.db.models.datasets import Dataset
from server.web.api.datasets.dto import DatasetIn
from server.web.api.utils import create_git_project, make_git_path
from server.settings import settings

api_router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # adjust the chunk size as desired


class DatasetInForm(DatasetIn):
    private: bool = Form(...)
    name: str = Form(...)
    description: str = Form(...)
    owner_id: str = Form(...)

@api_router.get("", tags=["datasets"], summary="Get All datasets user has access to")
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

@api_router.post("", tags=["datasets"], summary="Upload a new dataset")
async def create_dataset(
        # file: UploadFile = File(...), 
        name: str = Form(...),
        description: str = Form(...),
        private: bool = Form(...),
        owner_id: str = Form(...),
    ) -> Dataset:
    """Upload a new dataset."""
    try:

        dataset_id = uuid.uuid4()

        try:
            os.chdir(settings.datasets_dir)
        except FileNotFoundError:
            os.makedirs(settings.datasets_dir)
            os.chdir(settings.datasets_dir)
        git_path = make_git_path(name)

        filepath = os.path.join(settings.datasets_dir, git_path)
        
        create_git_project(filepath)
        
        try:    
            dataset = await Dataset.objects.create(
                id=dataset_id,
                name=name,
                description=description,
                path="/" + git_path,
                private=private,
                owner_id=owner_id,
            )
            print("dataset created")
        except ValidationError as e:
            print(e)
            raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return dataset
