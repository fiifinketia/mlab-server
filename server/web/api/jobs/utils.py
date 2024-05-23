"""UTILS FOR JOBS API"""
import datetime
import os
import subprocess
from typing import Any
import uuid
from concurrent.futures import ProcessPoolExecutor
from git import GitCommandError, Repo

from server.db.models.datasets import Dataset
from server.db.models.jobs import Job
from server.db.models.ml_models import Model
from server.db.models.results import Result
import pymlab as pm 
from server.settings import settings

async def train_model(
        dataset: Dataset,
        job: Job,
        model: Model,
        result_name: str,
        parameters: dict[str, Any] = {},
        # layers: list[Layer] = []
) -> Result:
    """Train model with a provided dataset and store results"""
    dataset_repo = Repo(settings.datasets_dir + dataset.path)
    model_repo = Repo(settings.models_dir + model.path)

    # clone dataset and model to a tmp directory and discard after use
    dataset_path = settings.datasets_dir + "/tmp/" + str(job.id) + dataset.path
    model_path = settings.models_dir + "/tmp/" + str(job.id) + model.path
    # clone specific jobb.repo_hash branch
    try:
        Repo.clone_from(dataset_repo.working_dir, dataset_path, branch= job.dataset_branch if job.dataset_branch is not None else "master")
        Repo.clone_from(model_repo.working_dir, model_path, branch= job.model_branch if job.model_branch is not None else "master")
    except GitCommandError as e:
        os.system(f"rm -rf {dataset_path}")
        os.system(f"rm -rf {model_path}")
        try:
            Repo.clone_from(dataset_repo.working_dir, dataset_path, branch= job.dataset_branch if job.dataset_branch is not None else "master")
            Repo.clone_from(model_repo.working_dir, model_path, branch= job.model_branch if job.model_branch is not None else "master")
        except Exception as e:
            os.system(f"rm -rf {dataset_path}")
            os.system(f"rm -rf {model_path}")
            raise e


    # Update the config file
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

    # Create results directory

    result_id = uuid.uuid4()
    os.makedirs(f"{settings.results_dir}/{result_id}")

    # paste config file to results directory also for future reference
    subprocess.run(
        f"cp {model_path}/config.txt {settings.results_dir}/{result_id}/config.txt",
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

    for key, value in old_parameters.items():
        if key == "dataset_url":
            pass
        elif parameters.get(key) is None:
            parameters[key] = value
    
    parameters["dataset_url"] = "dataset.csv"

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
        executor = ProcessPoolExecutor()
        # executor.submit(
        #     run_train_model,
        #     model_path=model_path,
        #     script_path=f"{model_path}/{entry_point}.py",
        #     result_id=result_id,
        #     config_path=f"{model_path}/config.txt",
        # )

        executor.submit(
            pm.run_native_pkg,
            name="pymlab.train",
            at=model_path,
            result_id=result_id,
            api_url=f"{settings.api_url}/results/train",
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
        result.modified = datetime.datetime.now()
        await result.update()
        # clear tmp repos
        os.system(f"rm -rf {dataset_path}")
        os.system(f"rm -rf {model_path}")
    except Exception as e:
        print(e)
    return result

async def test_model(
    dataset: Dataset,
    job: Job,
    model: Model,
    result_name: str,
    parameters: dict[str, Any] = {},
    pretrained_model: str | None = None,
) -> Result:
    """Test model with a provided dataset and store results"""
    # Get the dataset path
    dataset_repo = Repo(settings.datasets_dir + dataset.path)
    model_repo = Repo(settings.models_dir + model.path)


    # clone dataset and model to a tmp directory and discard after use
    dataset_path = settings.datasets_dir + "/tmp/" + str(job.id) + dataset.path
    model_path = settings.models_dir + "/tmp/" + str(job.id) + model.path

    try:
        Repo.clone_from(dataset_repo.working_dir, dataset_path, branch= job.dataset_branch if job.dataset_branch is not None else "master")
        Repo.clone_from(model_repo.working_dir, model_path, branch= job.model_branch if job.model_branch is not None else "master")
    except GitCommandError as e:
        os.system(f"rm -rf {dataset_path}")
        os.system(f"rm -rf {model_path}")
        try:
            Repo.clone_from(dataset_repo.working_dir, dataset_path, branch= job.dataset_branch if job.dataset_branch is not None else "master")
            Repo.clone_from(model_repo.working_dir, model_path, branch= job.model_branch if job.model_branch is not None else "master")
        except Exception as e:
            os.system(f"rm -rf {dataset_path}")
            os.system(f"rm -rf {model_path}")
            raise e


    # Update the config file

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

    # Create results directory

    result_id = uuid.uuid4()
    os.makedirs(f"{settings.results_dir}/{result_id}")

    # paste config file to results directory also for future reference
    subprocess.run(
        f"cp {model_path}/config.txt {settings.results_dir}/{result_id}/config.txt",
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

    for key, value in old_parameters.items():
        if key == "dataset_url":
            pass
        elif parameters.get(key) is None:
            parameters[key] = value
    
    parameters["dataset_url"] = "dataset.csv"

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
            api_url=f"{settings.api_url}/results/test",
            pretrained_model=trained_model
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
        result.modified = datetime.datetime.now()
        await result.update()
        # clear tmp repos
        os.system(f"rm -rf {dataset_path}")
        os.system(f"rm -rf {model_path}")
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

