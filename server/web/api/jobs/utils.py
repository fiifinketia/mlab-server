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
    dataset_path = settings.datasets_dir + dataset.path
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
                    old_parameters[args[1]] = args[3].strip()

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

    # edit config.txt file in results directory and remove the dataset_url line
    with open(f"{settings.results_dir}/{result_id}/config.txt", "r") as file:
        filedata = file.read()
        filedata = filedata.replace(
            f"PARAM dataset_url str {dataset_path}",
            "",
        )

        # Save the updated config file
        with open(f"{settings.results_dir}/{result_id}/config.txt", "w") as file:
            file.write(filedata)

    files = []

    files.append("config.txt")

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        status="running",
        result_type="train",
        owner_id=job.owner_id,
        files=files,
    )

    # Run the script
    executor = ProcessPoolExecutor()

    try:
        install_output = executor.submit(
            run_install_requirements,
            model_path,
        )
        if install_output.result().returncode != 0:
            raise subprocess.CalledProcessError(
                install_output.result().returncode,
                install_output.result().args,
                "Error running script",
                install_output.result().stderr,
            )
        # Run the script
        executor.submit(
            run_train_model,
            model_path,
            f"{model_path}/{entry_point}.py",
            result_id,
            f"{settings.jobs_dir}/{result_id}/config.txt",
        )
    except subprocess.CalledProcessError as e:
        error_message = ""
        if e.stderr is not None:
            error_message = e.output.decode("utf-8") + "\n" + e.stderr.decode("utf-8")
        else:
            error_message = str(e)
        # Append error in error.txt file
        # First check if error.txt file exists
        if not os.path.exists(f"{settings.results_dir}/{result_id}/error.txt"):
            with open(f"{settings.results_dir}/{result_id}/error.txt", "w", encoding="utf-8") as f:
                f.write(error_message)
        else:
            with open(f"{settings.results_dir}/{result_id}/error.txt", "a", encoding="utf-8") as f:
                f.write(error_message)
        # Update the result status
        files.append("error.txt")
        result.files = files
        result.status = "error"
        await result.update()
    return result
            

def run_install_requirements(
    model_path: str,
) -> subprocess.CompletedProcess[bytes]:
    """Install requirements in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{model_path}/venv"
    activate_venv = f"source {venv_path}/bin/activate"

    # Run install requirements
    install_requirements = f"pip install -r {model_path}/requirements.txt"

    # Combine the commands
    command = f"{activate_venv} && {install_requirements}"

    # Run the command
    return subprocess.run(command, shell=True, executable="/bin/bash", check=True)

def run_train_model(
    model_path: str,
    script_path: str,
    result_id: uuid.UUID,
    config_path: str,
) -> subprocess.CompletedProcess[bytes]:
    """Run a script in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{model_path}/venv"
    activate_venv = f"source {venv_path}/bin/activate"

    # Prepare the command to run the script with arguments
    run_script = f"python {script_path} --config {config_path} --result_id {result_id}"

    # Combine the commands
    command = f"{activate_venv} && {run_script}"

    # Run the command
    return subprocess.run(command, shell=True, executable="/bin/bash", check=True)
