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


def request_status(url: str, token: str | None = None) -> tuple[int, dict[str, object]]:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_api_authentication_is_optional_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTPROOF_API_TOKEN", raising=False)
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "test.sqlite3"))

    with running_api() as base_url:
        status, payload = request_status(base_url + "/")
    assert status == 200
    assert payload["name"] == "AgentProof API"


def test_api_rejects_missing_and_invalid_bearer_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENTPROOF_API_TOKEN", "test-secret-token")
    monkeypatch.setenv("AGENTPROOF_DB", str(tmp_path / "test.sqlite3"))

    with running_api() as base_url:
        missing_status, missing_payload = request_status(base_url + "/")
        invalid_status, invalid_payload = request_status(base_url + "/", "wrong-token")
        valid_status, valid_payload = request_status(base_url + "/", "test-secret-token")

    assert missing_status == 401
    assert missing_payload == {"error": "Unauthorized"}
    assert invalid_status == 401
    assert invalid_payload == {"error": "Unauthorized"}
    assert valid_status == 200
    assert valid_payload["name"] == "AgentProof API"
