"""results model."""
import datetime
import uuid

import ormar

from server.db.base import BaseMeta
from server.db.models.jobs import Job


class Result(ormar.Model):
    """Result model"""

    class Meta(BaseMeta):
        """Meta class"""

        tablename = "results"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    # Foreign key to job
    job = ormar.ForeignKey(Job)
    dataset_id: uuid.UUID = ormar.UUID()
    # path: str = ormar.String(max_length=300)
    status: str = ormar.String(max_length=300)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
