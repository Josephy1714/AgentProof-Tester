"""Opt-in Supabase REST storage using a verified user access token.

SQLite remains the default. This adapter never accepts a service-role key and
resolves the owner from Supabase Auth instead of trusting a caller-supplied ID.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from agentproof.models import EvaluationRun


class SupabaseStorageError(RuntimeError):
    """A hosted-storage request failed or the session could not be verified."""


class SupabaseHostedStorage:
    """Small user-scoped adapter for the AgentProof Supabase schema.

    Configure AGENTPROOF_SUPABASE_URL, AGENTPROOF_SUPABASE_ANON_KEY, and
    AGENTPROOF_SUPABASE_ACCESS_TOKEN. The access token must be a user JWT
    obtained from Supabase Auth; a publishable/anon key is not a user identity.
    """

    RUNS = "agentproof_evaluation_runs"
    TRACES = "agentproof_trace_evaluations"

    def __init__(
        self,
        project_url: str | None = None,
        publishable_key: str | None = None,
        access_token: str | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.project_url = (project_url or os.environ.get("AGENTPROOF_SUPABASE_URL", "")).rstrip("/")
        self.publishable_key = publishable_key or os.environ.get("AGENTPROOF_SUPABASE_ANON_KEY", "")
        self.access_token = access_token or os.environ.get("AGENTPROOF_SUPABASE_ACCESS_TOKEN", "")
        self.timeout = timeout
        parsed = urlparse(self.project_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("AGENTPROOF_SUPABASE_URL must be an HTTPS project URL.")
        if not self.publishable_key or not self.access_token:
            raise ValueError(
                "Set AGENTPROOF_SUPABASE_ANON_KEY and AGENTPROOF_SUPABASE_ACCESS_TOKEN."
            )
        self._user_id: str | None = None

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        prefer: str | None = None,
    ) -> Any:
        url = f"{self.project_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        body = None
        if payload is not None:
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code in (401, 403):
                raise SupabaseStorageError(
                    f"Supabase rejected the session or row-level policy ({exc.code})."
                ) from exc
            raise SupabaseStorageError(f"Supabase request failed ({exc.code}): {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SupabaseStorageError(f"Could not reach Supabase: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SupabaseStorageError("Supabase returned invalid JSON.") from exc

    @property
    def user_id(self) -> str:
        """Return the owner ID from a Supabase-verified access token."""
        if self._user_id is None:
            user = self._request("/auth/v1/user")
            if not isinstance(user, dict) or not isinstance(user.get("id"), str):
                raise SupabaseStorageError("Supabase Auth did not return a verified user ID.")
            self._user_id = user["id"]
        return self._user_id

    @staticmethod
    def _jsonable(value: Any) -> Any:
        return json.loads(json.dumps(value, default=lambda item: item.value if hasattr(item, "value") else str(item), allow_nan=False))

    def save_run(
        self,
        run: EvaluationRun,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        payload = run.to_dict()
        self._request(
            f"/rest/v1/{self.RUNS}",
            method="POST",
            payload={
                "user_id": self.user_id,
                "run_key": run.run_id,
                "suite_name": run.suite_name,
                "suite_version": run.suite_version,
                "provider": provider,
                "model": model,
                "score": run.score,
                "started_at": run.started_at,
                "payload": self._jsonable(payload),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def list_runs(
        self, limit: int = 50, offset: int = 0, suite: str | None = None, model: str | None = None
    ) -> list[dict[str, Any]]:
        query = {
            "select": "run_key,suite_name,suite_version,provider,model,score,started_at,created_at,payload",
            "user_id": f"eq.{self.user_id}",
            "order": "started_at.desc",
            "limit": str(max(1, min(int(limit), 200))),
            "offset": str(max(0, int(offset))),
        }
        if suite:
            query["suite_name"] = f"eq.{suite}"
        if model:
            query["model"] = f"eq.{model}"
        rows = self._request(f"/rest/v1/{self.RUNS}", query=query)
        if not isinstance(rows, list):
            raise SupabaseStorageError("Unexpected evaluation history response.")
        return rows

    def get_run(self, run_key: str) -> dict[str, Any] | None:
        rows = self._request(
            f"/rest/v1/{self.RUNS}",
            query={
                "select": "run_key,payload",
                "user_id": f"eq.{self.user_id}",
                "run_key": f"eq.{run_key}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list):
            raise SupabaseStorageError("Unexpected evaluation detail response.")
        return rows[0]["payload"] if rows else None

    def save_trace_evaluation(
        self,
        trace: list[dict[str, Any]],
        checks: list[dict[str, Any]],
        report: dict[str, Any],
        *,
        trace_key: str,
    ) -> None:
        self._request(
            f"/rest/v1/{self.TRACES}",
            method="POST",
            payload={
                "user_id": self.user_id,
                "trace_key": trace_key,
                "passed": bool(report.get("passed")),
                "score": float(report.get("score", 0.0)),
                "summary": self._jsonable(report.get("summary", {})),
                "trace": self._jsonable(trace),
                "checks": self._jsonable(checks),
                "results": self._jsonable(report.get("results", [])),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def list_trace_evaluations(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        rows = self._request(
            f"/rest/v1/{self.TRACES}",
            query={
                "select": "trace_key,passed,score,evaluated_at,summary",
                "user_id": f"eq.{self.user_id}",
                "order": "evaluated_at.desc",
                "limit": str(max(1, min(int(limit), 200))),
                "offset": str(max(0, int(offset))),
            },
        )
        if not isinstance(rows, list):
            raise SupabaseStorageError("Unexpected trace history response.")
        return rows

    def get_trace_evaluation(self, trace_key: str) -> dict[str, Any] | None:
        rows = self._request(
            f"/rest/v1/{self.TRACES}",
            query={
                "select": "trace_key,passed,score,evaluated_at,summary,trace,checks,results",
                "user_id": f"eq.{self.user_id}",
                "trace_key": f"eq.{trace_key}",
                "limit": "1",
            },
        )
        if not isinstance(rows, list):
            raise SupabaseStorageError("Unexpected trace detail response.")
        return rows[0] if rows else None
