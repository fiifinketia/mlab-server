
from enum import Enum
from typing import Any, Optional
import uuid
from pydantic import BaseModel
from server.db.models.jobs import Job
from server.db.models.results import Result


class JobWithResults(Job):
    """Job with results"""
    results: list[Result] = []

class JobIn(BaseModel):
    """Job in"""

    name: str
    description: str
    owner_id: str
    model_id: uuid.UUID
    parameters: Optional[dict[str, Any]]
    dataset_id: uuid.UUID
    # tags: list = []


class TrainModelIn(BaseModel):
    """Train model in"""

    job_id: uuid.UUID
    parameters: dict[str, Any] = {}
    name: str
    model_branch: Optional[str] = None
    dataset_branch: Optional[str] = None

class ModelType(str,Enum):
    default = "default"
    pretrained = "pretrained"
    custom = "custom"

class DatasetType(str,Enum):
    default = "default"
    upload = "upload"
class UseModel(BaseModel):
    type: ModelType
    result_id: Optional[str]
    branch: Optional[str]

class UseDataset(BaseModel):
    type: DatasetType
    branch: Optional[str]
    path: Optional[str]
class TestModelIn(BaseModel):
    """Test model in"""
    name: str
    job_id: uuid.UUID
    parameters: dict[str, Any] = {}
    model: UseModel
    dataset: UseDataset
