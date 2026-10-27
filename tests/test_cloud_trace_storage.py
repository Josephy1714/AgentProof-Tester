from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from agentproof.cloud_storage import SupabaseHostedStorage


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.body = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_trace_history_crud_uses_verified_owner_and_stable_key() -> None:
    responses = [
        FakeResponse({"id": "user-42"}),
        FakeResponse(None),
        FakeResponse([{
            "trace_key": "trace-abc",
            "passed": True,
            "score": 1.0,
            "evaluated_at": "2026-10-27T10:00:00+00:00",
            "summary": {"total": 1},
        }]),
        FakeResponse([{
            "trace_key": "trace-abc",
            "passed": True,
            "score": 1.0,
            "evaluated_at": "2026-10-27T10:00:00+00:00",
            "summary": {"total": 1},
            "trace": [{"event_type": "final_answer", "text": "done"}],
            "checks": [{"type": "final_answer_contains", "value": "done"}],
            "results": [{"passed": True}],
        }]),
    ]
    requests: list[Any] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        requests.append(request)
        return responses.pop(0)

    storage = SupabaseHostedStorage(
        "https://example.supabase.co", "publishable-key", "user-token"
    )
    trace = [{"event_type": "final_answer", "text": "done"}]
    checks = [{"type": "final_answer_contains", "value": "done"}]
    report = {"passed": True, "score": 1.0, "summary": {"total": 1}, "results": [{"passed": True}]}

    with patch("agentproof.cloud_storage.urlopen", side_effect=fake_urlopen):
        storage.save_trace_evaluation(trace, checks, report, trace_key="trace-abc")
        rows = storage.list_trace_evaluations()
        detail = storage.get_trace_evaluation("trace-abc")

    assert json.loads(requests[1].data)["user_id"] == "user-42"
    assert json.loads(requests[1].data)["trace_key"] == "trace-abc"
    assert rows[0]["trace_key"] == "trace-abc"
    assert "user_id=eq.user-42" in requests[2].full_url
    assert detail is not None and detail["trace"] == trace
    assert "user_id=eq.user-42" in requests[3].full_url
