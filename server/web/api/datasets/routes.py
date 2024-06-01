"""Routes for jobs API."""
import uuid
from fastapi import APIRouter, HTTPException, Form
from pydantic import ValidationError
# from server.db.models.jobs import Job
# from server.db.models.ml_models import Model
from server.db.models.datasets import Dataset
from server.web.api.datasets.dto import DatasetIn, DatasetResponse
from server.services.git import GitService, RepoNotFoundError, RepoTypes

api_router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # adjust the chunk size as desired


class DatasetInForm(DatasetIn):
    """Dataset form model."""
    private: bool = Form(...)
    name: str = Form(...)
    description: str = Form(...)
    owner_id: str = Form(...)

@api_router.get("", tags=["datasets"], summary="Get All datasets user has access to")
async def fetch_datasets(user_id: str = "") -> list[Dataset]:
    """Get all datasets."""
    all_datasets = await Dataset.objects.all(private=False)
    user_datasets = None
    if user_id is not None:
        user_datasets = await Dataset.objects.all(private=True, owner_id=user_id)
        all_datasets.extend(user_datasets)
    return all_datasets

@api_router.get("/{dataset_id}", tags=["datasets"], summary="Get a dataset")
async def fetch_dataset(dataset_id: str) -> DatasetResponse:
    """Get a dataset."""
    dataset_uuid = uuid.UUID(dataset_id)
    dataset = await Dataset.objects.get(id=dataset_uuid)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    try:
        git = GitService()
        files = git.list_files(dataset.path)
    except RepoNotFoundError:
        files = []

    return DatasetResponse(
        id=str(dataset.id),
        name=dataset.name,
        description=dataset.description,
        path=dataset.path,
        private=dataset.private,
        owner_id=dataset.owner_id,
        created_at=str(dataset.created),
        updated_at=str(dataset.modified),
        files=files,
    )

@api_router.post("", tags=["datasets"], summary="Upload a new dataset")
async def create_dataset(
        dataset_in: DatasetInForm,
    ) -> Dataset:
    """Upload a new dataset."""
    try:

        dataset_id = uuid.uuid4()

        git = GitService()
        git_path = git.create_repo(
            repo_name=dataset_in.name,
            repo_type=RepoTypes.DATASET,
            username=dataset_in.owner_id,
            is_private=dataset_in.private,
        )

        try:
            dataset = await Dataset.objects.create(
                id=dataset_id,
                name=dataset_in.name,
                description=dataset_in.description,
                path=git_path,
                private=dataset_in.private,
                owner_id=dataset_in.owner_id,
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise e

    return dataset
