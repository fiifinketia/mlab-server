"""UTILS FOR JOBS API"""
import datetime
import os
import subprocess
from typing import Any
import uuid
from concurrent.futures import ProcessPoolExecutor
from fastapi import HTTPException
import pymlab as pm

from server.settings import settings
from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.services.git import GitService
from server.web.api.utils import job_get_dirs

async def train_model(
        dataset: Dataset,
        job: Job,
        model: Model,
        result_name: str,
        user_token: str,
        parameters: dict[str, Any] = {},
        dataset_branch: str | None = None,
        model_branch: str | None = None,
        # layers: list[Layer] = []
) -> Result:
    """Train model with a provided dataset and store results"""
    job_base_dir, dataset_path, model_path = job_get_dirs(job.id, dataset.git_name, model.git_name)

    # Update the config file
    old_parameters = update_config_file(model_path=model_path, parameters=parameters, dataset_path=dataset_path)

    # Create results directory
    result_id = uuid.uuid4()
    result_dir = f"{job_base_dir}/{str(result_id)}"
    os.makedirs(result_dir)

    files = write_result_config_file(model_path=model_path, dataset_path=dataset_path, result_dir=result_dir, parameters=parameters, old_parameters=old_parameters)


    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        status="running",
        result_type="train",
        owner_id=job.owner_id,
        files=files,
        parameters=parameters,
        name=result_name,
    )

    try:
        install_output = run_install_requirements(model_path)
        if install_output.returncode != 0:
            raise subprocess.CalledProcessError(
                install_output.returncode,
                install_output.args,
                "Error running script",
                install_output.stderr,
            )
        # Run the script
        executor = ProcessPoolExecutor()

        executor.submit(
            pm.run_native_pkg,
            name="pymlab.train",
            at=model_path,
            result_id=result_id,
            api_url=f"{settings.api_url}/results/submit",
            user_token=user_token,
        )
    except subprocess.CalledProcessError as e:
        await handle_subprocess_error(result_dir=result_dir, e=e, files=files, result=result, job=job)
    return result

async def test_model(
    dataset: Dataset,
    job: Job,
    model: Model,
    result_name: str,
    user_token: str,
    parameters: dict[str, Any] = {},
    pretrained_model: str | None = None,
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> Result:
    """Test model with a provided dataset and store results"""

    # Update the config file
    job_base_dir, dataset_path, model_path = job_get_dirs(job.id, dataset.git_name, model.git_name)

    old_parameters = update_config_file(model_path=model_path, parameters=parameters, dataset_path=dataset_path)

    # Create results directory
    result_id = uuid.uuid4()
    result_dir = f"{job_base_dir}/{str(result_id)}"
    os.makedirs(result_dir)

    files = write_result_config_file(model_path=model_path, dataset_path=dataset_path, result_dir=result_dir, parameters=parameters, old_parameters=old_parameters)

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        status="running",
        result_type="test",
        owner_id=job.owner_id,
        files=files,
        parameters=parameters,
        name=result_name,
    )

    # Run the script

    try:
        install_output = run_install_requirements(model_path)
        if install_output.returncode != 0:
            raise subprocess.CalledProcessError(
                install_output.returncode,
                install_output.args,
                "Error running script",
                install_output.stderr,
            )
        # Run the script
        trained_model = pretrained_model if pretrained_model is not None else f"{model_path}/{model.default_model}"

        executor = ProcessPoolExecutor()

        executor.submit(
            pm.run_native_pkg,
            name="pymlab.test",
            at=model_path,
            result_id=result_id,
            api_url=f"{settings.api_url}/results/submit",
            pretrained_model=trained_model,
            user_token=user_token,
        )
    except subprocess.CalledProcessError as e:
        await handle_subprocess_error(result_dir=result_dir, e=e, files=files, result=result, job=job)
    return result


def run_install_requirements(
    model_path: str
) -> subprocess.CompletedProcess[bytes]:
    """Install requirements in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{model_path}/venv"
    if not os.path.exists(venv_path):
        subprocess.run(f"python3 -m venv {venv_path}", shell=True, executable="/bin/bash", check=True)
    activate_venv = f"source {venv_path}/bin/activate"

    # Run install requirements
    install_requirements = f"pip install -r {model_path}/requirements.txt"

    # Combine the commands
    command = f"{activate_venv} && {install_requirements}"

    # Run the command
    return subprocess.run(command, shell=True, executable="/bin/bash", check=True)

async def setup_environment(
        job_id: uuid.UUID,
        dataset_name: str,
        model_name: str,
        dataset_branch: str | None = None,
        model_branch: str | None = None,
    ) -> bool:
    # Clone Dataset to job_results_dir
    git = GitService()

    # clone dataset and model to a tmp directory and discard after use
    job_base_dir, dataset_path, model_path = job_get_dirs(job_id, dataset_name, model_name)
    # clone specific jobb.repo_hash branch
    try:
        git.clone_repo(repo_name_with_namspace=dataset_name, to=dataset_path, branch= dataset_branch)
        git.clone_repo(repo_name_with_namspace=model_name, to=model_path, branch= model_branch)
        run_install_requirements(model_path)
    except Exception as e:
        os.system(f"rm -rf {dataset_path}")
        os.system(f"rm -rf {model_path}")
        raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {str(e)}")

    return True

async def run_env_setup_and_save(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> None:
    """Run environment setup and save the results"""
    try:
        is_complete = await setup_environment(job_id, dataset_name, model_name, dataset_branch, model_branch)
        if is_complete:
            job = await Job.objects.get(id=job_id)
            job.ready = True
            job.modified = datetime.datetime.now()
            await job.update()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {str(e)}")


def update_config_file(
    model_path: str,
    parameters: dict[str, Any],
    dataset_path: str,
) -> dict[str, Any]:
    """Update the config file with new parameters"""
    old_parameters = {}
    with open(f"{model_path}/config.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            if line[0] == ";":
                continue
            else:
                # Split the line by space
                # if first element is PARAM,
                # then store the second element as key and third element as value
                args = line.split(" ")
                if args[0] == "PARAM":
                    old_parameters[args[1]] = args[3].strip()

    with open(f"{model_path}/config.txt", "r") as file:
        filedata = file.read()
        # Replace the entire PARAM dataset_url line with the new dataset path,
        # the dataset path in the config is un
        for key, value in parameters.items():
            # get the type if float, int, str, bool
            param_type = type(value).__name__
            filedata = filedata.replace(
                f"PARAM {key} {param_type} {old_parameters[key]}",
                f"PARAM {key} {param_type} {value}",
            )
        filedata = filedata.replace(
            f"PARAM dataset_url str {old_parameters['dataset_url']}",
            f"PARAM dataset_url str {dataset_path}",
        )

        # Save the updated config file
        with open(f"{model_path}/config.txt", "w") as file:
            file.write(filedata)
    return old_parameters

def write_result_config_file(
    model_path: str,
    dataset_path: str,
    result_dir: str,
    old_parameters: dict[str, Any],
    parameters: dict[str, Any],
) -> list[str]:
    """Write the config file for the results directory"""
        # paste config file to results directory also for future reference
    subprocess.run(
        f"cp {model_path}/config.txt {result_dir}/config.txt",
        shell=True,
        executable="/bin/bash",
        check=True,
    )

    # edit config.txt file in results directory and remove the dataset_url line
    with open(f"{result_dir}/config.txt", "r") as file:
        filedata = file.read()
        filedata = filedata.replace(
            f"PARAM dataset_url str {dataset_path}",
            "",
        )

        # Save the updated config file
        with open(f"{result_dir}/config.txt", "w") as file:
            file.write(filedata)

    files = []

    files.append("config.txt")

    for key, value in old_parameters.items():
        if key == "dataset_url":
            pass
        elif parameters.get(key) is None:
            parameters[key] = value

    parameters["dataset_url"] = "dataset.csv"
    return files

async def handle_subprocess_error(
    result_dir: str,
    e: subprocess.CalledProcessError,
    files: list[str],
    result: Result,
    job: Job,
) -> None:
    """Handle subprocess errors"""
    print(e)
    error_message = ""
    if e.stderr is not None:
        error_message = e.output.decode("utf-8") + "\n" + e.stderr.decode("utf-8")
    else:
        error_message = str(e)
    # Append error in error.txt file
    # First check if error.txt file exists
    if not os.path.exists(f"{result_dir}/error.txt"):
        with open(f"{result_dir}/error.txt", "w", encoding="utf-8") as f:
            f.write(error_message)
    else:
        with open(f"{result_dir}/error.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
    # Update the result status
    files.append("error.txt")
    result.files = files
    result.status = "error"
    result.modified = datetime.datetime.now()
    job.ready = True
    job.modified = datetime.datetime.now()
    await result.update()
    await job.update()

def remove_job_env(job_id: uuid.UUID, dataset_name: str, model_name: str) -> None:
    """Close a job"""
    # Delete the dataset and model directories
    job_base_dir, model_path, dataset_path = job_get_dirs(job_id, dataset_name, model_name)
    os.system(f"rm -rf {model_path}")
    os.system(f"rm -rf {dataset_path}")
