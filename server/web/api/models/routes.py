"""Routes for models API."""
from typing import Any
import uuid

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Request

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



@api_router.get("", tags=["models"], summary="Get all models")
async def get_models(req: Request) -> list[Model]:
    """Get all models."""
    user_id = req.state.user_id
    all_models = await Model.objects.all(private=False)
    user_models = None
    if user_id is not None:
        user_models = await Model.objects.all(private=True, owner_id=user_id)
        all_models.extend(user_models)
    return all_models

# TODO: add branch name to request query
@api_router.get("/{model_id}", tags=["models"], summary="Get a model")
async def get_modle(model_id: str, req: Request) -> ModelResponse:
    """Get a model."""
    user_id = req.state.user_id
    model_uuid = uuid.UUID(model_id)
    model = await Model.objects.get(id=model_uuid, private=False)
    if model is None and user_id is not None:
        model = await Model.objects.get(id=model_uuid, private=True, owner_id=user_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
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
        git_name=model.git_name,
        clone_url=model.clone_url,
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
    req: Request
) -> Model:
    """Create a new model."""
    model_id = uuid.uuid4()
    user_id = req.state.user_id
    try:

        git = GitService()
        git_path, clone_url = git.create_repo(
            repo_name=create_model_request.name,
            repo_type=RepoTypes.MODEL,
            username=user_id,
            is_private=create_model_request.private,
        )

        model = await Model.objects.create(
            id=model_id,
            name=create_model_request.name,
            description=create_model_request.description,
            owner_id=user_id,
            version=create_model_request.version,
            git_name=git_path,
            clone_url=clone_url,
            parameters=create_model_request.parameters,
            private=create_model_request.private,
        )
    except RepoNotFoundError:
        raise HTTPException(status_code=404, detail="Repository not found")
    return model

@api_router.delete("/{model_id}", tags=["models"], summary="Delete a model")
async def delete_model(model_id: str, req: Request) -> None:
    """Delete a model."""
    user_id = req.state.user_id
    model_uuid = uuid.UUID(model_id)
    model = await Model.objects.get(id=model_uuid, private=False)
    if model is None and user_id is not None:
        model = await Model.objects.get(id=model_uuid, private=True, owner_id=user_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    await Model.objects.delete(id=model_uuid)
    git = GitService()
    git.delete_repo(model.git_name)
    return None
