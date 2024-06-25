"""UTILS FOR JOBS API"""
import datetime
import os
import subprocess
from typing import Any
import uuid
from fastapi import HTTPException

from server.settings import settings
from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
import server.services.cog as cg

from server.web.api.utils import job_get_dirs

async def train_model(
    dataset: Dataset,
    job: Job,
    model: Model,
    result_name: str,
    user_token: str,
    environment_type: str = "docker",
    parameters: dict[str, Any] = {},
    dataset_branch: str | None = None,
    model_branch: str | None = None,
    # layers: list[Layer] = []
) -> Result:
    """Train model with a provided dataset and store results"""
    job_base_dir, dataset_path, model_path = job_get_dirs(job.id, dataset.git_name, model.git_name)
    result_id = uuid.uuid4()
    results_dir = f"{job_base_dir}/{str(result_id)}"
    os.makedirs(results_dir)
    config_path = f"{model_path}/config.train.txt"

    update_config_file(config_path=config_path, parameters=parameters, results_dir=results_dir)

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        dataset_type="default",
        status="running",
        result_type="train",
        owner_id=job.owner_id,
        parameters=parameters,
        name=result_name,
    )

    try:
        match environment_type:
            case "docker":
                try:
                    await cg.prepare(job_id=job.id, dataset_name=dataset.git_name, model_name=model.git_name, dataset_type="default")
                    await cg.run(
                        name="pymlab.train",
                        at=model_path,
                        result_id=result_id,
                        user_token=user_token,
                        api_url=f"{settings.api_url}/results/submit",
                        base_dir=job_base_dir,
                        dataset_dir=dataset_path,
                        job_id=job.id
                    )
                except subprocess.CalledProcessError as e:
                    await handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
            case _:
                raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {environment_type}")
    except subprocess.CalledProcessError as e:
        await handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
    return result

async def test_model(
    dataset_path: str,
    job: Job,
    model: Model,
    result_name: str,
    user_token: str,
    dataset_type: str,
    model_type: str,
    environment_type: str = "docker",
    parameters: dict[str, Any] = {},
    pretrained_model: str | None = None,
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> Result:
    """Test model with a provided dataset and store results"""
    job_base_dir, _, model_path = job_get_dirs(job.id, "", model.git_name)
    result_id = uuid.uuid4()
    results_dir = f"{job_base_dir}/{str(result_id)}"
    os.makedirs(results_dir)
    config_path = f"{model_path}/config.test.txt"

    update_config_file(config_path=config_path, parameters=parameters, results_dir=results_dir)

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=job.dataset_id,
        dataset_type=dataset_type,
        status="running",
        result_type="test",
        owner_id=job.owner_id,
        parameters=parameters,
        name=result_name,
    )

    if dataset_type == 'upload':
        dataset_name = dataset_path
    elif dataset_type == 'default':
        dataset = await Dataset.objects.get(id=job.dataset_id)
        dataset_name = dataset.git_name
    else:
        raise NotImplementedError(f"Dataset type {dataset_type} is not supported")

    # Run the script
    try:
        match environment_type:
            case "docker":
                try:
                    await cg.prepare(
                        job_id=job.id,
                        dataset_type=dataset_type,
                        model_name=model.git_name,
                        dataset_name=dataset_name,
                        results_dir=results_dir,
                    )
                    await cg.run(
                        name="pymlab.test",
                        at=model_path,
                        result_id=result_id,
                        user_token=user_token,
                        trained_model=pretrained_model,
                        api_url=f"{settings.api_url}/results/submit",
                        base_dir=job_base_dir,
                        dataset_dir=dataset_path if dataset_type == "default" else results_dir,
                        job_id=job.id
                    )
                except subprocess.CalledProcessError as e:
                    await handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
            case _:
                raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {environment_type}")
    except subprocess.CalledProcessError as e:
        await handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
    return result

async def setup_environment(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
    environment_type: str = "docker",
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> None:
    """Run environment setup and save the results"""
    is_complete = False
    match environment_type:
        case "docker":
            try:
                is_complete = await cg.setup(job_id, dataset_name, model_name, dataset_branch, model_branch)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {str(e)}") from e
        case _:
            raise HTTPException(status_code=400, detail=f"Error Setting up Environment: {environment_type} is not supported")
    if is_complete:
        job = await Job.objects.get(id=job_id)
        job.ready = True
        job.modified = datetime.datetime.now()
        await job.update()



def update_config_file(
    config_path: str,
    parameters: dict[str, Any],
    results_dir: str,
) -> None:
    """Update the config file with new parameters"""
    old_parameters = {}
    with open(config_path, "r") as f:
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

    with open(config_path, "r") as file:
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

        # Save the updated config file
        with open(config_path, "w") as file:
            file.write(filedata)
    # copy new parameters to results directory
    results_config_path = f"{results_dir}/{config_path.split('/')[-1]}"
    subprocess.run(["cp", config_path, results_config_path])

def stop_job_processes(job_id: uuid.UUID, environment_type: str = "docker") -> None:
    """Stop jobs"""
    match environment_type:
        case "docker":
            cg.stop(job_id=job_id)
        case _:
            raise HTTPException(status_code=400, detail=f"Error stoping jobs for Environment: {environment_type}")


def remove_job_env(job_id: uuid.UUID, dataset_name: str, model_name: str, environment_type: str = "docker") -> None:
    """Close a job"""
    # Delete the dataset and model directories
    match environment_type:
        case "docker":
            cg.remove(job_id=job_id, dataset_name=dataset_name, model_name=model_name)
            cg.remove_docker(job_id=job_id)
        case _:
            raise HTTPException(status_code=400, detail=f"Error removing Environment: {environment_type}")

async def handle_error(
    results_dir: str,
    e: Any,
    result: Result,
    job: Job,
) -> None:
    if isinstance(e, subprocess.CalledProcessError):
        await handle_subprocess_error(results_dir, e, result, job)
    else:
        await handle_subprocess_error(results_dir, e, result, job)

async def handle_subprocess_error(
    results_dir: str,
    e: subprocess.CalledProcessError,
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
    if not os.path.exists(f"{results_dir}/error.txt"):
        with open(f"{results_dir}/error.txt", "w", encoding="utf-8") as f:
            f.write(error_message)
    else:
        with open(f"{results_dir}/error.txt", "a", encoding="utf-8") as f:
            f.write(error_message)
    # Update the result status
    result.status = "error"
    result.modified = datetime.datetime.now()
    job.ready = True
    job.modified = datetime.datetime.now()
    await result.update()
    await job.update()
