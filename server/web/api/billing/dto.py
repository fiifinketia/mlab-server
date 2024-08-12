from enum import Enum
from pydantic import BaseModel
from typing import Any


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

class BalanceBillDTO(BaseModel):
    """DTO for balance bill."""
    action: Action
    data: Any

class CheckBillDTO(BaseModel):
    """Check bill model."""
    action: Action
    data: Any
