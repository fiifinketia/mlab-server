import enum
from pathlib import Path
from tempfile import gettempdir
from typing import Optional

from pydantic import BaseSettings
from yarl import URL

TEMP_DIR = Path(gettempdir())


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

    host: str = "0.0.0.0"
    port: int = 8000
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = False

    # Current environment
    environment: str = "dev"
    log_level: LogLevel = LogLevel.INFO
    # Variables for the database
    db_host: str = "0.0.0.0"
    db_port: int = 5432
    db_user: str = "server"
    db_pass: str = "server"
    db_base: str = "server"
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
