from fastapi import status
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from typing import List
from enum import Enum


class FileTypeName(str, Enum):
    # Audio file type
    mp3 = "audio/mp3"
    mpeg = "audio/mpeg"
    ogg = "audio/ogg"
    wave = "audio/wave"
    wav = "audio/wav"

    # Image file type
    jpeg = "image/jpeg"
    png = "image/png"
    jpg = "image/jpg"
    gif = "image/gif"
    webp = "image/webp"

    # Video file type
    webm = "video/webm"
    mp4 = "video/mp4"
    mpeg4 = "video/mpeg4"
    webm2 = "video/webm2"
    webm3 = "video/webm3"

    # text files
    txt = "text/plain"
    csv = "text/csv"
    json = "application/json"
    xml = "application/xml"
    html = "text/html"
    pdf = "application/pdf"
    doc = "application/msword"
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    xls = "application/vnd.ms-excel"
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ppt = "application/vnd.ms-powerpoint"
    pptx = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    # archive files
    zip = "application/zip"
    rar = "application/x-rar-compressed"
    tar = "application/x-tar"
    gzip = "application/x-gzip"
    tar_gz = "application/x-tar-gz"



    @classmethod
    def list(cls) -> list[str]:
        """Returns"""
        return list(map(lambda c: c.value, cls))


class ValidateUploadFileMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp, max_size: int = 1048576, # 1MB
        file_types: List[str] = FileTypeName.list()
    ) -> None:
        super().__init__(app)
        self.max_size = max_size
        self.file_types = file_types

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == 'POST':
            form = await request.form()
            file = form.get('file')
            if file is None:
                return Response(status_code=status.HTTP_400_BAD_REQUEST)
            if isinstance(file, str):
                raise NotImplementedError("This middleware does not support file str")
            if file.content_type not in self.file_types:
                return Response(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
            if 'content-length' not in request.headers:
                return Response(status_code=status.HTTP_411_LENGTH_REQUIRED)
            content_length = int(request.headers['content-length'])
            if content_length > self.max_size:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)
