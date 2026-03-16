import asyncio
import json
import logging
import threading
import time

import stomp

from indigoapi.models import AnalysisRequest
from indigoapi.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class _StompListener(stomp.ConnectionListener):
    def __init__(self, queue_manager: QueueManager, loop: asyncio.AbstractEventLoop):
        self.queue_manager = queue_manager
        self.loop = loop

    def on_connected(self, frame):
        logger.info("STOMP connected to RabbitMQ")

    def on_disconnected(self):
        logger.warning("STOMP disconnected from RabbitMQ")

    def on_error(self, frame):
        logger.error(f"STOMP error: {frame.body}")

    def on_message(self, frame):
        try:
            data = json.loads(frame.body)

            job = AnalysisRequest(**data)

            logger.info(f"RabbitMQ job received: {job.request_id}")

            asyncio.run_coroutine_threadsafe(
                self.queue_manager.enqueue(job),
                self.loop,
            )

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            logger.error("Failed message:", frame.body)


class RabbitMQListener:
    def __init__(
        self,
        queue_manager: QueueManager,
        host: str,
        port: int,
        username: str,
        password: str,
        destinations: list[str],
    ):
        self.queue_manager = queue_manager
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.destinations = destinations

        self.running = True
        self.thread: threading.Thread | None = None

    async def start(self):
        loop = asyncio.get_running_loop()

        self.thread = threading.Thread(
            target=self._run,
            args=(loop,),
            daemon=True,
        )

        self.thread.start()

        logger.info("RabbitMQ listener thread started")

    def _run(self, loop: asyncio.AbstractEventLoop):

        attempt = 0

        while self.running:
            attempt += 1

            logger.info(
                f"RabbitMQ connection attempt {attempt} to {self.host}:{self.port}"
            )

            try:
                conn = stomp.Connection(
                    [(self.host, self.port)],
                )

                listener = _StompListener(self.queue_manager, loop)
                conn.set_listener("", listener)

                conn.connect(self.username, self.password, wait=True)

                logger.info("RabbitMQ connected")

                for i, dest in enumerate(self.destinations):
                    conn.subscribe(destination=dest, id=str(i), ack="auto")
                    logger.info(f"Subscribed to {dest}")

                while conn.is_connected():
                    time.sleep(1)

                logger.warning("RabbitMQ connection lost")

            except Exception as e:
                logger.warning(f"RabbitMQ connection failed: {e}")
