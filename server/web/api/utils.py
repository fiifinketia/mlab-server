import os
from typing import Any
from git import PathLike, Repo, Tree
from fastapi import HTTPException



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