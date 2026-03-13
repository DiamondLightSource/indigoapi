import asyncio
import json
import logging

import stomp

from indigoapi.models import AnalysisRequest
from indigoapi.queue_manager import QueueManager

logger = logging.getLogger(__name__)

RETRY_INTERVAL = 30  # seconds


class _StompListener(stomp.ConnectionListener):
    def __init__(self, queue_manager: QueueManager, loop: asyncio.AbstractEventLoop):
        self.queue_manager = queue_manager
        self.loop = loop

    def on_connected(self, frame):
        logger.info("STOMP connected")

    def on_disconnected(self):
        logger.warning("STOMP disconnected")

    def on_heartbeat_timeout(self):
        logger.warning("STOMP heartbeat timeout — connection likely dead")

    def on_error(self, frame):
        logger.error(f"STOMP error: {frame.body}")

    def on_message(self, frame):

        # STOMP must send JSON like:

        # message = {
        #       "analysis_name": "gaussian_fit",
        #       "inputs" : {"x": [1,2,3], "y" : [4,5,6]},
        #     }

        print(frame)

        try:
            data = json.loads(frame.body)

            job = AnalysisRequest(**data)

            logger.info(f"RabbitMQ job received: {job.request_id}")

            asyncio.run_coroutine_threadsafe(
                self.queue_manager.enqueue(job),
                self.loop,
            )

        except Exception as e:
            logger.error(f"Failed to process STOMP message: {e}")


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

        self.conn: stomp.Connection | None = None

    async def start(self):

        loop = asyncio.get_running_loop()

        while True:
            try:
                logger.info("Connecting to RabbitMQ (STOMP)")

                self.conn = stomp.Connection(
                    [(self.host, self.port)],
                    heartbeats=(10000, 10000),
                    heart_beat_receive_scale=1.5,
                )

                listener = _StompListener(self.queue_manager, loop)
                self.conn.set_listener("", listener)

                self.conn.connect(self.username, self.password, wait=True)

                logger.info("Connected to RabbitMQ")

                for i, destination in enumerate(self.destinations):
                    self.conn.subscribe(
                        destination=destination,
                        id=str(i),
                        ack="auto",
                    )

                    logger.info(f"Listening on {destination}")

                # Wait until connection actually dies
                while True:
                    if not self.conn.is_connected():
                        logger.warning("STOMP connection lost")
                        break

                    transport = self.conn.transport

                    if transport is None or not transport.is_connected():
                        logger.warning("STOMP transport closed")
                        break

                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"RabbitMQ STOMP listener failed: {e}")

            logger.info(f"Reconnecting in {RETRY_INTERVAL} seconds")
            await asyncio.sleep(RETRY_INTERVAL)
