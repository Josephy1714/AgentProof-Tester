from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from typing import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agentproof.api import Handler


@contextmanager
def running_api() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(url: str, payload: object | None = None) -> tuple[int, dict[str, object]]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.fixture
def api_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "agentproof-test.sqlite3"))
    monkeypatch.delenv("AGENTPROOF_API_TOKEN", raising=False)


def valid_suite() -> dict[str, object]:
    return {
        "name": "browser-api-smoke",
        "version": "1.0",
        "tests": [
            {
                "id": "checks-structured-output",
                "input": {"simulated_output": {"answer": "hello", "status": "ok"}},
                "assertions": [
                    {"type": "has_key", "expected": "answer"},
                    {"type": "equals", "path": "status", "expected": "ok"},
                    {"type": "is_type", "path": "answer", "expected": "string"},
                ],
            }
        ],
    }


def test_post_run_executes_checks_and_persists_detail(api_env: None) -> None:
    with running_api() as base_url:
        status, run = request_json(base_url + "/api/runs", valid_suite())
        assert status == 201
        run_id = str(run["run_id"])
        assert run["simulated"] is True
        assert run["summary"]["passed"] == 1
        assert run["summary"]["failed"] == 0

        list_status, history = request_json(base_url + "/api/runs?limit=10")
        detail_status, detail = request_json(base_url + "/api/runs/" + run_id)
        overview_status, overview = request_json(base_url + "/api/dashboard/overview")

    assert list_status == 200
    assert any(row["run_id"] == run_id for row in history["data"])
    assert detail_status == 200
    assert detail["test_results"][0]["test_id"] == "checks-structured-output"
    assert detail["test_results"][0]["status"] == "passed"
    assert overview_status == 200
    assert overview["total_runs"] == 1
    assert overview["total_tests"] == 1


def test_post_run_returns_validation_error_for_unknown_assertion(api_env: None) -> None:
    suite = valid_suite()
    suite["tests"][0]["assertions"] = [{"type": "not-a-real-check"}]
    with running_api() as base_url:
        status, payload = request_json(base_url + "/api/runs", suite)
    assert status == 400
    assert "Unsupported assertion" in str(payload["error"])


def test_post_run_rejects_empty_test_list(api_env: None) -> None:
    with running_api() as base_url:
        status, payload = request_json(base_url + "/api/runs", {"name": "empty", "tests": []})
    assert status == 400
    assert "between 1 and 10 tests" in str(payload["error"])


def test_post_run_requires_bearer_token_when_configured(api_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTPROOF_API_TOKEN", "test-token")
    with running_api() as base_url:
        status, payload = request_json(base_url + "/api/runs", valid_suite())
        good_request = Request(
            base_url + "/api/runs",
            data=json.dumps(valid_suite()).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer test-token"},
            method="POST",
        )
        try:
            with urlopen(good_request, timeout=3) as response:
                good_status, good_payload = response.status, json.loads(response.read())
        except HTTPError as exc:
            good_status, good_payload = exc.code, json.loads(exc.read())

    assert status == 401
    assert payload == {"error": "Unauthorized"}
    assert good_status == 201
    assert good_payload["summary"]["passed"] == 1
