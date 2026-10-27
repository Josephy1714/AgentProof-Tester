from __future__ import annotations

import json
from pathlib import Path

from agentproof.cli import main


def test_trace_eval_command_writes_report_and_returns_success(tmp_path: Path) -> None:
    fixture = tmp_path / "trace.json"
    report = tmp_path / "report.json"
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

    exit_code = main(["trace-eval", str(fixture), "--report", str(report), "--db", str(tmp_path / "history.sqlite3")])

    assert exit_code == 0
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["passed"] is True
    assert saved["summary"] == {"total": 2, "passed": 2, "failed": 0}


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

    assert main(["trace-eval", str(fixture), "--report", str(report), "--db", str(tmp_path / "history.sqlite3")]) == 1
    saved = json.loads(report.read_text(encoding="utf-8"))
    assert saved["passed"] is False


def test_trace_eval_rejects_invalid_fixture_shape(tmp_path: Path) -> None:
    fixture = tmp_path / "trace.json"
    fixture.write_text(json.dumps({"trace": "not-an-array", "checks": []}), encoding="utf-8")

    assert main(["trace-eval", str(fixture), "--report", str(tmp_path / "report.json"), "--db", str(tmp_path / "history.sqlite3")]) == 2



def test_trace_eval_persists_history_and_trace_show_returns_evidence(tmp_path: Path, capsys: object) -> None:
    fixture = tmp_path / "trace.json"
    db = tmp_path / "history.sqlite3"
    fixture.write_text(
        json.dumps(
            {
                "trace": [{"event_type": "assistant_message", "content": "Hello there"}],
                "checks": [{"type": "final_answer_contains", "value": "Hello"}],
            }
        ),
        encoding="utf-8",
    )

    assert main(["trace-eval", str(fixture), "--db", str(db)]) == 0
    output = main(["trace-runs", "--db", str(db)])
    assert output == 0
    history_text = capsys.readouterr().out
    history = json.loads(history_text)
    run_id = history[0]["trace_run_id"]

    assert main(["trace-show", run_id, "--db", str(db)]) == 0
    detail_text = capsys.readouterr().out
    detail = json.loads(detail_text)
    assert detail["trace_run_id"] == run_id
    assert detail["report"]["passed"] is True
    assert detail["trace"][0]["content"] == "Hello there"
