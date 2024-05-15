import os
import uuid

from fastapi import UploadFile

from server.db.models.datasets import Dataset
from server.settings import settings
from server.web.api.datasets.dto import DatasetIn

async def create_file_and_get_path(dataset_id: uuid.UUID, file: UploadFile) -> str:
    """Create file and get path"""
    # Create the file path
    try:
        os.chdir(settings.datasets_dir)
    except FileNotFoundError:
        os.makedirs(settings.datasets_dir)
        os.chdir(settings.datasets_dir)
    datasets_path = os.getcwd()
    file_type = file.filename.split(".")[-1] if file.filename else ""
    file_path = os.path.join(datasets_path, f"{dataset_id}.{file_type}")

    # Create the file and write content to it
    with open(file_path, "wb") as out_file:
        content = await file.read()  # read the file content
        out_file.write(content)

    # Return the file path
    # Trim path to remove settings.dataset_path
    file_path = file_path.replace(settings.datasets_dir, "")
    return file_path


async def upload_new_dataset(
    dataset_in: DatasetIn,
) -> Dataset:
    """Upload a new dataset."""
    # Upload dataset
    dataset_id = uuid.uuid4()
    path = await create_file_and_get_path(dataset_id=dataset_id, file=dataset_in.file)
    dataset = await Dataset.objects.create(
        id=dataset_id,
        name=dataset_in.name,
        description=dataset_in.description,
        path=path,
        content_type=dataset_in.file.content_type,
        private=dataset_in.private,
        owner_id=dataset_in.owner_id,
    )
    # Return dataset
    return dataset
