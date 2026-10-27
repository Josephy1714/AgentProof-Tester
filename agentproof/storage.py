"""SQLite-backed evaluation history with a replaceable repository boundary."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Protocol

from agentproof.models import EvaluationRun, TestResult


class RunRepository(Protocol):
    def save_run(self, run: EvaluationRun, *, provider: str | None = None, model: str | None = None) -> None: ...
    def get_run(self, run_id: str) -> EvaluationRun | None: ...
    def list_runs(self, limit: int = 50, offset: int = 0, suite: str | None = None, model: str | None = None) -> list[dict[str, Any]]: ...
    def get_test_results(self, run_id: str) -> list[dict[str, Any]]: ...
    def latest(self, suite: str | None = None) -> EvaluationRun | None: ...
    def previous(self, run_id: str, suite: str | None = None) -> EvaluationRun | None: ...


class SQLiteRunRepository:
    """Small local repository. JSON columns keep model outputs auditable and portable."""

    def __init__(self, path: str | Path = "agentproof.sqlite3") -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if self.path != ":memory:" else None
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
            CREATE TABLE IF NOT EXISTS evaluation_runs (
                run_id TEXT PRIMARY KEY, suite_name TEXT NOT NULL, suite_version TEXT NOT NULL,
                config_fingerprint TEXT NOT NULL, adapter_name TEXT NOT NULL, simulated INTEGER NOT NULL,
                provider TEXT, model TEXT, started_at TEXT NOT NULL, duration_ms REAL NOT NULL,
                score REAL NOT NULL, summary_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
                test_id TEXT NOT NULL, status TEXT NOT NULL, score REAL NOT NULL, duration_ms REAL NOT NULL,
                assertions_json TEXT NOT NULL, output_json TEXT, error_type TEXT, error_message TEXT, category TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_runs_started ON evaluation_runs(started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_runs_suite ON evaluation_runs(suite_name);
            CREATE INDEX IF NOT EXISTS idx_runs_model ON evaluation_runs(model);
            CREATE INDEX IF NOT EXISTS idx_results_run ON test_results(run_id);
            """
            )

    @staticmethod
    def _json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)

    def save_run(self, run: EvaluationRun, *, provider: str | None = None, model: str | None = None) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM test_results WHERE run_id=?", (run.run_id,))
            db.execute(
                """INSERT OR REPLACE INTO evaluation_runs
                (run_id,suite_name,suite_version,config_fingerprint,adapter_name,simulated,provider,model,started_at,duration_ms,score,summary_json,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run.run_id,
                    run.suite_name,
                    run.suite_version,
                    run.config_fingerprint,
                    run.adapter_name,
                    int(run.simulated),
                    provider,
                    model,
                    run.started_at,
                    run.duration_ms,
                    run.score,
                    self._json(run.summary),
                    run.started_at,
                ),
            )
            for result in run.results:
                db.execute(
                    """INSERT INTO test_results
                    (run_id,test_id,status,score,duration_ms,assertions_json,output_json,error_type,error_message,category)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        run.run_id,
                        result.test_id,
                        result.status.value,
                        result.score,
                        result.duration_ms,
                        self._json([
                            a.__dict__ if hasattr(a, "__dict__") else {
                                "assertion_type": a.assertion_type,
                                "passed": a.passed,
                                "message": a.message,
                                "expected": a.expected,
                                "actual": a.actual,
                            }
                            for a in result.assertion_results
                        ]),
                        self._json(result.output),
                        result.error_type,
                        result.error_message,
                        result.category,
                    ),
                )

    def _row_to_run(self, row: sqlite3.Row) -> EvaluationRun:
        results = tuple(
            self._row_to_result(r)
            for r in self._connect().execute(
                "SELECT * FROM test_results WHERE run_id=? ORDER BY id", (row["run_id"],)
            )
        )
        return EvaluationRun(
            row["run_id"],
            row["suite_name"],
            row["suite_version"],
            row["config_fingerprint"],
            row["adapter_name"],
            bool(row["simulated"]),
            row["started_at"],
            row["duration_ms"],
            results,
            row["score"],
            json.loads(row["summary_json"]),
        )

    def _row_to_result(self, row: sqlite3.Row) -> TestResult:
        from agentproof.models import AssertionResult, TestStatus

        assertions = tuple(AssertionResult(**a) for a in json.loads(row["assertions_json"]))
        return TestResult(
            row["test_id"],
            TestStatus(row["status"]),
            row["score"],
            row["duration_ms"],
            assertions,
            json.loads(row["output_json"]) if row["output_json"] else None,
            row["error_type"],
            row["error_message"],
            row["category"],
        )

    def get_run(self, run_id: str) -> EvaluationRun | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM evaluation_runs WHERE run_id=?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        suite: str | None = None,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM evaluation_runs WHERE 1=1"
        params: list[Any] = []
        if suite:
            sql += " AND suite_name=?"
            params.append(suite)
        if model:
            sql += " AND model=?"
            params.append(model)
        sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params += [max(1, min(limit, 200)), max(0, offset)]
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [dict(r, summary=json.loads(r["summary_json"])) for r in rows]

    def get_test_results(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM test_results WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return [
            dict(
                r,
                assertions=json.loads(r["assertions_json"]),
                output=json.loads(r["output_json"]) if r["output_json"] else None,
            )
            for r in rows
        ]

    def latest(self, suite: str | None = None) -> EvaluationRun | None:
        runs = self.list_runs(1, 0, suite)
        return self.get_run(runs[0]["run_id"]) if runs else None

    def previous(self, run_id: str, suite: str | None = None) -> EvaluationRun | None:
        current = self.get_run(run_id)
        if not current:
            return None
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM evaluation_runs WHERE suite_name=? AND started_at<? ORDER BY started_at DESC LIMIT 1",
                (suite or current.suite_name, current.started_at),
            ).fetchone()
        return self._row_to_run(row) if row else None
