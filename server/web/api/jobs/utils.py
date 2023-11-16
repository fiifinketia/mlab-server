"""UTILS FOR JOBS API"""
import os
import subprocess
from typing import Any
import uuid
from concurrent.futures import ProcessPoolExecutor

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.settings import settings


async def run_model(
        dataset: Dataset,
        job: Job,
        parameters: dict[str, Any] = {},
        # layers: list[Layer] = []
) -> Result:
    """Train model with a provided dataset and store results"""
    # Get the dataset path
    dataset_path = os.path.join(settings.datasets_dir, dataset.path)
    job_path = os.path.join(settings.jobs_dir, str(job.id))

    # Get the model path using the job model_name
    model = await Model.objects.get(id=job.model_id)
    model_path = os.path.join(settings.models_dir, model.path)
    entry_point = "__train__"

    # Update the config file

    old_parameters = {}
    with open(f"{job_path}/config.txt", "r") as f:
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
                    old_parameters[args[1]] = args[2].strip()

    with open(f"{job_path}/config.txt", "r") as file:
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
        with open(f"{job_path}/config.txt", "w") as file:
            file.write(filedata)

    # Create results directory

    result_id = uuid.uuid4()
    os.makedirs(f"{settings.results_dir}/{result_id}")

    # paste config file to results directory also for future reference
    subprocess.run(
        f"cp {job_path}/config.txt {settings.results_dir}/{result_id}/config.txt",
        shell=True,
        executable="/bin/bash",
        check=True,
    )

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        status="running",
        result_type="train",
    )

    # Run the script
    executor = ProcessPoolExecutor()
    executor.submit(
        run_script_in_venv,
        model_path,
        f"{model_path}/{entry_point}.py",
        result_id,
        f"{job_path}/config.txt",
    )
    # run_script_in_venv(
    #   model_path,
    #   script_path=f"{model_path}/{entry_point}.py",
    #   config_path=f"{job_path}/config.txt",
    #   result_id=result_id,
    # )

    return result


def run_script_in_venv(
    model_path: str,
    script_path: str,
    result_id: uuid.UUID,
    config_path: str,
    create_model_path: str | None = None,
) -> None:
    """Run a script in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{model_path}/venv"
    activate_venv = f"source {venv_path}/bin/activate"

    # Run install requirements
    install_requirements = f"pip install -r {model_path}/requirements.txt"

    # Prepare the command to run the script with arguments
    run_script = f"python {script_path} --config {config_path} --result_id {result_id} --model {create_model_path}"

    # Combine the commands
    command = f"{activate_venv} && {install_requirements} && {run_script}"

    # Run the command
    subprocess.run(command, shell=True, executable="/bin/bash", check=True)
