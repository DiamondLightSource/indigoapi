"""Interface for ``python -m indigoapi``."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from indigoapi.analyses import MODULE_NAMES  # auto-register plugins
from indigoapi.api.routes import ROUTER
from indigoapi.cleanup import cleanup_results
from indigoapi.config import Config
from indigoapi.queue_manager import QueueManager

from . import __version__

config: Config = Config.load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    queue_manager = QueueManager(workers=config.queue.workers)
    workers = [
        asyncio.create_task(queue_manager.worker())
        for _ in range(queue_manager.workers)
    ]
    cleanup = asyncio.create_task(
        cleanup_results(
            queue_manager,
            ttl=config.results.ttl_seconds,
            interval=config.cleanup.interval_seconds,
        )
    )

    app.state.queue_manager = queue_manager
    app.state.config = config
    yield

    for task in workers:
        task.cancel()
    cleanup.cancel()


def start_api() -> FastAPI:

    logger = logging.getLogger(__name__)
    logger.info(f"{MODULE_NAMES} have been loaded")
    logger = logging.info(f"version: {__version__}")

    app = FastAPI(lifespan=lifespan)
    app.include_router(ROUTER)

    return app
