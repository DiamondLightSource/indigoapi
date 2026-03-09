import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

import numpy as np
import requests

from indigoapi.models import AnalysisResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisClient:
    """
    Python client for the Analysis API
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        session: requests.Session | None = None,  # set to None for usual use
    ):
        self.base_url = base_url.rstrip("/")
        self.last_request_id: UUID | None = None
        self.session = session or requests.Session()  # useful for testing

    def list_analyses(self) -> list[dict[str, Any]]:
        """
        Return all available analysis jobs with parameters.
        """
        resp = self.session.get(f"{self.base_url}/get_analyses")
        resp.raise_for_status()
        return resp.json()

    def _convert_to_serialisable(self, obj):

        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)  # Convert all np.int* types
        elif isinstance(obj, np.floating):
            return float(obj)  # Convert all np.float* types
        elif isinstance(obj, (set, frozenset)):
            return tuple(obj)
        else:
            return obj

    def _serialisable_payload(self, payload: dict):

        for k, v in payload.items():
            payload[k] = self._convert_to_serialisable(v)

        return payload

    def submit(self, analysis_type: str, payload: dict[str, Any]) -> UUID:
        """
        Submit an analysis job.
        Returns the request_id.
        """

        payload = self._serialisable_payload(payload)

        data = {"analysis_type": analysis_type, "payload": payload}
        resp = self.session.post(f"{self.base_url}/analyse", json=data)
        resp.raise_for_status()
        request_id = UUID(resp.json()["request_id"])

        self.last_request_id = request_id

        return request_id

    def request_result(self, request_id: UUID) -> AnalysisResult | None:
        """
        Retrieve a job result.
        Returns None if not found.
        """
        resp = self.session.get(f"{self.base_url}/result/{request_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        response = resp.json()

        result = AnalysisResult(**response)

        return result

    def get_result(
        self, timeout: float = 30.0, poll_interval: float = 0.1
    ) -> AnalysisResult:

        if self.last_request_id is None:
            return AnalysisResult(
                status="error",
                result=None,
                created_at=datetime.now(),
                finished_at=datetime.now(),
            )
        else:
            return self.get_request_id_result(
                request_id=self.last_request_id,
                timeout=timeout,
                poll_interval=poll_interval,
            )

    def get_request_id_result(
        self, request_id: UUID, timeout: float = 30.0, poll_interval: float = 0.1
    ) -> AnalysisResult:
        """
        Poll the API until result is ready or timeout expires.
        """
        start_time = time.time()
        while True:
            result = self.request_result(request_id)

            if result is not None:
                return result
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Result not ready after {timeout} seconds")
            time.sleep(poll_interval)
