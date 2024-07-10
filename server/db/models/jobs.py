"""JObs model."""
import datetime
from typing import Any
import uuid

import ormar

from server.db.base import BaseMeta

class JobStatus(ormar.Enum):
    """Enum of Job Status"""
    INITIALIZING = "initializing"
    OCCUPIED = "occupied"
    READY = "ready"
    CLOSED = "closed"

class Job(ormar.Model):
    """Job model"""

    class Meta(BaseMeta):
        """Meta class"""

        tablename = "jobs"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    name: str = ormar.String(max_length=100)
    description: str = ormar.String(max_length=500)
    model_id: uuid.UUID = ormar.UUID()
    dataset_id: uuid.UUID = ormar.UUID()
    model_name: str = ormar.String(max_length=200)
    owner_id: str = ormar.String(max_length=100)
    runner_id: str = ormar.String(max_length=100, nullable=True)
    environment: str = ormar.String(max_length=100, nullable=True)
    parameters: dict[str, Any] = ormar.JSON(default={})
    closed: bool = ormar.Boolean(default=False)
    ready: bool = ormar.Boolean(default=False)
    status: str = ormar.String(max_length=100, default=JobStatus.INITIALIZING, choices=list(JobStatus))
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
