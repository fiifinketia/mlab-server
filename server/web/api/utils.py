import os
from git import Repo
from fastapi import HTTPException


def make_git_path(name: str) -> str:
    # use all lower case, replace any spaces with hyphens, and append ".git" to the name.
    return name.lower().replace(" ", "-") + ".git"

def create_git_project(filepath: str) -> None:
    # Check if path to model exists
    if os.path.exists(filepath):
        raise HTTPException(status_code=409, detail=f"Path {filepath} already exists")
    Repo.init(path=filepath, mkdir=True,bare=True)

def print_files_from_git(root, level=0)-> None:
    """Print files from a git repository."""
    for entry in root:
        print(f'{"-" * 4 * level}| {entry.path}, {entry.type}')
        if entry.type == "tree":
            print_files_from_git(entry, level + 1)