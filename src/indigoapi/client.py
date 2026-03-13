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
        base_url: str = "http://127.0.0.1:8000",
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.last_request_id: UUID | None = None
        self.session = session or requests.Session()

    def list_analyses(self) -> list[dict[str, Any]]:
        resp = self.session.get(f"{self.base_url}/get_analyses")
        resp.raise_for_status()
        return resp.json()

    def _convert_to_serialisable(self, obj: Any) -> Any:

        if isinstance(obj, np.ndarray):
            return obj.tolist()

        if isinstance(obj, np.integer):
            return int(obj)

        if isinstance(obj, np.floating):
            return float(obj)

        if isinstance(obj, dict):
            return {k: self._convert_to_serialisable(v) for k, v in obj.items()}

        if isinstance(obj, (list, tuple, set)):
            return [self._convert_to_serialisable(v) for v in obj]

        return obj

    def submit(self, analysis_type: str, **inputs: Any) -> UUID:
        """
        Submit an analysis job.

        Example:
        client.submit("gaussian_fit", x=x, y=y)
        """

        inputs = self._convert_to_serialisable(inputs)

        data = {
            "analysis_type": analysis_type,
            "inputs": inputs,
        }

        resp = self.session.post(f"{self.base_url}/analyse", json=data)
        resp.raise_for_status()

        request_id = UUID(resp.json()["request_id"])
        self.last_request_id = request_id

        return request_id

    def request_result(self, request_id: UUID) -> AnalysisResult | None:

        resp = self.session.get(f"{self.base_url}/result/{request_id}")

        if resp.status_code == 404:
            return None

        resp.raise_for_status()

        response = resp.json()

        return AnalysisResult(**response)

    def get_result(
        self,
        timeout: float = 30.0,
        poll_interval: float = 0.1,
    ) -> AnalysisResult:

        if self.last_request_id is None:
            return AnalysisResult(
                status="error",
                result=None,
                created_at=datetime.now(),
                finished_at=datetime.now(),
            )

        return self.get_request_id_result(
            self.last_request_id,
            timeout,
            poll_interval,
        )

    def get_request_id_result(
        self,
        request_id: UUID,
        timeout: float = 30.0,
        poll_interval: float = 0.1,
    ) -> AnalysisResult:

        start_time = time.time()

        while True:
            result = self.request_result(request_id)

            if result is not None:
                return result

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Result not ready after {timeout} seconds")

            time.sleep(poll_interval)


if __name__ == "__main__":
    import numpy as np

    from indigoapi.analyses.peak_fitting import gaussian

    x = np.linspace(0, 20, 200)

    y = gaussian(x, 10, 5, 1)
    y = y + np.random.rand(y.shape[-1]) / 5

    client = AnalysisClient()

    print(client.list_analyses())

    client.submit("gaussian_fit", x=x, y=y)

    r = client.get_result()

    print(r)
