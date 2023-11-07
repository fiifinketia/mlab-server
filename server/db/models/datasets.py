import datetime
import uuid

import ormar

from server.db.base import BaseMeta


class Dataset(ormar.Model):
    """Base model for all datasets."""

    class Meta(BaseMeta):
        """Meta class for all datasets."""

        tablename = "datasets"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    name: str = ormar.String(max_length=200)
    description: str = ormar.String(max_length=200, nullable=True)
    path: str = ormar.String(max_length=200)
    content_type: str = ormar.String(max_length=100)
    private: bool = ormar.Boolean(default=False)
    owner_id: str = ormar.String(max_length=200)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
