from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from agentproof.cloud_storage import SupabaseHostedStorage
from agentproof.models import EvaluationRun, TestResult, TestStatus


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.body = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def make_run() -> EvaluationRun:
    return EvaluationRun(
        "run-1", "smoke", "1.0", "fingerprint", "test-adapter", True,
        "2026-10-27T10:00:00+00:00",
        12.0,
        (TestResult("case-1", TestStatus.PASSED, 1.0, 2.0),),
        1.0,
        {"passed": 1, "failed": 0},
    )


def test_cloud_storage_verifies_owner_before_writing() -> None:
    responses = [
        FakeResponse({"id": "verified-user-id"}),
        FakeResponse(None),
    ]
    requests: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        requests.append(request)
        return responses.pop(0)

    storage = SupabaseHostedStorage(
        "https://example.supabase.co", "publishable-key", "user-access-token"
    )
    with patch("agentproof.cloud_storage.urlopen", side_effect=fake_urlopen):
        storage.save_run(make_run(), provider="mock", model="test-model")

    assert requests[0].full_url == "https://example.supabase.co/auth/v1/user"
    assert requests[0].get_header("Authorization") == "Bearer user-access-token"
    assert requests[1].get_method() == "POST"
    sent = json.loads(requests[1].data)
    assert sent["user_id"] == "verified-user-id"
    assert sent["run_key"] == "run-1"
    assert sent["payload"]["suite_name"] == "smoke"
    assert "service_role" not in requests[1].get_header("Apikey", "").lower()


def test_history_queries_are_owner_scoped_and_bounded() -> None:
    responses = [
        FakeResponse({"id": "owner-123"}),
        FakeResponse([{"run_key": "r1", "payload": {"suite_name": "smoke"}}]),
    ]
    requests: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        requests.append(request)
        return responses.pop(0)

    storage = SupabaseHostedStorage(
        "https://example.supabase.co", "publishable-key", "valid-user-jwt"
    )
    with patch("agentproof.cloud_storage.urlopen", side_effect=fake_urlopen):
        rows = storage.list_runs(limit=1000, offset=-10, suite="smoke")

    assert rows[0]["run_id"] == "r1"
    assert "user_id=eq.owner-123" in requests[1].full_url
    assert "limit=200" in requests[1].full_url
    assert "offset=0" in requests[1].full_url
    assert "suite_name=eq.smoke" in requests[1].full_url


def test_hosted_storage_requires_https_and_credentials() -> None:
    import pytest

    with pytest.raises(ValueError):
        SupabaseHostedStorage("http://example.supabase.co", "key", "token")
    with pytest.raises(ValueError):
        SupabaseHostedStorage("https://example.supabase.co", "", "")



def test_hosted_run_detail_rebuilds_typed_evaluation_run() -> None:
    payload = {
        "run_id": "run-7",
        "suite_name": "smoke",
        "suite_version": "1.0",
        "config_fingerprint": "fingerprint",
        "adapter_name": "test-adapter",
        "simulated": True,
        "started_at": "2026-10-27T10:00:00+00:00",
        "duration_ms": 12.0,
        "score": 1.0,
        "summary": {"passed": 1, "failed": 0, "error": 0, "timeout": 0, "skipped": 0},
        "results": [{
            "test_id": "case-1",
            "status": "passed",
            "score": 1.0,
            "duration_ms": 2.0,
            "assertion_results": [{
                "assertion_type": "equals",
                "passed": True,
                "message": "matched",
                "expected": "yes",
                "actual": "yes",
            }],
            "output": {"answer": "yes"},
            "error_type": None,
            "error_message": None,
            "category": "general",
        }],
    }
    responses = [FakeResponse({"id": "owner-1"}), FakeResponse([{"run_key": "run-7", "payload": payload}])]
    requests: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        requests.append(request)
        return responses.pop(0)

    storage = SupabaseHostedStorage(
        "https://example.supabase.co", "publishable-key", "user-token"
    )
    with patch("agentproof.cloud_storage.urlopen", side_effect=fake_urlopen):
        run = storage.get_run("run-7")
        test_results = storage.get_test_results("run-7")

    assert run is not None
    assert run.run_id == "run-7"
    assert run.results[0].status == TestStatus.PASSED
    assert run.results[0].assertion_results[0].actual == "yes"
    assert test_results[0]["test_id"] == "case-1"
    assert test_results[0]["assertions"][0]["passed"] is True
    assert "user_id=eq.owner-1" in requests[1].full_url
