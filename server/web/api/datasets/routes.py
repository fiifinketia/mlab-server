"""Routes for jobs API."""

from fastapi import APIRouter, HTTPException, Request

# from server.db.models.jobs import Job
# from server.db.models.ml_models import Model
from server.db.models.datasets import Dataset
from server.web.api.datasets.dto import DatasetIn
from server.web.api.datasets.utils import upload_new_dataset

api_router = APIRouter()


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
async def upload_dataset(request: Request) -> Dataset:
    """Upload a new dataset."""
    form = await request.form()
    is_private = False
    if "private" in form:
        is_private = form["private"] == "true"
    # Explicitly convert to str to avoid error
    file = form["file"]  # type: ignore
    dataset_in = DatasetIn(
        name=str(form["name"]),
        description=str(form["description"]),
        owner_id=str(form["owner_id"]),
        file=file,  # type: ignore
        private=is_private,
    )
    dataset = await upload_new_dataset(dataset_in)
    # Return dataset
    return dataset
