"""UTILS FOR JOBS API"""
import os
import subprocess
import uuid
from concurrent.futures import ProcessPoolExecutor

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
from server.settings import settings


async def run_model(dataset: Dataset, job: Job) -> Result:
    """Train model with a provided dataset and store results"""
    # Get the dataset path
    dataset_path = os.path.join(settings.datasets_dir, dataset.path)
    job_path = os.path.join(settings.jobs_dir, str(job.id))

    # Get the model path using the job model_name
    model = await Model.objects.get(unique_name=job.model_name)
    model_path = os.path.join(settings.models_dir, model.path)
    entry_point = ""
    if model.entry_point:
        entry_point = model.entry_point
    else:
        entry_point = "train"

    parameters = {}
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
                    parameters[args[1]] = args[2].strip()

    with open(f"{job_path}/config.txt", "r") as file:
        filedata = file.read()
        # Replace the entire PARAM dataset_url line with the new dataset path,
        # the dataset path in the config is un
        filedata = filedata.replace(
            f"PARAM dataset_url {parameters['dataset_url']}",
            f"PARAM dataset_url {dataset_path}",
        )
        # Save the updated config file
        with open(f"{job_path}/config.txt", "w") as file:
            file.write(filedata)

    # Create results directory

    result_id = uuid.uuid4()
    os.makedirs(f"{settings.results_dir}/{result_id}")

    result = await Result.objects.create(
        id=result_id,
        job=job,
        dataset_id=dataset.id,
        status="running",
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
) -> None:
    """Run a script in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{model_path}/venv"
    activate_venv = f"source {venv_path}/bin/activate"

    # Run install requirements
    install_requirements = f"pip install -r {model_path}/requirements.txt"

    # Prepare the command to run the script with arguments
    run_script = f"python {script_path} {config_path} {result_id}"

    # Combine the commands
    command = f"{activate_venv} && {install_requirements} && {run_script}"

    # Run the command
    subprocess.run(command, shell=True, executable="/bin/bash", check=True)
