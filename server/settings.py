import enum
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
from dotenv import load_dotenv

from pydantic import BaseSettings
from yarl import URL

TEMP_DIR = Path(gettempdir())
load_dotenv()

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

    ssh_keys_path: str = os.getenv("SSH_KEYS_PATH", "/root/.ssh")

    api_url: str = os.getenv("API_URL", "http://localhost:8000")

    x_api_key: str = os.getenv("X_API_KEY")

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
    redis_host: str = "server-redis"
    redis_port: int = 6379
    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_base: Optional[int] = None

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

    @property
    def models_dir(self) -> str:
        """
        Return path to models directory."""
        # create a path to the models directory
        models_dir = "/var/lib/docker/volumes/filez-models"
        # create the directory if it does not exist
        return models_dir

    @property
    def datasets_dir(self) -> str:
        """
        Return path to datasets directory."""
        # create a path to the datasets directory
        datasets_dir = "/var/lib/docker/volumes/filez-datasets"
        # create the directory if it does not exist
        return datasets_dir

    @property
    def jobs_dir(self) -> str:
        """
        Return path to jobs directory."""
        # create a path to the jobs directory
        jobs_dir = "/var/lib/docker/volumes/filez-jobs"
        # create the directory if it does not exist
        return jobs_dir

    @property
    def results_dir(self) -> str:
        """
        Return path to results directory."""
        # create a path to the results directory
        results_dir = "/var/lib/docker/volumes/filez-results"
        # create the directory if it does not exist
        return results_dir


    class Config:
        env_file = ".env"
        env_prefix = "SERVER_"
        env_file_encoding = "utf-8"


settings = Settings()
