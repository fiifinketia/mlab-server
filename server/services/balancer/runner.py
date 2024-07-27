

import grpc
from mlab_pyprotos import runner_pb2_grpc, runner_pb2


class Runner:
    def __init__(self, id: str, url: str,):
        self.url = url
        self.id = id
        self.options = [('grpc.max_send_message_length', 1024 * 1024 * 1024), ('grpc.max_receive_message_length', 1024 * 1024 * 1024)]

    def client(self) -> runner_pb2_grpc.RunnerStub:

        channel = grpc.insecure_channel(self.url, options=self.options)
        stub = runner_pb2_grpc.RunnerStub(channel)
        return stub

    def client_aio(self) -> runner_pb2_grpc.RunnerStub:
        channel = grpc.aio.insecure_channel(self.url, options=self.options)
        stub = runner_pb2_grpc.RunnerStub(channel)
        return stub

    def status(self):
        client = self.client()
        try:
            request = runner_pb2.GetRunnerRequest()
            response = client.get_runner(request)
            return response.status
        except grpc.RpcError as e:
            raise e

    def get_client_state(self) -> grpc.ChannelConnectivity:
        channel = grpc.insecure_channel(self.url)
        return channel.get_state()


