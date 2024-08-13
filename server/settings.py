"""Settings for the application."""
import enum
import importlib
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
import dotenv

from pydantic import BaseSettings
from yarl import URL

TEMP_DIR = Path(gettempdir())
dotenv.load_dotenv(verbose=True, override=True)

class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    host: str = os.getenv("HOST", "localhost")
    port: int = int(os.getenv("PORT", "8000"))
    # quantity of workers for uvicorn, get from env
    workers_count: int = int(os.getenv("WORKERS_COUNT", "1"))
    # Enable uvicorn reloading
    reload: bool = False

    ssh_keys_path: str = "/root/.ssh"

    api_url: str = os.getenv("API_URL", "http://localhost:8000")
    rpc_url: str = os.getenv("RPC_URL", "localhost:50051")
    cog_internal_api_url: str = os.getenv("COG_INTERNAL_API_URL", "http://host.docker.internal:8090/api")

    x_api_key: str = os.getenv("X_API_KEY", "")

    image_storage: str = os.getenv("IMAGE_STORAGE", "/var/lib/docker/volumes/filez/images")

    # Current environment
    environment: str = os.getenv("ENVIRONMENT", "dev")
    log_level: LogLevel = LogLevel.INFO
    # Variables for the database
    db_host: str = os.getenv("DB_HOST", "server-db")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_user: str = os.getenv("DB_USER", "server")
    db_pass: str = os.getenv("DB_PASS", "")
    db_base: str = os.getenv("DB_BASE", "server")
    db_echo: bool = False

    # Variables for Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_base: Optional[int] = None

    # Variables for the GitHub API
    gitlab_url: str = os.getenv("GITLAB_URL", "")
    gitlab_server: str = os.getenv("GITLAB_SERVER", "")
    gitlab_token: str = os.getenv("GITLAB_TOKEN", "")
    # git_user_path: str = "/var/lib/git"

    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "")

    job_limit: int = int(os.getenv("JOB_LIMIT", "30"))

    cog_base_dir = os.getenv("COG_BASE_DIR", "/var/lib/docker/volumes/filez")

    results_dir: str = os.getenv("RESULTS_DIR", "/var/lib/docker/volumes/filez/results")

    runners_list_path: str = os.getenv("RUNNERS_LIST", "/var/lib/docker/volumes/filez/runners.json")
    # datasets_dir: str = git_user_path + "/datasets"
    # models_dir: str = git_user_path + "/models"

    # sudo_password: str = os.getenv("SUDO_PASSWORD", "")

    @property
    def get_runners_url(self) -> str:
        """Returns str"""
        return f"{self.api_url}/api/runners"

    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.

        :return: database URL.
        """
        return URL.build(
            scheme="postgresql",
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            path=f"/{self.db_base}",
        )

    @property
    def redis_url(self) -> URL:
        """
        Assemble REDIS URL from settings.

        :return: redis URL.
        """
        path = ""
        if self.redis_base is not None:
            path = f"/{self.redis_base}"
        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            user=self.redis_user,
            password=self.redis_pass,
            path=path,
        )


    class Config:
        """Configuration for settings."""
        env_file = ".env"
        env_prefix = "SERVER_"
        env_file_encoding = "utf-8"


settings = Settings()
