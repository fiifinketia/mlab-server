from ormar import ModelMeta

from server.db.config import database
from server.db.meta import meta


class BaseMeta(ModelMeta):
    """Base metadata for models."""

    database = database
    metadata = meta
