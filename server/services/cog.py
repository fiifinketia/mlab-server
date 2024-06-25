"""This module contains the functions to run the cog commands"""
from concurrent.futures import ProcessPoolExecutor
import subprocess
import os, shutil
from typing import Any, Callable, Iterable
import uuid
from pathlib import Path
from fastapi import HTTPException

from server.services.git import GitService
from server.web.api.utils import job_get_dirs
from server.settings import settings

def copytree(
        src: str,
        dst: str,
        symlinks: bool=False,
        ignore: Callable[[str, list[str]], Iterable[str]] | Callable[[Any, list[str]], Iterable[str]] | None = None,
    ) -> None:
    """
    Copy a directory tree from src to dst.

    This function copies an entire directory tree from source (src) to destination (dst).
    It uses the shutil.copytree() function for copying directories and shutil.copy2() for copying files.

    Parameters:
    - src (str): The source directory path.
    - dst (str): The destination directory path.
    - symlinks (bool, optional): If True, symbolic links in the source tree are treated as symbolic links. Defaults to False.
    - ignore (callable, optional): A function that takes a directory name and a list of filenames in that directory as input and returns a list of filenames to ignore. Defaults to None.

    Returns:
    None

    Raises:
    - Exception: If an error occurs during the copying process.
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


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
    """
    Run a script in a cog environment using ProcessPoolExecutor.

    This function is responsible for executing a command-line interface (CLI) script in a cog environment.
    It uses Python's concurrent.futures.ProcessPoolExecutor to run the script asynchronously.

    Parameters:
    - name (str): The name of the cog.
    - at (str): The directory path where the script should be executed.
    - dataset_dir (str): The directory path of the dataset.
    - base_dir (str): The base directory path.
    - result_id (uuid.UUID): The unique identifier for the result.
    - api_url (str): The URL of the API.
    - user_token (str): The user's authentication token.
    - job_id (uuid.UUID): The unique identifier for the job.
    - trained_model (str | None, optional): The path to the trained model. Defaults to None.

    Returns:
    None

    Raises:
    - Any: Any exceptions raised during the execution of the script.
    """
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
    """
    Build a cog command to be executed in a subprocess.

    This function constructs a command-line interface (CLI) script for training a cog model.
    The script includes parameters for the dataset directory, base directory, result ID, API URL,
    user token, job ID, and an optional trained model path. The script also includes a mount
    command to bind the base directory to a specific target directory in the cog environment.

    Parameters:
    - name (str): The name of the cog.
    - dataset_dir (str): The directory path of the dataset.
    - base_dir (str): The base directory path.
    - result_id (uuid.UUID): The unique identifier for the result.
    - api_url (str): The URL of the API.
    - user_token (str): The user's authentication token.
    - job_id (uuid.UUID): The unique identifier for the job.
    - trained_model (str | None, optional): The path to the trained model. Defaults to None.

    Returns:
    str: The constructed CLI script as a string.
    """
    dataset_dir = replace_source_with_destination(dataset_dir, base_dir)
    run_script = f"cog train -n {str(job_id)} -i dataset={dataset_dir} -i result_id={result_id} -i api_url={api_url} -i pkg_name={name} -i user_token={user_token}"
    if trained_model is not None:
        trained_model = replace_source_with_destination(trained_model, base_dir)
        run_script += f" -i trained_model={trained_model}"
    # Mount the base directory
    run_script += f" --mount type=bind,source={base_dir},target={settings.cog_base_dir}"
    return run_script

def run_process_with_std(run_script: str, stdout_file_path: Path, at: str) -> None:
    """
    Run a process with stderr and stdout.

    This function executes a command-line script in a subprocess, redirecting the standard output (stdout)
    and standard error (stderr) to a specified file. The function also changes the working directory (cwd)
    to the specified path before executing the script.

    Parameters:
    - run_script (str): The command-line script to be executed.
    - stdout_file_path (Path): The path to the file where the stdout and stderr will be redirected.
    - at (str): The path to the directory where the script should be executed.

    Returns:
    None

    Raises:
    - subprocess.CalledProcessError: If the script execution returns a non-zero exit status.
    """
    with stdout_file_path.open("wb") as stdout_file:
        subprocess.run(
            run_script,
            stdout=stdout_file,
            stderr=subprocess.STDOUT,
            cwd=at,
            shell=True,
            executable="/bin/bash",
            check=True
        )

async def setup(
        job_id: uuid.UUID,
        dataset_name: str,
        model_name: str,
        dataset_branch: str | None = None,
        model_branch: str | None = None,
    ) -> bool:
    """
    Setup the environment for the job.

    This function clones the dataset and model repositories to a temporary directory,
    discarding them after use. It also handles any exceptions that may occur during the cloning process.

    Parameters:
    - job_id (uuid.UUID): The unique identifier for the job.
    - dataset_name (str): The name of the dataset repository.
    - model_name (str): The name of the model repository.
    - dataset_branch (str | None, optional): The branch of the dataset repository to clone. Defaults to None.
    - model_branch (str | None, optional): The branch of the model repository to clone. Defaults to None.

    Returns:
    - bool: True if the setup is successful, False otherwise.

    Raises:
    - HTTPException: If an error occurs during the setup process.
    """
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

    return True

async def prepare(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
    dataset_type: str,
    results_dir: str = "",
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> bool:
    """
    Prepare the environment for the job.

    If the dataset type is 'upload', it copies the
    dataset from the results directory to the dataset path. If the dataset type is 'default',
    it fetches the dataset from the specified branch of the dataset repository.
    It also fetches the model from the specified branch of the model repository.

    Parameters:
    - job_id (uuid.UUID): The unique identifier for the job.
    - dataset_name (str): The name of the dataset repository or the path to the dataset
    - model_name (str): The name of the model repository.
    - dataset_type (str): The type of the dataset. It can be either 'upload' or 'default'.
    - results_dir (str, optional): The directory path where the uploaded dataset is located. Defaults to an empty string.
    - dataset_branch (str | None, optional): The branch of the dataset repository to clone. Defaults to None.
    - model_branch (str | None, optional): The branch of the model repository to clone. Defaults to None.

    Returns:
    - bool: True if the preparation is successful, False otherwise.

    Raises:
    - HTTPException: If an error occurs during the preparation process.
    """
    # Clone Dataset to job_results_dir
    git = GitService()
    _, dataset_path, model_path = job_get_dirs(job_id, dataset_name, model_name)

    try:
        # run git
        if dataset_type == 'upload':
            copytree(dataset_name,results_dir)
        elif dataset_type == 'default':
            git.fetch(repo_name_with_namspace=dataset_name, to=dataset_path, branch= dataset_branch)
        git.fetch(repo_name_with_namspace=model_name, to=model_path, branch= model_branch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error Preparing Docker Environment: {str(e)}")

    return True

def stop(job_id: uuid.UUID) -> bool:
    """
    Stop the jobs for container.

    This function stops and removes all Docker containers that have the specified job_id as their ancestor.
    It uses the Docker CLI commands 'docker ps -a -q  --filter ancestor={str(job_id)}' to get the list of container IDs,
    and then iterates over these IDs to stop and remove each container.

    Parameters:
    - job_id (uuid.UUID): The unique identifier for the job.

    Returns:
    - bool: True if all containers are successfully stopped and removed, False otherwise.

    Raises:
    - None

    Note:
    - This function uses the os.system() function to execute Docker CLI commands.
    """
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
    """
    Remove the environment for the job.

    This function removes the dataset and model directories associated with the given job_id.
    It uses the os.system() function to execute the 'rm -rf' command to delete the directories.

    Parameters:
    - job_id (uuid.UUID): The unique identifier for the job.
    - dataset_name (str): The name of the dataset repository.
    - model_name (str): The name of the model repository.

    Returns:
    - bool: True if the directories are successfully removed, False otherwise.

    Note:
    - This function uses the os.system() function to execute the 'rm -rf' command, which can be a security risk.
    - It is recommended to use a safer alternative, such as shutil.rmtree(), for removing directories in production code.
    """
    _, dataset_path, model_path = job_get_dirs(job_id, dataset_name, model_name)
    os.system(f"rm -rf {dataset_path}")  # noqa: F821
    os.system(f"rm -rf {model_path}")
    return True

def remove_docker(job_id: uuid.UUID) -> None:
    """
    Remove docker image which serves as env from machine.

    This function uses the os.system() function to execute the 'docker rmi' command,
    which removes a Docker image from the local machine. The image to be removed is
    identified by its unique job_id.

    Parameters:
    - job_id (uuid.UUID): The unique identifier for the job. This is used to identify the Docker image to be removed.

    Returns:
    - None: This function does not return any value.

    Note:
    - This function uses the os.system() function to execute the 'docker rmi' command, which can be a security risk.
    - It is recommended to use a safer alternative, such as Docker SDK for Python, for interacting with Docker in production code.
    """
    os.system(f"docker rmi {str(job_id)}")

def replace_source_with_destination(at: str, base_dir: str) -> str:
    """
    Replace the source directory with the destination directory.

    This function is used to replace the source directory path with the destination directory path.
    It is used in the context of setting up a cog environment, where the source directory is replaced
    with the destination directory in the command-line script.

    Parameters:
    - at (str): The original source directory path.
    - base_dir (str): The destination directory path.

    Returns:
    str: The updated command-line script with the source directory replaced by the destination directory.

    Note:
    - This function is used in the context of setting up a cog environment.
    - The source directory is replaced with the destination directory in the command-line script.
    """
    return at.replace(base_dir, settings.cog_base_dir)
