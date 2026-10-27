from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from typing import Any, Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import agentproof.api as api


@contextmanager
def running_api() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def post_json(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def live_suite() -> dict[str, Any]:
    return {
        "name": "openrouter-live-smoke-test",
        "version": "1.0",
        "provider": "openrouter",
        "tests": [{
            "id": "real-answer-check",
            "input": {"prompt": "What is 12 times 8? Reply with only the number."},
            "assertions": [{"type": "contains", "path": "content", "value": "96"}],
        }],
    }


def test_openrouter_requires_server_side_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "agentproof.sqlite3"))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with running_api() as base_url:
        status, payload = post_json(base_url + "/api/runs", live_suite())
    assert status == 503
    assert "OPENROUTER_API_KEY" in payload["error"]


def test_openrouter_runs_real_adapter_contract_and_persists_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "agentproof.sqlite3"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-never-used-for-network")

    class FakeOpenRouterAdapter:
        name = "openai-compatible"
        is_simulated = False

        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["model"] == "openrouter/free"
            assert kwargs["base_url"] == "https://openrouter.ai/api/v1"
            assert kwargs["max_tokens"] == 128

        def invoke(self, payload: Any) -> dict[str, str]:
            assert "12 times 8" in payload["prompt"]
            return {"content": "96"}

    monkeypatch.setattr(api, "OpenAICompatibleAdapter", FakeOpenRouterAdapter)
    with running_api() as base_url:
        status, run = post_json(base_url + "/api/runs", live_suite())
        list_request = Request(base_url + "/api/runs?limit=10")
        with urlopen(list_request, timeout=3) as response:
            history = json.loads(response.read())

    assert status == 201
    assert run["simulated"] is False
    assert run["adapter_name"] == "openai-compatible"
    assert run["summary"]["passed"] == 1
    assert run["results"][0]["output"] == {"content": "96"}
    assert history["data"][0]["model"] == "openrouter/free"


def test_openrouter_rejects_simulated_input_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "agentproof.sqlite3"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    suite = live_suite()
    suite["tests"][0]["input"] = {"simulated_output": {"answer": "96"}}
    with running_api() as base_url:
        status, payload = post_json(base_url + "/api/runs", suite)
    assert status == 400
    assert "input.prompt or input.messages" in payload["error"]
