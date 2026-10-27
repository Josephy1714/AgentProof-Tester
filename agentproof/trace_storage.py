"""SQLite persistence for deterministic trace evaluation runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class SQLiteTraceRunRepository:
    """Persist trace inputs and evidence in the same local database as run history."""

    def __init__(self, path: str | Path = "agentproof.sqlite3") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_evaluations (
                    trace_run_id TEXT PRIMARY KEY,
                    fixture_name TEXT,
                    created_at TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    score REAL NOT NULL,
                    trace_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_trace_evaluations_created "
                "ON trace_evaluations(created_at DESC)"
            )

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, default=str)

    def save(
        self,
        trace: list[dict[str, Any]],
        checks: list[dict[str, Any]],
        report: dict[str, Any],
        *,
        fixture_name: str | None = None,
    ) -> str:
        """Save one evaluation and return its stable run identifier."""
        run_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO trace_evaluations
                (trace_run_id, fixture_name, created_at, passed, score,
                 trace_json, checks_json, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    fixture_name,
                    created_at,
                    int(bool(report.get("passed"))),
                    float(report.get("score", 0.0)),
                    self._dump(trace),
                    self._dump(checks),
                    self._dump(report),
                ),
            )
        return run_id

    def list_runs(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Return newest trace runs without their potentially large event payloads."""
        bounded_limit = max(1, min(limit, 200))
        bounded_offset = max(0, offset)
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT trace_run_id, fixture_name, created_at, passed, score,
                       report_json
                FROM trace_evaluations
                ORDER BY created_at DESC, trace_run_id DESC
                LIMIT ? OFFSET ?
                """,
                (bounded_limit, bounded_offset),
            ).fetchall()
        return [
            {
                "trace_run_id": row["trace_run_id"],
                "fixture_name": row["fixture_name"],
                "created_at": row["created_at"],
                "passed": bool(row["passed"]),
                "score": row["score"],
                "summary": json.loads(row["report_json"])["summary"],
            }
            for row in rows
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Return the trace, checks, and complete evidence report for a run."""
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM trace_evaluations WHERE trace_run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "trace_run_id": row["trace_run_id"],
            "fixture_name": row["fixture_name"],
            "created_at": row["created_at"],
            "passed": bool(row["passed"]),
            "score": row["score"],
            "trace": json.loads(row["trace_json"]),
            "checks": json.loads(row["checks_json"]),
            "report": json.loads(row["report_json"]),
        }
