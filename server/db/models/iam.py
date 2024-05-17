# Identity and Access Management (IAM) models are used to manage user roles and permissions.

# Path: server/db/models/iam.py

import datetime
from typing import List

import ormar

from server.db.base import BaseMeta


class UserKeyPair(ormar.Model):
    """Model for User Key Pair."""

    class Meta(BaseMeta):
        tablename = "user_key_pairs"

    id: str = ormar.String(primary_key=True, max_length=200)
    user_id: str = ormar.String(max_length=200)
    public_key: str = ormar.String(max_length=200)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)