import time

import pytest
from fastapi.testclient import TestClient

from indigoapi.config import Config
from indigoapi.main import start_api

app = start_api()
client = TestClient(app)


def test_analysis_flow():

    response = client.post(
        "/analyse", json={"analysis_name": "double", "inputs": {"value": 21}}
    )

    assert response.status_code == 200

    request_id = response.json()["request_id"]
    with TestClient(app) as client_http:
        for _ in range(10):
            r = client_http.get(f"/result/{request_id}")

            if r.status_code == 200:
                time.sleep(0.1)
                continue
            else:
                break
        else:
            pytest.fail("Result not ready in time")

        assert r is not None
        data = r.json()

        assert data["status"] == "completed"
        assert data["result"] == 42


def test_empty_config_intialises():

    cfg = Config()
    assert isinstance(cfg, Config)


def test_config_loads_from_file():

    cfg = Config.load_config()
    assert isinstance(cfg, Config)
