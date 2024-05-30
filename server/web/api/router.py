from fastapi.routing import APIRouter

from server.web.api import monitoring
from server.web.api.datasets import routes as datasets_routes
from server.web.api.jobs import routes as jobs_routes
from server.web.api.models import routes as models_routes
from server.web.api.results import routes as results_routes
from server.web.api.iam import routes as iam_routes

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(models_routes.api_router, prefix="/models")
api_router.include_router(jobs_routes.api_router, prefix="/jobs")
api_router.include_router(datasets_routes.api_router, prefix="/datasets")
api_router.include_router(results_routes.api_router, prefix="/results")
api_router.include_router(iam_routes.api_router, prefix="/iam")
