"""Analytics derived only from persisted evaluation history."""
from __future__ import annotations
from collections import defaultdict
from typing import Any
from agentproof.storage import SQLiteRunRepository


def overview(repo: SQLiteRunRepository) -> dict[str, Any]:
    runs = repo.list_runs(200)
    if not runs:
        return {"total_runs":0,"total_tests":0,"average_score":0.0,"latest_score":None,"pass_rate":0.0,"failure_rate":0.0,"error_rate":0.0,"regressions":0}
    totals=defaultdict(int)
    for r in runs:
        for k,v in r["summary"].items(): totals[k]+=v
    total=totals["passed"]+totals["failed"]+totals["error"]+totals["timeout"]+totals["skipped"]
    return {"total_runs":len(runs),"total_tests":total,"average_score":sum(r["score"] for r in runs)/len(runs),"latest_score":runs[0]["score"],"pass_rate":totals["passed"]/total if total else 0.0,"failure_rate":totals["failed"]/total if total else 0.0,"error_rate":(totals["error"]+totals["timeout"])/total if total else 0.0,"regressions":0}


def trends(repo: SQLiteRunRepository, limit: int = 50) -> list[dict[str, Any]]:
    runs=repo.list_runs(limit)
    return [{"run_id":r["run_id"],"timestamp":r["started_at"],"suite":r["suite_name"],"score":r["score"],"tests":sum(r["summary"].values()),"passed":r["summary"].get("passed",0),"failed":r["summary"].get("failed",0),"errors":r["summary"].get("error",0)+r["summary"].get("timeout",0)} for r in reversed(runs)]


def group_by(repo: SQLiteRunRepository, field: str) -> list[dict[str, Any]]:
    rows=repo.list_runs(200); groups: dict[str,list[dict[str,Any]]]=defaultdict(list)
    for r in rows: groups[str(r.get(field) or "unknown")].append(r)
    return [{"name":name,"runs":len(items),"average_score":sum(x["score"] for x in items)/len(items),"pass_rate":sum(x["summary"].get("passed",0) for x in items)/max(1,sum(sum(x["summary"].values()) for x in items))} for name,items in sorted(groups.items())]
