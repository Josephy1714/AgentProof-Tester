"""Tiny stdlib HTTP API for the local dashboard and hosted Vercel deployment."""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agentproof.adapters import OpenAICompatibleAdapter, SimulatedAdapter
from agentproof.analytics import group_by, overview, trends
from agentproof.cloud_storage import SupabaseHostedStorage, SupabaseStorageError
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.regression import compare_runs
from agentproof.runner import run_suite
from agentproof.storage import SQLiteRunRepository
from agentproof.trace_storage import SQLiteTraceRepository


OPENROUTER_ALLOWED_MODELS = {
    "openrouter/free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-3.5-super-vl:free",
}


def _database_path() -> str:
    """Use explicit storage when configured; serverless filesystems are not persistent."""
    configured = os.environ.get("AGENTPROOF_DB")
    if configured:
        return configured
    if os.environ.get("VERCEL"):
        return "/tmp/agentproof.sqlite3"
    return "agentproof.sqlite3"


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_dashboard(self) -> None:
        dashboard = Path(__file__).resolve().parent.parent / "apps" / "web" / "index.html"
        try:
            body = dashboard.read_bytes()
        except OSError:
            self._send({"error": "Dashboard asset is missing from this deployment."}, 500)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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

        if path == "/":
            self._send_dashboard()
            return

        database = _database_path()
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

    def do_POST(self) -> None:
        expected_token = os.environ.get("AGENTPROOF_API_TOKEN")
        if expected_token:
            authorization = self.headers.get("Authorization", "")
            scheme, _, supplied_token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not supplied_token or not hmac.compare_digest(supplied_token, expected_token):
                self._send({"error": "Unauthorized"}, 401)
                return

        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/api/runs":
            self._send({"error": "Not found"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > 16384:
                self._send({"error": "Request body must be between 1 and 16384 bytes."}, 413)
                return
            raw = json.loads(self.rfile.read(content_length))
            if not isinstance(raw, dict):
                raise ValueError("Suite must be a JSON object.")
            provider = str(raw.get("provider", "simulated")).lower()
            if provider not in {"simulated", "openrouter"}:
                raise ValueError("Provider must be 'simulated' or 'openrouter'.")
            api_key = os.environ.get("OPENROUTER_API_KEY") if provider == "openrouter" else None
            requested_model = str(raw.get("model", "openrouter/free"))
            if provider == "openrouter" and requested_model not in OPENROUTER_ALLOWED_MODELS:
                raise ValueError("Unsupported live model. Choose openrouter/free or one of the approved free NVIDIA models.")
            if provider == "openrouter" and not api_key:
                self._send({
                    "error": "Live runs are not configured yet. Add OPENROUTER_API_KEY as a server-side Vercel environment secret, then redeploy."
                }, 503)
                return

            tests_raw = raw.get("tests")
            max_tests = 3 if provider == "openrouter" else 10
            if not isinstance(tests_raw, list) or not 1 <= len(tests_raw) <= max_tests:
                raise ValueError(f"Suite must contain between 1 and {max_tests} tests for this provider.")
            tests = []
            timeout_cap = 8.0 if provider == "openrouter" else 2.0
            for item in tests_raw:
                if not isinstance(item, dict):
                    raise ValueError("Each test must be a JSON object.")
                assertions_raw = item.get("assertions", [])
                if not isinstance(assertions_raw, list) or not 1 <= len(assertions_raw) <= 10:
                    raise ValueError("Each test must contain between 1 and 10 assertions.")
                test_input = item.get("input")
                if provider == "openrouter":
                    if not isinstance(test_input, dict) or not (
                        isinstance(test_input.get("prompt"), str)
                        or isinstance(test_input.get("messages"), list)
                    ):
                        raise ValueError("Real-model tests need input.prompt or input.messages.")
                    if isinstance(test_input.get("prompt"), str) and len(test_input["prompt"]) > 4000:
                        raise ValueError("Each live prompt must be 4000 characters or fewer.")
                tests.append(TestCase(
                    id=item["id"],
                    input=test_input,
                    assertions=tuple(AssertionSpec(**assertion) for assertion in assertions_raw),
                    category=item.get("category", "general"),
                    timeout_seconds=min(float(item.get("timeout_seconds", timeout_cap)), timeout_cap),
                    metadata=item.get("metadata", {}),
                ))
            suite = EvaluationSuite(
                name=str(raw.get("name", "Browser evaluation"))[:120],
                version=str(raw.get("version", "1.0"))[:40],
                tests=tuple(tests),
                schema_version=str(raw.get("schema_version", "1.0"))[:20],
                scoring_weights=raw.get("scoring_weights", {}),
                metadata=raw.get("metadata", {}),
            )
            if provider == "openrouter":
                # Only fixed free model IDs are allowed; callers cannot provide arbitrary URLs or paid model names.
                adapter = OpenAICompatibleAdapter(
                    model=requested_model,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    request_timeout=8.0,
                    max_tokens=128,
                )
                run = run_suite(
                    suite, adapter,
                    {"provider": "openrouter", "model": requested_model, "mode": "live"},
                )
                model = requested_model
            else:
                run = run_suite(suite, SimulatedAdapter(), {"mode": "simulated"})
                model = "synthetic"
            repo = SQLiteRunRepository(_database_path())
            repo.save_run(run, provider=provider, model=model)
            self._send(run.to_dict(), 201)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OverflowError) as exc:
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
