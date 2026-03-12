import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from indigoapi.models import AnalysisRequest
from indigoapi.queue_manager import QueueManager

logger = logging.getLogger(__name__)

RETRY_FREQUENCY = 30  # in seconds


class RabbitMQListener:
    def __init__(self, queue_manager: QueueManager, url: str, queue_names: list[str]):
        self.queue_manager = queue_manager
        self.url = url
        self.queue_names = queue_names
        self.connection = None

    async def start(self):

        while True:
            try:
                logger.info("Connecting to RabbitMQ")

                connection = await aio_pika.connect_robust(self.url)
                channel = await connection.channel()

                for queue_name in self.queue_names:
                    queue = await channel.declare_queue(
                        queue_name,
                        durable=True,
                    )

                    await queue.consume(self._handle_message)

                    logger.info(f"Listening on {queue_name}")

                await connection.closed()

            except Exception as e:
                logger.error(f"RabbitMQ listener failed: {e}")
                await asyncio.sleep(RETRY_FREQUENCY)

    async def _handle_message(self, message: AbstractIncomingMessage):

        async with message.process():
            try:
                payload = json.loads(message.body)

                job = AnalysisRequest(**payload)

                logger.info(f"RabbitMQ job received: {job.request_id}")

                await self.queue_manager.enqueue(job)

            except Exception as e:
                logger.error(f"Failed to process RabbitMQ message: {e}")
