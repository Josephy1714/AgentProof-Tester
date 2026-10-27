from __future__ import annotations

import json
from pathlib import Path

from agentproof.cli import main


def test_trace_eval_writes_report_and_returns_success(tmp_path: Path) -> None:
    fixture = Path("examples/trace_fixture.json")
    report_path = tmp_path / "trace-report.json"

    code = main(["trace-eval", str(fixture), "--report", str(report_path)])

    assert code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["summary"] == {"total": 4, "passed": 4, "failed": 0}


def test_trace_eval_returns_one_when_check_fails(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    report_path = tmp_path / "report.json"
    case_path.write_text(
        json.dumps({
            "trace": [{"event_type": "tool_call", "name": "search"}],
            "checks": [{"type": "tool_not_called", "name": "search"}],
        }),
        encoding="utf-8",
    )

    code = main(["trace-eval", str(case_path), "--report", str(report_path)])

    assert code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert report["summary"]["failed"] == 1


def test_trace_eval_rejects_invalid_document(tmp_path: Path) -> None:
    case_path = tmp_path / "bad.json"
    case_path.write_text(json.dumps({"trace": {}, "checks": []}), encoding="utf-8")

    assert main(["trace-eval", str(case_path), "--report", str(tmp_path / "out.json")]) == 2
