"""results model."""
import datetime
import uuid

import ormar
from typing import Any
from server.db.base import BaseMeta
from server.db.models.jobs import Job
from enum import Enum

# Enum of Result Type
class ResultType(Enum):
    """Result type enum"""

    train = "train"
    test = "test"

class Result(ormar.Model):
    """Result model"""

    class Meta(BaseMeta):
        """Meta class"""

        tablename = "results"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    owner_id: str = ormar.String(max_length=100, nullable=False)
    name: str = ormar.String(max_length=200, default="test")
    # Result type: [train or test]
    result_type: str = ormar.String(max_length=7, choices=list(ResultType))
    # Foreign key to job
    job = ormar.ForeignKey(Job)
    dataset_id: uuid.UUID = ormar.UUID()
    # path: str = ormar.String(max_length=300)
    status: str = ormar.String(max_length=300)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    metrics: dict[str, float] = ormar.JSON(default=[])
    files: list[str] = ormar.JSON(default=[])
    parameters: dict[str, Any] = ormar.JSON(default={})
    pretrained_model: str = ormar.String(max_length=300, nullable=True)
    predictions: dict[str, Any] = ormar.JSON(default={})
