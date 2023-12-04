"""Routes for jobs API."""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Any
# from server.db.models.jobs import Job
# from server.db.models.ml_models import Model
from server.db.models.datasets import Dataset
from server.web.api.datasets.dto import DatasetIn
from server.web.api.datasets.utils import upload_new_dataset
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator
import streaming_form_data
from starlette.requests import ClientDisconnect
import os

api_router = APIRouter()

MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # = 4GB
MAX_REQUEST_BODY_SIZE = MAX_FILE_SIZE + 1024

class MaxBodySizeException(Exception):
    def __init__(self, body_len: str):
        self.body_len = body_len

class MaxBodySizeValidator:
    def __init__(self, max_size: int) -> None:
        """Initialize the validator"""
        self.body_len = 0
        self.max_size = max_size

    def __call__(self, chunk: bytes)-> None:
        """Validate the size of the request body"""
        self.body_len += len(chunk)
        if self.body_len > self.max_size:
            raise MaxBodySizeException(body_len=str(self.body_len))



@api_router.get("/", tags=["datasets"], summary="Get All datasets user has access to")
async def fetch_datasets(user_id: str = "") -> list[Dataset]:
    all_datasets = await Dataset.objects.all(private=False)
    user_datasets = None
    if user_id is not None:
        user_datasets = await Dataset.objects.all(private=True, owner_id=user_id)
        all_datasets.extend(user_datasets)
    return all_datasets

@api_router.get("/{dataset_id}", tags=["datasets"], summary="Get a dataset")
async def fetch_dataset(dataset_id: str) -> Dataset:
    """Get a dataset."""
    dataset = await Dataset.objects.get(id=dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset

@api_router.post("/", tags=["datasets"], summary="Upload a new dataset")
async def upload_dataset(request: Request) -> Any:
    """Upload a new dataset."""
    body_validator = MaxBodySizeValidator(MAX_REQUEST_BODY_SIZE)
    filename = request.headers.get('Filename')
    
    if not filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail='Filename header is missing')
    try:
        filepath = os.path.join('./', os.path.basename(filename)) 
        file_ = FileTarget(filepath, validator=MaxSizeValidator(MAX_FILE_SIZE))
        data = ValueTarget()
        parser = StreamingFormDataParser(headers=request.headers)
        parser.register('file', file_)
        parser.register('data', data)
        
        async for chunk in request.stream():
            body_validator(chunk)
            parser.data_received(chunk)
    except ClientDisconnect:
        print("Client Disconnected")
    except MaxBodySizeException as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
           detail=f'Maximum request body size limit ({MAX_REQUEST_BODY_SIZE} bytes) exceeded ({e.body_len} bytes read)')
    except streaming_form_data.validators.ValidationError:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
            detail=f'Maximum file size limit ({MAX_FILE_SIZE} bytes) exceeded') 
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='There was an error uploading the file') 
   
    if not file_.multipart_filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='File is missing')

    print(data.value.decode())
    print(file_.multipart_filename)
        
    return {"message": f"Successfuly uploaded {filename}"}
