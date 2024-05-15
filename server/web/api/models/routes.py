"""Routes for models API."""
import os
from typing import Any
import uuid

from git import Repo
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException
from git.cmd import Git

from server.db.models.ml_models import Model
from server.settings import settings
from server.web.api.models.dto import ModelResponse
from server.web.api.utils import create_git_project, list_files_from_git, make_git_path

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

@api_router.get("/{model_id}", tags=["models"], summary="Get a model")
async def get_modle(model_id: str) -> ModelResponse:
    """Get a model."""
    model_uuid = uuid.UUID(model_id)
    model = await Model.objects.get(id=model_uuid)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    repo = Repo(f"{settings.models_dir}{model.path}")
    try:
        files = list_files_from_git(repo.head.commit.tree)
    except:
        files = []
    return ModelResponse(
        id=str(model.id),
        name=model.name,
        description=model.description,
        path=model.path,
        private=model.private,
        owner_id=model.owner_id,
        created_at=str(model.created),
        updated_at=str(model.modified),
        parameters=model.parameters,
        files=files,
    )


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
