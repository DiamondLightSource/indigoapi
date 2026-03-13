import asyncio
import logging
import time
from datetime import datetime
from uuid import UUID

from indigoapi.analyses.registry import get_analysis
from indigoapi.models import AnalysisRequest, AnalysisResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueueManager:
    def __init__(self, workers: int = 2):
        self.queue: asyncio.Queue[AnalysisRequest] = asyncio.Queue()
        self.results: dict[UUID, tuple[AnalysisResult, float]] = {}
        self.workers = workers
        self.latest_result: AnalysisResult | None = None

        logger.info(self.queue)

    async def enqueue(self, job: AnalysisRequest):
        job.created_at = datetime.now()
        logger.info(job)
        await self.queue.put(job)

    async def worker(self):
        while True:
            job = await self.queue.get()

            try:
                analysis_fn = get_analysis(job.analysis_name)

                result_value = await analysis_fn(**job.inputs)

                result = AnalysisResult(
                    request_id=job.request_id,
                    analysis_name=job.analysis_name,
                    status="completed",
                    result=result_value,
                    created_at=job.created_at,
                    finished_at=datetime.now(),
                )

            except Exception as e:
                result = AnalysisResult(
                    request_id=job.request_id,
                    analysis_name=job.analysis_name,
                    status="failed",
                    result=str(e),
                    created_at=job.created_at,
                    finished_at=datetime.now(),
                )

                print(f"Job {job.request_id} failed: {e}")

            self.results[job.request_id] = (result, time.time())
            # store latest result
            self.latest_result = result
