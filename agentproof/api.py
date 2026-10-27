"""Tiny stdlib HTTP API for the local dashboard and future hosted adapters."""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from agentproof.analytics import group_by, overview, trends
from agentproof.cloud_storage import SupabaseHostedStorage, SupabaseStorageError
from agentproof.regression import compare_runs
from agentproof.storage import RunRepository, SQLiteRunRepository
from agentproof.trace_storage import SQLiteTraceRepository


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        expected_token = os.environ.get("AGENTPROOF_API_TOKEN")
        if expected_token:
            authorization = self.headers.get("Authorization", "")
            scheme, _, supplied_token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not supplied_token or not hmac.compare_digest(supplied_token, expected_token):
                self._send({"error": "Unauthorized"}, 401)
                return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        q = parse_qs(parsed.query)
        database = os.environ.get("AGENTPROOF_DB", "agentproof.sqlite3")
        storage_mode = os.environ.get("AGENTPROOF_STORAGE", "sqlite").lower()
        try:
            repo: RunRepository
            if storage_mode == "supabase":
                repo = SupabaseHostedStorage()
            elif storage_mode == "sqlite":
                repo = SQLiteRunRepository(database)
            else:
                self._send({"error": "AGENTPROOF_STORAGE must be 'sqlite' or 'supabase'."}, 500)
                return
            if path == "/api/dashboard/overview":
                self._send(overview(repo))
                return
            if path == "/api/analytics/trends":
                self._send({"data": trends(repo, int(q.get("limit", ["50"])[0]))})
                return
            if path == "/api/analytics/models":
                self._send({"data": group_by(repo, "model")})
                return
            if path == "/api/analytics/suites":
                self._send({"data": group_by(repo, "suite_name")})
                return
            if path == "/api/runs":
                self._send({
                    "data": repo.list_runs(
                        int(q.get("limit", ["50"])[0]),
                        int(q.get("offset", ["0"])[0]),
                        q.get("suite", [None])[0],
                        q.get("model", [None])[0],
                    )
                })
                return
            if path == "/api/traces":
                storage_mode = os.environ.get("AGENTPROOF_STORAGE", "sqlite").lower()
                if storage_mode == "supabase":
                    trace_rows = SupabaseHostedStorage().list_trace_evaluations(
                        int(q.get("limit", ["20"])[0]),
                        int(q.get("offset", ["0"])[0]),
                    )
                    self._send({"data": [
                        {
                            "trace_id": row["trace_key"],
                            "created_at": row["evaluated_at"],
                            "passed": row["passed"],
                            "score": row["score"],
                            "summary": row["summary"],
                        } for row in trace_rows
                    ]})
                elif storage_mode == "sqlite":
                    trace_repo = SQLiteTraceRepository(database)
                    self._send({
                        "data": trace_repo.list_evaluations(
                            int(q.get("limit", ["20"])[0]),
                            int(q.get("offset", ["0"])[0]),
                        )
                    })
                else:
                    self._send({"error": "AGENTPROOF_STORAGE must be 'sqlite' or 'supabase'."}, 500)
                return
            if path.startswith("/api/traces/"):
                trace_id = path.removeprefix("/api/traces/")
                if not trace_id or "/" in trace_id:
                    self._send({"error": "Trace evaluation not found"}, 404)
                    return
                storage_mode = os.environ.get("AGENTPROOF_STORAGE", "sqlite").lower()
                if storage_mode == "supabase":
                    evaluation = SupabaseHostedStorage().get_trace_evaluation(trace_id)
                    if evaluation is not None:
                        evaluation["trace_id"] = evaluation.pop("trace_key")
                        evaluation["created_at"] = evaluation.pop("evaluated_at")
                elif storage_mode == "sqlite":
                    evaluation = SQLiteTraceRepository(database).get_evaluation(trace_id)
                else:
                    self._send({"error": "AGENTPROOF_STORAGE must be 'sqlite' or 'supabase'."}, 500)
                    return
                if evaluation is None:
                    self._send({"error": "Trace evaluation not found"}, 404)
                else:
                    self._send(evaluation)
                return
            if path.startswith("/api/runs/"):
                parts = path.split("/")
                run_id = parts[3] if len(parts) > 3 else ""
                run = repo.get_run(run_id)
                if not run:
                    self._send({"error": "Run not found"}, 404)
                    return
                if len(parts) > 4 and parts[4] == "regression":
                    previous = repo.previous(run_id)
                    self._send(
                        compare_runs(previous, run)
                        if previous
                        else {"comparable": False, "message": "No previous run for this suite."}
                    )
                    return
                data = run.to_dict()
                data["test_results"] = repo.get_test_results(run_id)
                self._send(data)
                return
            self._send({"name": "AgentProof API", "status": "ok"})
        except SupabaseStorageError as exc:
            self._send({"error": str(exc)}, 502)
        except (ValueError, TypeError) as exc:
            self._send({"error": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API; non-loopback binds require explicit bearer-token protection."""
    if host not in {"127.0.0.1", "::1", "localhost"} and not os.environ.get("AGENTPROOF_API_TOKEN"):
        raise RuntimeError(
            "Refusing to bind the AgentProof API to a non-loopback host without "
            "AGENTPROOF_API_TOKEN. Set a long random token or bind to 127.0.0.1."
        )
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
