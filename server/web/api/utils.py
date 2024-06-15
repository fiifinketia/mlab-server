import os
from pathlib import Path
from typing import Any
import uuid
from git import PathLike, Repo, Tree
from fastapi import HTTPException

from server.settings import settings



def make_git_path(name: str) -> str:
    # use all lower case, replace any spaces with hyphens, and append ".git" to the name.
    return name.lower().replace(" ", "-") + ".git"

def create_git_project(filepath: str) -> None:
    # Check if path to model exists
    if os.path.exists(filepath):
        raise HTTPException(status_code=409, detail=f"Path {filepath} already exists")
    Repo.init(path=filepath, mkdir=True,bare=True)

def list_files_from_git(root: Tree, level:int=0)-> list[Any]:
    """list files from a git repository."""
    files = []
    for item in root:
        if item.type == "blob":
            files.append(item.path)
        elif item.type == "tree":
            files.extend(list_files_from_git(item, level + 1))
    return files


def job_get_dirs(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
) -> tuple[str, str, str]:
    """Get directories for dataset and model"""
    base_dir = settings.results_dir + "/" +str(job_id)
    dataset_path = base_dir + "/" + dataset_name
    model_path = base_dir + "/" + model_name
    os.makedirs(dataset_path, exist_ok=True)
    os.makedirs(model_path, exist_ok=True)
    return base_dir, dataset_path, model_path

def get_files_in_path(path: Path) -> list[str]:
    # get all files and files in subdirectories in path
    files = []
    for root, _, file in os.walk(path):
        for f in file:
            # remove file parent directory from path
            filepath = os.path.relpath(os.path.join(root, f), path)
            files.append(filepath)
    print(files)
    return files
