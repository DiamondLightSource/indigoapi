import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from indigoapi.models import AnalysisRequest
from indigoapi.queue_manager import QueueManager

logger = logging.getLogger(__name__)

RETRY_FREQUENCY = 10  # in seconds


class RabbitListener:
    def __init__(self, queue_manager: QueueManager, url: str, queue_name: str):
        self.queue_manager = queue_manager
        self.url = url
        self.queue_name = queue_name
        self.connection = None

    async def start(self):

        while True:
            try:
                logger.info("Connecting to RabbitMQ")

                connection = await aio_pika.connect_robust(self.url)

                channel = await connection.channel()

                queue = await channel.declare_queue(
                    self.queue_name,
                    durable=True,
                )

                logger.info(f"Listening on {self.queue_name}")

                await queue.consume(self._handle_message)

                # wait until connection closes
                await connection.closed()
                # if the connection closes it will loop and try to connect again

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
