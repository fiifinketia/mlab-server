"""Routes for models API."""
from typing import Any
import uuid

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from server.db.models.ml_models import Model
from server.web.api.models.dto import ModelResponse
from server.services.git import GitService, RepoNotFoundError, RepoTypes

api_router = APIRouter()

class CreateModelRequest(BaseModel):
    """Request model for creating a new model."""
    name: str
    description: str
    owner_id: str
    version: str
    parameters: dict[str, Any]
    private: bool = False
    default_model: str | None = None



@api_router.get("", tags=["models"], summary="Get all models")
async def get_models() -> list[Model]:
    """Get all models."""
    return await Model.objects.all()

# TODO: add branch name to request query
@api_router.get("/{model_id}", tags=["models"], summary="Get a model")
async def get_modle(model_id: str) -> ModelResponse:
    """Get a model."""
    model_uuid = uuid.UUID(model_id)
    model = await Model.objects.get(id=model_uuid)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    try:
        git = GitService()
        files = git.list_files(model.path)
    except RepoNotFoundError:
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

    git = GitService()
    git_path = git.create_repo(
        repo_name=create_model_request.name,
        repo_type=RepoTypes.MODEL,
        username=create_model_request.owner_id,
        is_private=create_model_request.private,
    )

    await Model.objects.create(
        id=model_id,
        name=create_model_request.name,
        description=create_model_request.description,
        owner_id=create_model_request.owner_id,
        version=create_model_request.version,
        path=git_path,
        parameters=create_model_request.parameters,
        private=create_model_request.private,
        default_model=create_model_request.default_model,
    )
