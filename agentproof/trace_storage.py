"""SQLite history for deterministic trace evaluations."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteTraceRepository:
    """Persist trace checks and their evidence in the local AgentProof database."""

    def __init__(self, path: str | Path = "agentproof.sqlite3") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_evaluations (
                    trace_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    score REAL NOT NULL,
                    summary_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    results_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_trace_evaluations_created "
                "ON trace_evaluations(created_at DESC)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)

    def save_evaluation(
        self,
        trace: list[dict[str, Any]],
        checks: list[dict[str, Any]],
        report: dict[str, Any],
    ) -> str:
        """Store the input trace, checks, and complete result evidence; return its ID."""
        trace_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO trace_evaluations
                (trace_id, created_at, passed, score, summary_json, trace_json, checks_json, results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    created_at,
                    int(bool(report.get("passed"))),
                    float(report.get("score", 0.0)),
                    self._json(report.get("summary", {})),
                    self._json(trace),
                    self._json(checks),
                    self._json(report.get("results", [])),
                ),
            )
        return trace_id

    def list_evaluations(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """List recent trace evaluations without returning full trace payloads."""
        bounded_limit = max(1, min(limit, 200))
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT trace_id, created_at, passed, score, summary_json
                FROM trace_evaluations
                ORDER BY created_at DESC, trace_id DESC LIMIT ? OFFSET ?
                """,
                (bounded_limit, max(0, offset)),
            ).fetchall()
        return [
            {
                "trace_id": row["trace_id"],
                "created_at": row["created_at"],
                "passed": bool(row["passed"]),
                "score": row["score"],
                "summary": json.loads(row["summary_json"]),
            }
            for row in rows
        ]

    def get_evaluation(self, trace_id: str) -> dict[str, Any] | None:
        """Return a trace evaluation with the original inputs and per-check evidence."""
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM trace_evaluations WHERE trace_id = ?", (trace_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "trace_id": row["trace_id"],
            "created_at": row["created_at"],
            "passed": bool(row["passed"]),
            "score": row["score"],
            "summary": json.loads(row["summary_json"]),
            "trace": json.loads(row["trace_json"]),
            "checks": json.loads(row["checks_json"]),
            "results": json.loads(row["results_json"]),
        }
