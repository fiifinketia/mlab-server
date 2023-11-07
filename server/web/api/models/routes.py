"""Routes for models API."""
import os
import uuid

from fastapi import APIRouter, HTTPException

from server.db.models.ml_models import Model
from server.settings import settings

api_router = APIRouter()


@api_router.get("/", tags=["models"], summary="Get all models")
async def get_models() -> list[Model]:
    """Get all models."""
    return await Model.objects.all()


@api_router.post("/", tags=["models"], summary="Create a new model")
async def create_model(
    name: str,
    unique_name: str,
    description: str,
    owner_id: str,
    version: str,
    path: str,
    # tags: list = [],
) -> None:
    """Create a new model."""
    # Check if model unique_name already exists
    if await Model.objects.filter(unique_name=unique_name).exists():
        raise HTTPException(status_code=409, detail=f"Model {unique_name} exists")
    try:
        os.chdir(settings.models_dir)
    except FileNotFoundError:
        os.makedirs(settings.models_dir)
        os.chdir(settings.models_dir)

    # Check if path to model exists
    if not os.path.exists(path):
        raise HTTPException(status_code=409, detail=f"Path {path} does not exist")
    # Get full path to model
    # Create model
    model_id = uuid.uuid4()
    await Model.objects.create(
        id=model_id,
        name=name,
        description=description,
        unique_name=unique_name,
        # tags=tags,
        owner_id=owner_id,
        path=path,
        version=version,
    )
