from __future__ import annotations

import json
from pathlib import Path

from agentproof.cli import main
from agentproof.trace_storage import SQLiteTraceRepository


def test_trace_eval_command_writes_report_and_history(tmp_path: Path) -> None:
    fixture = tmp_path / "trace.json"
    report = tmp_path / "report.json"
    database = tmp_path / "history.sqlite3"
    fixture.write_text(
        json.dumps(
            {
                "trace": [
                    {"event_type": "tool_call", "name": "search", "arguments": {"query": "cats"}},
                    {"event_type": "assistant_message", "content": "Found cats."},
                ],
                "checks": [
                    {"type": "tool_called", "name": "search"},
                    {"type": "final_answer_contains", "value": "cats"},
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main([
        "trace-eval", str(fixture), "--report", str(report), "--db", str(database)
    ])

    assert exit_code == 0
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["passed"] is True
    assert saved["summary"] == {"total": 2, "passed": 2, "failed": 0}
    history = SQLiteTraceRepository(database).list_evaluations()
    assert len(history) == 1
    assert history[0]["passed"] is True


def test_trace_eval_command_returns_one_for_failed_checks(tmp_path: Path) -> None:
    fixture = tmp_path / "trace.json"
    report = tmp_path / "report.json"
    fixture.write_text(
        json.dumps(
            {
                "trace": [],
                "checks": [{"type": "tool_called", "name": "delete_file"}],
            }
        ),
        encoding="utf-8",
    )

    assert main([
        "trace-eval", str(fixture), "--report", str(report), "--no-history"
    ]) == 1
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["passed"] is False


def test_trace_eval_rejects_invalid_fixture_shape(tmp_path: Path) -> None:
    fixture = tmp_path / "trace.json"
    fixture.write_text(json.dumps({"trace": "not-an-array", "checks": []}), encoding="utf-8")

    assert main([
        "trace-eval", str(fixture), "--report", str(tmp_path / "report.json"), "--no-history"
    ]) == 2
