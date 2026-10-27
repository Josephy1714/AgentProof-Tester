"""Tiny stdlib HTTP API for the local dashboard and future hosted adapters."""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from agentproof.analytics import group_by, overview, trends
from agentproof.regression import compare_runs
from agentproof.storage import SQLiteRunRepository
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
        repo = SQLiteRunRepository(database)
        try:
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
                trace_repo = SQLiteTraceRepository(database)
                self._send({
                    "data": trace_repo.list_evaluations(
                        int(q.get("limit", ["20"])[0]),
                        int(q.get("offset", ["0"])[0]),
                    )
                })
                return
            if path.startswith("/api/traces/"):
                trace_id = path.removeprefix("/api/traces/")
                if not trace_id or "/" in trace_id:
                    self._send({"error": "Trace evaluation not found"}, 404)
                    return
                evaluation = SQLiteTraceRepository(database).get_evaluation(trace_id)
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
        except (ValueError, TypeError) as exc:
            self._send({"error": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
