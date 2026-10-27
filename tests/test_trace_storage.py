from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from agentproof.trace_storage import SQLiteTraceRepository


def sample() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trace = [{"event_type": "tool_call", "name": "search", "arguments": {"q": "docs"}}]
    checks = [{"type": "tool_called", "name": "search"}]
    report = {
        "passed": True,
        "score": 1.0,
        "summary": {"total": 1, "passed": 1, "failed": 0},
        "results": [{"index": 0, "type": "tool_called", "passed": True, "actual": True}],
    }
    return trace, checks, report


def test_trace_evaluation_round_trip() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = SQLiteTraceRepository(Path(directory) / "history.sqlite3")
        trace, checks, report = sample()
        trace_id = repo.save_evaluation(trace, checks, report)

        loaded = repo.get_evaluation(trace_id)
        assert loaded is not None
        assert loaded["trace_id"] == trace_id
        assert loaded["trace"] == trace
        assert loaded["checks"] == checks
        assert loaded["results"] == report["results"]
        assert loaded["passed"] is True


def test_trace_history_list_is_summary_only_and_bounded() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo = SQLiteTraceRepository(Path(directory) / "history.sqlite3")
        trace, checks, report = sample()
        trace_id = repo.save_evaluation(trace, checks, report)

        rows = repo.list_evaluations(limit=500)
        assert len(rows) == 1
        assert rows[0]["trace_id"] == trace_id
        assert "trace" not in rows[0]
        assert repo.get_evaluation("missing") is None
