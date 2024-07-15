"""
This module implements a load balancer algorithm.
This alogirthm will be used to decide test or train request to be handled.
It will check which of the runners are available based on user requriements.
If requested resource is not available it will add it to the queue.
This queue will be a redis cache of the request details to be processed later.
"""

import os
import json
import logging
from typing import Any, List, Dict, Union
from grpc import ChannelConnectivity
import grpc.aio as grpc
from grpc import RpcError
# from grpc.aio import grpc
from server.services.balancer.runner import Runner
from server.settings import settings
from mlab_pyprotos import runner_pb2_grpc, runner_pb2
from server.services.balancer.queue import QueueManager
from server.web.api.utils import ErrorContext


class LoadBalancer:
    def __init__(self) -> None:
        self.queue_manager = QueueManager()
        # load list from json file
        self.runners_list = self.load_runners_list()
        self.queue_name = "load_balancer_queue"
        self.retry_queue = "retry_queue"
        self._logger = logging.getLogger(__name__)

    @staticmethod
    def load_runners_list() -> List[Dict[str, Union[str, int]]]:
        """Load list of runners from json file."""
        with open(settings.runners_list_path, "r") as file:
            runners_list = json.load(file)
        return runners_list

    def get_runners(self) -> List[Runner]:
        runners = []
        for runner in self.runners_list:
            # get the address of the runner and send gRPC request to get its status
            url = f"{runner.get('base_url')}:{runner.get('rpc_port')}"
            runner_id = runner.get("id")
            if url is None:
                continue
            try:
                c_runner = Runner(id=str(runner_id), url=url)
                runners.append(c_runner)
            except RpcError as e:
                self._logger.error(f"Error connecting to runner at {url}: {e}")
        return runners

    def get_available_runner(self) -> Runner:
        try:
            runners = self.get_runners()
            available_runners = [runner for runner in runners if runner.status() == "available"]
            if available_runners:
                return available_runners[0]
            else:
                raise Exception("No available runner")
        except Exception as e:
            self._logger.info(f"Error finding available runner: {e}")
            raise e

    def find(self, runner_id):
        for runner in self.runners_list:
            if runner["id"] == runner_id:
                url = f"{runner.get('base_url')}:{runner.get('rpc_port')}"
                return Runner(id=runner["id"], url=url)
            else:
                continue
        return None

    def find4_job(self, runner_id: str, job_id: str):
        runner = self.find(runner_id)
        if runner is None:
            self._logger.debug(f"No runner found for job: {job_id}")
            raise Exception("No runner found for this job")
        if runner.status() != "available":
            self._logger.debug(f"Runner: {runner_id} status is not available")
            raise Exception("Runner status is not available")
        return runner

    async def add2_retry_queue(self, context: ErrorContext) -> None:
        """Add context to retry queue."""
        await self.queue_manager.add(self.retry_queue, context.get_bytes())
