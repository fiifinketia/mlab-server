import datetime
from typing import Any
import uuid
import ormar
from pydantic.dataclasses import dataclass
from server.db.base import BaseMeta


class Model(ormar.Model):
    """Base model for all models."""

    class Meta(BaseMeta):
        """Meta class for all models."""

        tablename = "ml_models"

    id: uuid.UUID = ormar.UUID(primary_key=True)
    name: str = ormar.String(max_length=200)
    description: str = ormar.String(max_length=200)
    version: str = ormar.String(max_length=200)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    git_name: str = ormar.String(max_length=200)
    clone_url: str = ormar.String(max_length=300)
    owner_id: str = ormar.String(max_length=200)
    parameters: dict[str, Any] = ormar.JSON(default={})
    # layers: list[dict[str, Any]] = ormar.JSON(default=[])
    private: bool = ormar.Boolean(default=False)
