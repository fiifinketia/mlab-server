"""JObs model."""
import datetime
from typing import Any
import uuid

import ormar

from server.db.base import BaseMeta


class Job(ormar.Model):
    """Job model"""

    class Meta(BaseMeta):
        """Meta class"""

        tablename = "jobs"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    name: str = ormar.String(max_length=100)
    description: str = ormar.String(max_length=500)
    model_id: uuid.UUID = ormar.UUID()
    model_name: str = ormar.String(max_length=200)
    owner_id: str = ormar.String(max_length=100)
    repo_hash: str = ormar.String(max_length=100, nullable=True)
    parameters: dict[str, Any] = ormar.JSON(default={})
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
