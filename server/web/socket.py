from typing import List
import socketio
from fastapi import FastAPI


def handle_connect(sid, environ):
    print(f"Socket connected with sid {sid}")

class SocketManager:
    def __init__(self, origins: List[str]):
        self.server = socketio.AsyncServer(
            cors_allowed_origins=origins,
            async_mode="asgi",
            logger=True,
            engineio_logger=True,
        )
        self.app = socketio.ASGIApp(self.server)

    @property
    def on(self):
        return self.server.on

    @property
    def send(self):
        return self.server.send

    def mount_to(self, path: str, app: FastAPI):
        app.mount(path, self.app)
