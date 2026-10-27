"""Analytics derived only from persisted evaluation history."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from agentproof.storage import RunRepository


def overview(repo: RunRepository) -> dict[str, Any]:
    runs = repo.list_runs(200)
    if not runs:
        return {
            "total_runs": 0,
            "total_tests": 0,
            "average_score": 0.0,
            "latest_score": None,
            "pass_rate": 0.0,
            "failure_rate": 0.0,
            "error_rate": 0.0,
            "regressions": 0,
        }

    totals: dict[str, int] = defaultdict(int)
    for run in runs:
        for key, value in run["summary"].items():
            totals[key] += value

    total = totals["passed"] + totals["failed"] + totals["error"] + totals["timeout"] + totals["skipped"]
    return {
        "total_runs": len(runs),
        "total_tests": total,
        "average_score": sum(run["score"] for run in runs) / len(runs),
        "latest_score": runs[0]["score"],
        "pass_rate": totals["passed"] / total if total else 0.0,
        "failure_rate": totals["failed"] / total if total else 0.0,
        "error_rate": (totals["error"] + totals["timeout"]) / total if total else 0.0,
        "regressions": 0,
    }


def trends(repo: SQLiteRunRepository, limit: int = 50) -> list[dict[str, Any]]:
    runs = repo.list_runs(limit)
    return [
        {
            "run_id": run["run_id"],
            "timestamp": run["started_at"],
            "suite": run["suite_name"],
            "score": run["score"],
            "tests": sum(run["summary"].values()),
            "passed": run["summary"].get("passed", 0),
            "failed": run["summary"].get("failed", 0),
            "errors": run["summary"].get("error", 0) + run["summary"].get("timeout", 0),
        }
        for run in reversed(runs)
    ]


def group_by(repo: SQLiteRunRepository, field: str) -> list[dict[str, Any]]:
    rows = repo.list_runs(200)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in rows:
        groups[str(run.get(field) or "unknown")].append(run)

    return [
        {
            "name": name,
            "runs": len(items),
            "average_score": sum(item["score"] for item in items) / len(items),
            "pass_rate": sum(item["summary"].get("passed", 0) for item in items)
            / max(1, sum(sum(item["summary"].values()) for item in items)),
        }
        for name, items in sorted(groups.items())
    ]
