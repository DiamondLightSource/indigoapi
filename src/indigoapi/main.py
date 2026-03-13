"""Interface for ``python -m indigoapi``."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from indigoapi.analyses import MODULE_NAMES
from indigoapi.api.routes import ROUTER
from indigoapi.cleanup import cleanup_results
from indigoapi.config import Config
from indigoapi.queue_manager import QueueManager
from indigoapi.rabbitmq_listener import RabbitMQListener

from . import __version__

config: Config = Config.load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):

    queue_manager = QueueManager(workers=config.queue.workers)

    # start worker tasks
    workers = [
        asyncio.create_task(queue_manager.worker())
        for _ in range(queue_manager.workers)
    ]

    # start cleanup task
    cleanup_task = asyncio.create_task(
        cleanup_results(
            queue_manager,
            ttl=config.results.ttl_seconds,
            interval=config.cleanup.interval_seconds,
        )
    )

    rabbit_task: asyncio.Task | None = None

    if config.rabbitmq.listen_to_rabbitmq:
        rabbit_listener = RabbitMQListener(
            queue_manager=queue_manager,
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            username=config.rabbitmq.username,
            password=config.rabbitmq.password,
            destinations=config.rabbitmq.destinations,
        )
        rabbit_task = asyncio.create_task(rabbit_listener.start())

    # store state
    app.state.queue_manager = queue_manager
    app.state.config = config

    yield

    # ---- shutdown phase ----

    for task in workers:
        task.cancel()

    cleanup_task.cancel()

    if rabbit_task is not None:
        rabbit_task.cancel()

    await asyncio.gather(*workers, return_exceptions=True)
    await asyncio.gather(cleanup_task, return_exceptions=True)

    if rabbit_task is not None:
        await asyncio.gather(rabbit_task, return_exceptions=True)


def start_api() -> FastAPI:

    logger = logging.getLogger(__name__)
    logger.info(f"{MODULE_NAMES} have been loaded")
    logger.info(f"version: {__version__}")

    app = FastAPI(lifespan=lifespan)
    app.include_router(ROUTER)

    return app
