from typing import Annotated
from fastapi import APIRouter, HTTPException, Header
from git import Union

from server.db.utils import create_database, drop_database
from server.settings import settings
from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result

router = APIRouter()


@router.get("/health")
def health_check() -> None:
    """
    Checks the health of a project.

    It returns 200 if the project is healthy.
    """
    return {"status": "healthy"}