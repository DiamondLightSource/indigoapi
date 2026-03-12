from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class RabbitMQConfig(BaseModel):
    url: str = "ixx-rabbitmq-daq.diamond.ac.uk"
    queue: str = "analysis_jobs"  # this is where rabbitmq listens


class QueueConfig(BaseModel):
    workers: int = 2


class ResultsConfig(BaseModel):
    # time to live seconds - how long the results
    # from a process can live before being being valid for removal
    ttl_seconds: int = 3600  # 3600s = 1hr


class CleanupConfig(BaseModel):
    # how frequently the cleanup job actually runs
    interval_seconds: int = 300


class PluginsConfig(BaseModel):
    paths: list[str] = []
    github_repos: list[str] | None = []


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    queue: QueueConfig = QueueConfig()
    results: ResultsConfig = ResultsConfig()
    cleanup: CleanupConfig = CleanupConfig()
    plugins: PluginsConfig = PluginsConfig()
    rabbitmq: RabbitMQConfig = RabbitMQConfig()

    @classmethod
    def load_config(cls, path: str | Path = "config.yaml") -> Self:
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
