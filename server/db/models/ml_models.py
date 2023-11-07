import datetime
import uuid

import ormar

from server.db.base import BaseMeta


class Model(ormar.Model):
    """Base model for all models."""

    class Meta(BaseMeta):
        """Meta class for all models."""

        tablename = "ml_models"

    id: uuid.UUID = ormar.UUID(primary_key=True)
    unique_name: str = ormar.String(max_length=200, unique=True)
    name: str = ormar.String(max_length=200)
    entry_point: str = ormar.String(max_length=200, default="train")
    description: str = ormar.String(max_length=200)
    version: str = ormar.String(max_length=200)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    path: str = ormar.String(max_length=200)
    owner_id: str = ormar.String(max_length=200)
