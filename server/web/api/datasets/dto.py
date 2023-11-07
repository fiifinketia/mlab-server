from fastapi import File, UploadFile
from pydantic import BaseModel


class DatasetIn(BaseModel):
    """Dataset in"""

    name: str
    description: str
    owner_id: str
    file: UploadFile = File()
    private: bool
    # tags: list = []
