
from typing import Any
from pydantic import BaseModel


class ModelResponse(BaseModel):
    """Model response"""

    id: str
    name: str
    description: str
    git_name: str
    clone_url: str
    private: bool
    owner_id: str
    created_at: str
    updated_at: str
    parameters: dict[str, Any]
    layers: list[dict[str, Any]] = []
    files: list[Any] = []
    # tags: list = []
