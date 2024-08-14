# Identity and Access Management (IAM) models are used to manage user roles and permissions.

# Path: server/db/models/iam.py

import datetime
from enum import Enum
import uuid

import ormar

from server.db.base import BaseMeta

class Action(str, Enum):
    """Action model."""
    CREATE_DATASET = "create:dataset"
    CREATE_MODEL = "create:model"
    CREATE_JOB = "create:job"
    STOP_JOB = "stop:job"
    CLOSE_JOB = "close:job"
    RUN_JOB = "run:job"
    UPLOAD_TEST_JOB = "upload:test:job"
    RUNNER_BILL = "runner:bill"

class BillingStatus(str, Enum):
    """Billing status model."""
    PAID = "paid"
    PENDING = "pending"



class Billing(ormar.Model):
    """Model for User Key Pair."""

    class Meta(BaseMeta):
        tablename = "billings"

    id: uuid.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    user_id: str = ormar.String(max_length=200)
    created: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    modified: datetime.datetime = ormar.DateTime(default=datetime.datetime.now)
    amount: float = ormar.Float(default=0)
    action: str = ormar.String(nullable=False, choices=list(Action), max_length=200)
    status: str = ormar.String(default=BillingStatus.PENDING, choices=list(BillingStatus), max_length=20)
    description: str = ormar.String(max_length=500)
