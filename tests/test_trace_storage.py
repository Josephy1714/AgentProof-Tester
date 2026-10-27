from __future__ import annotations

from pathlib import Path

from agentproof.trace_storage import SQLiteTraceRunRepository


def test_trace_runs_round_trip_inputs_and_report(tmp_path: Path) -> None:
    repository = SQLiteTraceRunRepository(tmp_path / "history.sqlite3")
    trace = [{"event_type": "tool_call", "name": "search", "arguments": {"q": "cats"}}]
    checks = [{"type": "tool_called", "name": "search"}]
    report = {
        "passed": True,
        "score": 1.0,
        "summary": {"total": 1, "passed": 1, "failed": 0},
        "results": [{"index": 0, "type": "tool_called", "passed": True}],
    }

    run_id = repository.save(trace, checks, report, fixture_name="sample.json")

    saved = repository.get_run(run_id)
    assert saved is not None
    assert saved["trace"] == trace
    assert saved["checks"] == checks
    assert saved["report"] == report
    assert saved["fixture_name"] == "sample.json"
    assert saved["passed"] is True


def test_trace_run_list_is_compact_and_newest_first(tmp_path: Path) -> None:
    repository = SQLiteTraceRunRepository(tmp_path / "history.sqlite3")
    report = {
        "passed": False,
        "score": 0.0,
        "summary": {"total": 1, "passed": 0, "failed": 1},
        "results": [],
    }
    first = repository.save([], [], report, fixture_name="first.json")
    second = repository.save([], [], report, fixture_name="second.json")

    runs = repository.list_runs(limit=10)

    assert len(runs) == 2
    assert {item["trace_run_id"] for item in runs} == {first, second}
    assert all("trace" not in item and "checks" not in item for item in runs)
    assert repository.get_run("missing") is None
