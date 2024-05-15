"""Routes for models API."""
import os
from typing import Any
import uuid

from pydantic import BaseModel

from fastapi import APIRouter

from server.db.models.ml_models import Model
from server.settings import settings
from server.web.api.utils import create_git_project, make_git_path

api_router = APIRouter()

class CreateModelRequest(BaseModel):
    name: str
    description: str
    owner_id: str
    version: str
    parameters: dict[str, Any]
    private: bool = False
    default_model: str = None



@api_router.get("", tags=["models"], summary="Get all models")
async def get_models() -> list[Model]:
    """Get all models."""
    return await Model.objects.all()


@api_router.post("", tags=["models"], summary="Create a new model")
async def create_model(
    create_model_request: CreateModelRequest,
) -> None:
    """Create a new model."""
    model_id = uuid.uuid4()
    try:
        os.chdir(settings.models_dir)
    except FileNotFoundError:
        os.makedirs(settings.models_dir)
        os.chdir(settings.models_dir)

    # Check if path to model exists
    git_path = make_git_path(create_model_request.name)

    filepath = os.path.join(settings.models_dir, git_path)

    create_git_project(filepath)

    # Get full path to model
    # Create model
    model_id = uuid.uuid4()
    # Serialize parameters and layers
    # parameters = []
    # for parameter in create_model_request.parameters:
    #     parameters.append(parameter.dict())
    # layers = []
    # for layer in create_model_request.layers:
    #     layers.append(layer.dict())
    await Model.objects.create(
        id=model_id,
        name=create_model_request.name,
        description=create_model_request.description,
        owner_id=create_model_request.owner_id,
        version=create_model_request.version,
        path="/" + git_path,
        parameters=create_model_request.parameters,
        private=create_model_request.private,
        default_model=create_model_request.default_model,
    )
