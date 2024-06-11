"""This module contains the functions to run the cog commands"""
from concurrent.futures import ProcessPoolExecutor
import subprocess
import os
import sys
from typing import Any
import uuid
from pathlib import Path
from fastapi import HTTPException

from server.services.git import GitService
from server.web.api.utils import job_get_dirs
from server.settings import settings

async def run(
    name: str,
    at: str,
    dataset_dir: str,
    base_dir: str,
    result_id: uuid.UUID,
    api_url: str,
    user_token: str,
    job_id: uuid.UUID,
    trained_model: str | None = None,
) -> None:
    """Run a script in a cog environment using ProcessPoolExecutor"""
    executor = ProcessPoolExecutor()

    run_script = build_cli_script(
        name=name,
        dataset_dir=dataset_dir,
        base_dir=base_dir,
        result_id=result_id,
        api_url=api_url,
        user_token=user_token,
        trained_model=trained_model,
        job_id=job_id
    )
    stdout_file_path = Path(f"{base_dir}/{str(result_id)}/stdout.log").resolve()
    executor.submit(
        run_process_with_std,
        run_script=run_script,
        stdout_file_path=stdout_file_path,
        at=at
    )
def build_cli_script(
    name: str,
    dataset_dir: str,
    base_dir: str,
    result_id: uuid.UUID,
    api_url: str,
    user_token: str,
    job_id: uuid.UUID,
    trained_model: str | None = None,
) -> str:
    """Build a cog command"""
    dataset_dir = replace_source_with_destination(dataset_dir, base_dir)
    run_script = f"cog train -n {str(job_id)} -i dataset={dataset_dir} -i result_id={result_id} -i api_url={api_url} -i pkg_name={name} -i user_token={user_token}"
    if trained_model is not None:
        run_script += f" -i trained_model={trained_model}"
    # Mount the base directory
    run_script += f" --mount type=bind,source={base_dir},target={settings.cog_base_dir}"
    return run_script

def run_process_with_std(run_script: str, stdout_file_path: Path, at: str) -> None:
    """Run a process with stderr and stdout"""
    with stdout_file_path.open("wb") as stdout_file:
        subprocess.run(run_script, stdout=stdout_file, stderr=subprocess.STDOUT,cwd=at, shell=True, executable="/bin/bash", check=True)

async def setup(
        job_id: uuid.UUID,
        dataset_name: str,
        model_name: str,
        dataset_branch: str | None = None,
        model_branch: str | None = None,
    ) -> bool:
    """Setup the environment for the job"""
    # Clone Dataset to job_results_dir
    git = GitService()

    # clone dataset and model to a tmp directory and discard after use
    _, dataset_path, model_path = job_get_dirs(job_id, dataset_name, model_name)
    # clone specific jobb.repo_hash branch
    try:
        git.clone_repo(repo_name_with_namspace=dataset_name, to=dataset_path, branch=dataset_branch)
        git.clone_repo(repo_name_with_namspace=model_name, to=model_path, branch=model_branch)
        # run_install_requirements(model_path, job_id)
    except Exception as e:
        remove(job_id, dataset_name, model_name)
        raise HTTPException(status_code=400, detail=f"Error Setting up Docker Environment: {str(e)}")

    # TODO: Setup cog option to build without predictor
    # try:
    #     # build cog image
    #     run_script = f"cog build -t {str(job_id)}"
    #     subprocess.run(
    #         run_script,
    #         shell=True,
    #         executable="/bin/bash",
    #         cwd=model_path,
    #         check=True,
    #     )
    # except Exception as e:
    #     remove_docker(job_id)
    #     raise HTTPException(status_code=400, detail=f"Error Setting up Docker Environment: {str(e)}")

    return True

async def prepare(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> bool:
    """Prepare the environment for the job"""
    # Clone Dataset to job_results_dir
    git = GitService()
    _, _, model_path = job_get_dirs(job_id, dataset_name, model_name)

    try:
        # run git
        git.fetch(repo_name_with_namspace=model_name, to=model_path, branch= model_branch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error Preparing Docker Environment: {str(e)}")

    return True

def stop(job_id: uuid.UUID) -> bool:
    """Stop the jobs for container"""
    # get the results from running this command f"docker ps -a -q  --filter ancestor={str(job_id)}"
    process = subprocess.run(f"docker ps -a -q  --filter ancestor={str(job_id)}", shell=True, stdout=subprocess.PIPE, executable="/bin/bash", check=False)
    if process.returncode!= 0:
        return False
    # get results from stdout
    results = process.stdout.decode("utf-8").split("\n")
    for result in results:
        if result == "":
            continue
        os.system(f"docker stop {result}")
        os.system(f"docker rm {result}")
    return True
def remove(job_id: uuid.UUID, dataset_name: str, model_name: str) -> bool:
    """Remove the environment for the job"""
    _, dataset_path, model_path = job_get_dirs(job_id, dataset_name, model_name)
    os.system(f"rm -rf {dataset_path}")  # noqa: F821
    os.system(f"rm -rf {model_path}")
    return True

def remove_docker(job_id: uuid.UUID) -> None:
    """Remove docker image which serves as env from machine"""
    os.system(f"docker rmi {str(job_id)}")

def replace_source_with_destination(at: str, base_dir: str) -> str:
    """Replace the source directory with the destination directory"""
    return at.replace(base_dir, settings.cog_base_dir)
