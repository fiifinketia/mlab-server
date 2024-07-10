"""UTILS FOR JOBS API"""
import asyncio
from concurrent.futures import ProcessPoolExecutor, process
import datetime
import logging
import os
from pathlib import Path
import subprocess
from typing import Any
import uuid
import aiofiles
from fastapi import HTTPException, UploadFile

from mlab_pyprotos import runner_pb2
from server.services.balancer.balancer import LoadBalancer
from server.settings import settings
from server.db.models.datasets import Dataset
from server.db.models.jobs import Job, JobStatus
from server.db.models.ml_models import Model
from server.db.models.results import Result

from server.web.api.jobs.dto import JobIn, ModelType, TestModelIn, TrainModelIn
from server.web.api.utils import ErrorContext, job_get_dirs

CHUNK_SIZE = 1024 * 1024


async def get_jobs(user_id: str | None) -> list[Job]:
    if user_id is None:
        return await Job.objects.select_related("results").all()
    # Add results related to job
    return await Job.objects.select_related("results").all(owner_id=user_id, closed=False)

async def create_job(user_id: str, job_in: JobIn) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Creating job %s", user_id)
    job_id = uuid.uuid4()
    logger.info("Job id: %s", job_id)
    try:
        logger.info(f"Finding public model with id: %s" % job_in.model_id)
        model = await Model.objects.get(id=job_in.model_id, private=False)
        logger.info(f"Model with id: {model.id}")
        logger.info(f"Finding pubblic dataset with id: {job_in.dataset_id}")
        dataset = await Dataset.objects.get(id=job_in.dataset_id, private=False)
        logger.info(f"Dataset with id: {dataset.id}")
        if model is None and user_id is not None:
            logger.info(f"No Public Model, checking user models: {user_id}")
            model = await Model.objects.get(id=job_in.model_id, private=True, owner_id=user_id)
            logger.info(f"User model found: {user_id}")
        if model is None:
            logger.info(f"No model found")
            raise HTTPException(status_code=404, detail=f"Model {job_in.model_id} not found")
        if dataset is None and user_id is not None:
            logger.info(f"No Public Dataset, checking user datasets: {user_id}")
            dataset = await Dataset.objects.get(id=job_in.dataset_id, private=True, owner_id=user_id)
            logger.info(f"User dataset found: {user_id}")
        if dataset is None:
            logger.info(f"No dataset found")
            raise HTTPException(status_code=404, detail=f"Dataset {job_in.dataset_id} not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500) from e
    parameters = job_in.parameters
    if parameters is None:
        parameters = model.parameters
    else:
        parameters = {**model.parameters, **parameters}

    await Job.objects.create(
        id=job_id,
        name=job_in.name,
        description=job_in.description,
        owner_id=user_id,
        model_id=job_in.model_id,
        dataset_id=job_in.dataset_id,
        model_name=model.name,
        parameters=parameters,
    )
    # Setup Enviroment for job
    asyncio.create_task(
        _setup_environment(
            job_id=job_id,
            model_name=model.git_name,
            dataset_name=dataset.git_name,
        )
    )

async def stop_job(user_id: str, job_id: uuid.UUID) -> None:
    job = await Job.objects.get(id=job_id)
    if job.owner_id!= user_id:
        raise HTTPException(status_code=403, detail=f"User does not have permission to stop job {job_id}")
    try:
        _stop_job_processes(job_id)
        job.status = JobStatus.READY
        job.modified = datetime.datetime.now()
        await job.update()
        # update jobb results with status running
        job_results_running = await Result.objects.filter(job=job, status="running").all()
        for result in job_results_running:
            result.status = "stopped"
            result.modified = datetime.datetime.now()
            await result.update()
    except:
        HTTPException(status_code=400, detail=f"Failed to stop job {job_id}")

async def close_job(user_id: str, job_id: uuid.UUID) -> None:
    job = await Job.objects.get(id=job_id)
    if job.owner_id != user_id:
        raise HTTPException(status_code=403, detail=f"User does not have permission to close job {job_id}")
    if job.status != JobStatus.READY:
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not ready, might still be running")
    # Close job
    dataset = await Dataset.objects.get(id=job.dataset_id)
    model = await Model.objects.get(id=job.model_id)
    if job.status == JobStatus.OCCUPIED:
        raise HTTPException(status_code=400, detail=f"Job {job_id} has running processes, please stop them first")
    try:
        await _remove_job_env(job_id=job_id, dataset_name=dataset.git_name, model_name=model.git_name)
    except:
        HTTPException(status_code=400, detail=f"Failed to remove job environment")
    job.status = JobStatus.CLOSED
    job.modified = datetime.datetime.now()
    await job.update()

async def train(user_id: str, train_model_in: TrainModelIn) -> Any:
    job = await Job.objects.get(id=train_model_in.job_id, owner_id=user_id)
    if job.status != JobStatus.READY:
        raise HTTPException(status_code=400, detail=f"Job {train_model_in.job_id} is not ready")
    job = await Job.objects.get(id=train_model_in.job_id)
    dataset = await Dataset.objects.get(id=job.dataset_id, private=False)
    model = await Model.objects.get(id=job.model_id)
    loop = asyncio.get_event_loop()
    loop.create_task(
        _train_model(
            dataset=dataset,
            job=job,
            model=model,
            result_name=train_model_in.name,
            parameters=train_model_in.parameters,
            model_branch=train_model_in.model_branch,
            dataset_branch=train_model_in.dataset_branch,
        )
    )
    job.status = JobStatus.OCCUPIED
    job.modified = datetime.datetime.now()
    await job.update()
    return job.status

async def test(user_id: str, test_model_in: TestModelIn) -> Any:
    job = await Job.objects.get(id=test_model_in.job_id, owner_id=user_id)
    if job.status != JobStatus.READY:
        raise HTTPException(status_code=400, detail=f"Job {test_model_in.job_id} is not ready")
    job = await Job.objects.get(id=test_model_in.job_id)

    if test_model_in.dataset.path is None:
        dataset = await Dataset.objects.get(id=job.dataset_id, private=False)
        if dataset is None and user_id is not None:
            dataset = await Dataset.objects.get(id=job.dataset_id, private=True, owner_id=user_id)
            if dataset is None:
                raise HTTPException(status_code=404, detail=f"Dataset {job.dataset_id} not found")
        _,dataset_path,_ = job_get_dirs(job_id=job.id, dataset_name=dataset.git_name, model_name="")
    else:
        test_dataset_parent = Path(test_model_in.dataset.path).parent.__str__()
        _,dataset_path,_ = job_get_dirs(job_id=job.id, dataset_name=test_dataset_parent, model_name="")
        dataset_path = Path(f"{dataset_path}/{test_model_in.dataset.path.split('/')[-1]}").__str__()
    model = await Model.objects.get(id=job.model_id, private=False)
    if model is None and user_id is not None:
        model = await Model.objects.get(id=job.model_id, private=True, owner_id=user_id)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Model {job.model_id} not found")

    match test_model_in.model.type:
        case ModelType.default:
            _,_,model_path = job_get_dirs(job_id=job.id, dataset_name="", model_name=model.git_name)
            pretrained_model_path = f"{model_path}/{model.default_model}"
        case ModelType.pretrained:
            result_id = uuid.UUID(test_model_in.model.result_id)
            train_result = await Result.objects.get(id=result_id)
            job_base_dir,_,_ = job_get_dirs(job_id=job.id, dataset_name="", model_name="")
            pretrained_model_path = f"{job_base_dir}/{str(train_result.id)}/{train_result.pretrained_model}"
        case ModelType.custom:
            # model = await Model.objects.get(id=job.model_id)
            # pretrained_model_path = settings.results_dir + "/" + model.path
            raise HTTPException(status_code=400, detail="Custom model not supported yet")
    loop = asyncio.get_event_loop()
    loop.create_task(
        _test_model(
        dataset_path=dataset_path,
        job=job,
        model=model,
        result_name=test_model_in.name,
        parameters=test_model_in.parameters,
        pretrained_model=pretrained_model_path,
        dataset_branch=test_model_in.dataset.branch,
        model_branch=test_model_in.model.branch,
        dataset_type=test_model_in.dataset.type,
        model_type=test_model_in.model.type,
    ))
    job.status = JobStatus.OCCUPIED
    job.modified = datetime.datetime.now()
    await job.update()
    return "Testing model"

async def upload_file(file: UploadFile, job_id: uuid.UUID) -> str:
    dataset_id = uuid.uuid4()
    filename = file.filename
    if filename is None:
        raise HTTPException(status_code=400, detail="No file provided")
    _, dataset_dir, _ = job_get_dirs(job_id=job_id, dataset_name=str(dataset_id), model_name="")
    filepath = Path(f"{dataset_dir}/{filename}")
    try:
        async with aiofiles.open(filepath, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                await buffer.write(chunk)
    # Catch any errors and delete the file
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await file.close()
    return str(Path(f"{str(dataset_id)}/{filename}"))
def _stop_job_processes(job_id: uuid.UUID) -> None:
    try:
        balancer = LoadBalancer()
        runner = balancer.get_available_runner()
        request = runner.StopTaskRequest(job_id=job_id)
        client = runner.client()
        client.stop_task(request)
    except Exception as e:
        context = ErrorContext(
            func=_stop_job_processes,
            args=[job_id]
        )
        _handle_job_stop_error(context, e)


async def _remove_job_env(job_id: uuid.UUID) -> None:
    try:
        balancer = LoadBalancer()
        runner = balancer.get_available_runner()
        request = runner_pb2.RemoveTaskRequest(job_id=job_id)
        client = runner.client()
        client.remove_task_environment(request)
    except Exception as e:
        context = ErrorContext(
            func=_remove_job_env,
            args=[job_id]
        )
        _handle_job_remove_error(context, e)

async def _setup_environment(
    job_id: uuid.UUID,
    dataset_name: str,
    model_name: str,
    environment_type: str = "docker",
    dataset_branch: str | None = None,
    model_branch: str | None = None,
) -> None:
    """Run environment setup and save the results"""
    try:
        balancer = LoadBalancer()
        runner = balancer.get_available_runner()
        model = runner_pb2.Project(
            name = model_name,
            branch=model_branch,
        )
        dataset = runner_pb2.Project(
            name=dataset_name,
            branch=dataset_branch,
        )
        create_task_request = runner_pb2.CreateTaskRequest(job_id=str(job_id), dataset=dataset, model=model)
        client = runner.client()
        client.create_task_environment(create_task_request)
        job = await Job.objects.get(id=job_id)
        job.status = JobStatus.READY
        job.modified = datetime.datetime.now()
        job.runner_id = runner.id
        await job.update()
    except Exception as e:
        # Handle error and log it
        context = ErrorContext(
            func=_setup_environment,
            args=[
                job_id,
                dataset_name,
                model_name,
                environment_type,
                dataset_branch,
                model_branch,
            ]
        )
        await _handle_job_create_error(context, e)

async def _train_model(
    dataset: Dataset,
    job: Job,
    model: Model,
    result_name: str,
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
        balancer = LoadBalancer()
        runner = balancer.find4_job(runner_id=job.runner_id, job_id=str(job.id))
        request_model = runner_pb2.Project(
            name = model.git_name,
            path=model_path,
        )
        request_dataset = runner_pb2.Project(
            name=dataset.git_name,
            path=dataset_path,
            type="default",
        )

        request = runner_pb2.RunTaskRequest(
            job_id=str(job.id),
            task_id=str(result_id),
            task_name="pymlab.train",
            user_id=job.owner_id,
            results_dir=results_dir,
            base_dir=job_base_dir,
            rpc_url=settings.rpc_url,
            model=request_model,
            dataset=request_dataset
        )
        client = runner.client()
        await _run_task(client, request, job.id, result_id)

    except subprocess.CalledProcessError as e:
        await _handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
    except Exception as e:
        context = ErrorContext(
            func=_train_model,
            args=[
                job,
                dataset,
                model,
                result_name,
                environment_type,
                parameters,
                dataset_branch,
                model_branch
            ]
        )
        await _handle_run_error(context, e)
    return result

async def _test_model(
    dataset_path: str,
    job: Job,
    model: Model,
    result_name: str,
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
        balancer = LoadBalancer()
        runner = balancer.find4_job(runner_id=job.runner_id, job_id=job.job_id)
        client = runner.client()

        request_model = runner_pb2.Project(
            name = model.git_name,
            path=model_path,
        )
        request_dataset = runner_pb2.Project(
            name=dataset_name,
            path=dataset_path if dataset_type == "default" else str(Path(f"{results_dir}/{dataset_path.split('/')[-1]}")),
            type=dataset_type,
        )

        request = runner_pb2.RunTaskRequest(
            job_id=job.id,
            task_id=result_id,
            task_name="pymlab.test",
            user_id=job.owner_id,
            results_dir=results_dir,
            base_dir=job_base_dir,
            rpc_url=settings.rpc_url,
            model=request_model,
            trained_model=pretrained_model,
            dataset=request_dataset
        )

        await _run_task(client, request, job.id, result_id)
    except subprocess.CalledProcessError as e:
        await _handle_subprocess_error(results_dir=results_dir, e=e, result=result, job=job)
    except Exception as e:
        context = ErrorContext(
            func=_test_model,
            args=[
                job,
                dataset_path,
                model,
                result_name,
                dataset_type,
                model_type,
                environment_type,
                parameters,
                pretrained_model,
                dataset_branch,
                model_branch]
        )
        await _handle_run_error(context, e)
    return result

async def _run_task(client: Any, request: Any, job_id: uuid.UUID, result_id: uuid.UUID) -> None:
    responses = client.run_task(request)
    def is_not_empty(response: Any) -> bool:
        return len(response.task_id) != 0
    for response in responses:
        if response.line:
            _save_file(job_id=job_id, file_name="stdout.log", content=response.line, result_id=result_id, mode="append")
        if is_not_empty(response.result):
            await _submit_result(response.result, job_id, result_id)

def _save_file(job_id: uuid.UUID, result_id: uuid.UUID, file_name: str, content: bytes, mode: str = "") -> None:
    """Save file to the job directory"""
    jobs_base_dir, _, _ = job_get_dirs(job_id, "", "")
    file_path = Path(f"{jobs_base_dir}/{str(result_id)}/{file_name}")
    if mode == "append":
        with open(file_path, "a") as file:
            file.write(content.decode())
            file.close()
    else:
        with open(file_path, "wb") as file:
            file.write(content)
            file.close()

async def _submit_result(task_result: Any, job_id: uuid.UUID, result_id: uuid.UUID) -> Result:
    # TODO: Implement submission of results to the database and analytics system
    result = await Result.objects.get(id=result_id)
    result.status = task_result.status
    metrics = {}
    for metric in task_result.metrics:
        # metrics.append((metric.name, metric.metric))
        metrics[metric.name] = metric.metric
    result.metrics = metrics
    if task_result.pkg_name == "pymlab.train":
        result.pretrained_model = task_result.pretrained_model
    for file in task_result.files:
        _save_file(job_id=job_id, file_name=file.info.name, content=file.buffer, result_id=result_id)
    result.modified = datetime.datetime.now()
    await result.update()
    result.job.status = JobStatus.READY
    result.job.modified = datetime.datetime.now()
    await result.job.update()
    return result

# Errors
async def _handle_job_create_error(context: ErrorContext, e: Exception) -> None:
    logging.error(e)
    if str(e).count("failed to connect"):
        balancer = LoadBalancer()
        await balancer.add2_retry_queue(context)
    elif isinstance(e, Exception):
        if e.args[0] == "No available runner":
            balancer = LoadBalancer()
            await balancer.add2_retry_queue(context)
    return


async def _handle_subprocess_error(
    results_dir: str,
    e: subprocess.CalledProcessError,
    result: Result,
    job: Job,
) -> None:
    """Handle subprocess errors"""
    logger = logging.getLogger(__name__)
    logger.error(e)
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
    job.status = JobStatus.READY
    job.modified = datetime.datetime.now()
    await result.update()
    await job.update()


async def _handle_run_error(context: ErrorContext, e: Any) -> None:
    logger = logging.getLogger(__name__)
    print(e)
    logger.error(f"An error occurred in {context.func.__name__}: {str(e)}")
    if str(e).count("failed to connect"):
        balancer = LoadBalancer()
        await balancer.add2_retry_queue(context)
    elif str(e).count("No available runner"):
        logger.error(f"No available runner: {context.args[0].id}")
        balancer = LoadBalancer()
        await balancer.add2_retry_queue(context)
        job = context.args[0]
        job.status = JobStatus.INITIALIZING
        job.modified = datetime.datetime.now()
        await job.update()
    elif str(e).count("Runner not available"):
        logger.error(f"Runner not available: {context.args[0].id}")
        balancer = LoadBalancer()
        await balancer.add2_retry_queue(context)
        job = context.args[0]
        job.status = JobStatus.INITIALIZING
        job.modified = datetime.datetime.now()
        await job.update()
    return

def _handle_job_stop_error(context: ErrorContext, e: Any):
    logger = logging.getLogger(__name__)
    print(e)
    logger.error(f"An error occurred in {context.func.__name__}: {str(e)}")

def _handle_job_remove_error(context: ErrorContext, e: Any):
    logger = logging.getLogger(__name__)
    print(e)
    logger.error(f"An error occurred in {context.func.__name__}: {str(e)}")
