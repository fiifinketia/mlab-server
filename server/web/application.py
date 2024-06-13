from importlib import metadata
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import UJSONResponse
from fastapi.security import HTTPBearer

from server.services.auth_bearer import JWTPayload, verify_jwt
from server.settings import settings
from server.web.api.router import api_router
from server.web.lifetime import register_shutdown_event, register_startup_event


def get_app() -> FastAPI:
    """
    Get FastAPI application.

    This is the main constructor of an application.

    :return: application.
    """
    app = FastAPI(
        title="server",
        version=metadata.version("server"),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=UJSONResponse,
    )

    origins = ["*", "https://mlab.appatechlab.com:8080", "https://disal.appatechlab.com:8080"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.middleware("http")
    async def check_auth(request: Request, call_next: Any) -> Any:
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path.endswith("/api/models") and request.method == "GET":
            return await call_next(request)
        if request.url.path.startswith("/api/docs") or request.url.path.startswith("/api/health") or request.url.path.startswith("/api/openapi.json"):
            return await call_next(request)
        credentials = request.headers.get("Authorization")
        if credentials:
            if not credentials.startswith("Bearer "):
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            try:
                token = credentials.split(" ")[1]
                payload = verify_jwt(token)
                request.state.user_id = payload.get("username")
                request.state.user_token = token
            except:
                raise HTTPException(status_code=403, detail="Invalid authorization code.")
            return await call_next(request)
        # check if headers has x-api-key
        if request.headers.get("x-api-key") == settings.x_api_key:
            # add user_id to request
            admin_jwt = JWTPayload(
                sub="admin",
                exp=0,
                aud="admin",
                iss="admin",
                iat=0,
                username="admin",
                email="admin",
                name="admin",
            )
            request.state.user_id = admin_jwt.username
            return await call_next(request)
        raise HTTPException(status_code=403, detail="Invalid authorization code.")

    # Adds startup and shutdown events.
    register_startup_event(app)
    register_shutdown_event(app)

    # Main router for the API.
    app.include_router(router=api_router, prefix="/api")

    return app
