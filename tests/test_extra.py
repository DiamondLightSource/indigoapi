import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from indigoapi.__main__ import main
from indigoapi.analyses.decorator import analysis
from indigoapi.analyses.loader import (
    clone_github_repo,
    load_plugins,
    load_plugins_from_dir,
)
from indigoapi.analyses.registry import (
    ANALYSIS_REGISTRY,
    get_analysis,
    register_analysis,
)
from indigoapi.cleanup import cleanup_results
from indigoapi.client import AnalysisClient
from indigoapi.config import Config
from indigoapi.main import start_api
from indigoapi.models import AnalysisRequest, AnalysisResult
from indigoapi.rabbitmq_listener import _StompListener


def test_cli_main_no_command_prints_message():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "Please invoke subcommand!" in result.output


def test_cli_serve_invokes_uvicorn(monkeypatch):
    runner = CliRunner()
    called = {}

    def fake_run(app, host=None, port=None):
        called["host"] = host
        called["port"] = port
        called["app"] = app

    monkeypatch.setattr("indigoapi.__main__.uvicorn.run", fake_run)
    result = runner.invoke(main, ["serve"])

    assert result.exit_code == 0
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 8000


def test_config_loads_path_from_env(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("server:\n  host: 127.0.0.1\n  port: 1234\n")
    monkeypatch.setenv("CONFIG_PATH", str(config_file))

    cfg = Config.load_config()
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 1234


def test_config_returns_default_for_missing_file(tmp_path):
    cfg = Config.load_config(tmp_path / "nope.yaml")
    assert cfg.server.host == "0.0.0.0"
    assert cfg.queue.workers == 2


def test_models_item_access():
    request = AnalysisRequest(analysis_name="double", inputs={"number": 10})
    assert request["analysis_name"] == "double"

    result = AnalysisResult(
        request_id=request.request_id,
        analysis_name="double",
        status="completed",
        result=20,
        created_at=datetime.now(),
        finished_at=datetime.now(),
    )
    assert result["status"] == "completed"


def test_client_convert_to_serialisable():
    client = AnalysisClient(session=Mock())

    converted = client._convert_to_serialisable(
        {
            "x": np.array([1, 2]),
            "n": np.int64(3),
            "f": np.float32(4.5),
            "nested": {"t": np.int32(7)},
            "seq": (np.int16(8),),
        }
    )

    assert converted["x"] == [1, 2]
    assert converted["n"] == 3
    assert converted["f"] == 4.5
    assert converted["nested"]["t"] == 7
    assert converted["seq"] == [8]


def test_client_submit_and_latest_request_id():
    response_id = str(uuid.uuid4())
    response = Mock()
    response.json.return_value = {"request_id": response_id}
    response.raise_for_status = Mock()

    session = Mock()
    session.post.return_value = response

    client = AnalysisClient(base_url="http://test", session=session)
    request_id = client.submit("double", x=np.array([1, 2]))

    assert str(request_id) == response_id
    assert client.latest_request_id == request_id
    session.post.assert_called_once()


def test_client_request_result_404():
    response = Mock(status_code=404)
    response.raise_for_status = Mock()
    session = Mock()
    session.get.return_value = response

    client = AnalysisClient(session=session)
    assert client.request_result(uuid.uuid4()) is None


def test_client_get_result_no_latest():
    client = AnalysisClient(session=Mock())
    result = client.get_result()

    assert result.status == "error"
    assert result.analysis_name == ""


def test_client_get_request_id_result_timeout(monkeypatch):
    client = AnalysisClient(session=Mock())
    client.request_result = Mock(return_value=None)

    times = [0.0, 0.0, 0.1, 0.2]

    def fake_time():
        return times.pop(0)

    monkeypatch.setattr("indigoapi.client.time.time", fake_time)
    monkeypatch.setattr("indigoapi.client.time.sleep", lambda _: None)

    with pytest.raises(TimeoutError):
        client.get_request_id_result(uuid.uuid4(), timeout=0.05, poll_interval=0.01)


def test_client_health_and_endpoints():
    health_response = Mock()
    health_response.status_code = 200
    health_response.json.return_value = {"status": "ok"}
    health_response.raise_for_status = Mock()

    endpoints_response = Mock()
    endpoints_response.status_code = 200
    endpoints_response.json.return_value = [{"path": "/health", "methods": ["GET"]}]
    endpoints_response.raise_for_status = Mock()

    session = Mock()
    session.get.side_effect = [health_response, endpoints_response]

    client = AnalysisClient(base_url="http://test", session=session)
    assert client.health() == {"status": "ok"}
    assert client.get_endpoints() == [{"path": "/health", "methods": ["GET"]}]


def test_api_health_and_endpoints_routes():
    app = start_api()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        response = client.get("/endpoints")
        assert response.status_code == 200
        assert any(route["path"] == "/health" for route in response.json())


def test_api_result_latest_and_not_found():
    app = start_api()
    with TestClient(app) as client:
        result = AnalysisResult(
            request_id=uuid.uuid4(),
            analysis_name="double",
            status="completed",
            result=10,
            created_at=datetime.now(),
            finished_at=datetime.now(),
        )
        client.app.state.queue_manager.latest_result = result  # type: ignore

        latest_response = client.get("/result/latest")
        assert latest_response.status_code == 200
        assert latest_response.json()["status"] == "completed"

        missing_response = client.get("/result/id/00000000-0000-0000-0000-000000000000")
        assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_cleanup_results_removes_expired(monkeypatch):
    class FakeQueue:
        pass

    now = time.time() - 10
    fake_queue = FakeQueue()
    fake_queue.results = {uuid.uuid4(): (None, now)}  # type: ignore

    async def fake_sleep(interval):
        raise asyncio.CancelledError

    monkeypatch.setattr("indigoapi.cleanup.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await cleanup_results(fake_queue, ttl=1, interval=0)

    assert fake_queue.results == {}  # type: ignore


def test_analysis_decorator_registers_sync_function():
    original_registry = ANALYSIS_REGISTRY.copy()
    try:

        @analysis("my_test_double")
        def my_double(number: int) -> int:
            return number * 2

        assert asyncio.iscoroutinefunction(my_double)
        fn = get_analysis("my_test_double")
        result = asyncio.run(fn(3))
        assert result == 6
    finally:
        ANALYSIS_REGISTRY.clear()
        ANALYSIS_REGISTRY.update(original_registry)


def test_registry_register_duplicate_raises():
    original_registry = ANALYSIS_REGISTRY.copy()
    try:
        register_analysis("duplicate_test", lambda x: x)
        with pytest.raises(ValueError):
            register_analysis("duplicate_test", lambda x: x)
    finally:
        ANALYSIS_REGISTRY.clear()
        ANALYSIS_REGISTRY.update(original_registry)


def test_registry_imports_missing_module(monkeypatch):
    original_registry = ANALYSIS_REGISTRY.copy()
    if "double" in ANALYSIS_REGISTRY:
        del ANALYSIS_REGISTRY["double"]

    def fake_import(module_name):
        return SimpleNamespace(double=lambda x: x * 2)

    monkeypatch.setattr(
        "indigoapi.analyses.registry.importlib.import_module",
        fake_import,
    )

    try:
        fn = get_analysis("double")
        assert callable(fn)
        assert fn(3) == 6
    finally:
        ANALYSIS_REGISTRY.clear()
        ANALYSIS_REGISTRY.update(original_registry)


def test_loader_load_plugins_from_dir(tmp_path):
    plugin_path = tmp_path / "dummy.py"
    side_effect_file = tmp_path / "loaded.txt"
    plugin_path.write_text(
        f"with open({str(side_effect_file)!r}, 'w') as f: f.write('ok')\n"
    )

    load_plugins_from_dir(tmp_path)
    assert side_effect_file.exists()
    assert side_effect_file.read_text() == "ok"

    if "dummy" in sys.modules:
        del sys.modules["dummy"]


def test_loader_clone_github_repo_existing(tmp_path):
    destination_dir = tmp_path / "repo"
    destination_dir.mkdir()
    result = clone_github_repo("https://example.com/repo.git", str(tmp_path))
    assert result == destination_dir


def test_loader_load_plugins_handles_clone_error(monkeypatch):
    cfg = Config()
    cfg.plugins.paths = []
    cfg.plugins.github_repos = ["https://example.com/repo.git"]

    def fake_clone(repo_url, dest_dir):
        raise RuntimeError("unable to clone")

    monkeypatch.setattr("indigoapi.analyses.loader.clone_github_repo", fake_clone)
    load_plugins(cfg)


def test_workflows_not_implemented():
    from indigoapi.analyses.workflows import Workflows

    with pytest.raises(NotImplementedError):
        Workflows()


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_stomp_listener_message_routes_enqueue(monkeypatch):
    enqueued = {}

    def fake_enqueue(job):
        enqueued["job"] = job

    queue_manager = SimpleNamespace(enqueue=fake_enqueue)
    loop = asyncio.new_event_loop()

    try:
        listener = _StompListener(queue_manager, loop)  # type: ignore

        def fake_run_coro_threadsafe(coro, event_loop):
            return None

        monkeypatch.setattr(
            "indigoapi.rabbitmq_listener.asyncio.run_coroutine_threadsafe",
            fake_run_coro_threadsafe,
        )

        frame = SimpleNamespace(
            body=json.dumps(
                {
                    "analysis_name": "double",
                    "inputs": {"number": 2},
                }
            )
        )
        listener.on_message(frame)
    finally:
        loop.close()


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_stomp_listener_invalid_json(monkeypatch):
    loop = asyncio.new_event_loop()
    try:
        queue_manager = SimpleNamespace(enqueue=Mock())
        listener = _StompListener(queue_manager, loop)  # type: ignore

        monkeypatch.setattr(
            "indigoapi.rabbitmq_listener.asyncio.run_coroutine_threadsafe",
            lambda coro, event_loop: None,
        )
        frame = SimpleNamespace(body="not-a-json")
        listener.on_message(frame)
    finally:
        loop.close()


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_stomp_listener_connection_events():
    loop = asyncio.new_event_loop()
    try:
        queue_manager = SimpleNamespace(enqueue=Mock())
        listener = _StompListener(queue_manager, loop)  # type: ignore

        listener.on_connected(None)
        listener.on_disconnected()
        listener.on_error(SimpleNamespace(body="error"))
    finally:
        loop.close()
