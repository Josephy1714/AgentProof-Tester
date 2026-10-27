"""CLI for running evaluations, trace checks, and inspecting local history."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from agentproof.adapters import AgentAdapter, OpenAICompatibleAdapter, SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.runner import run_suite, write_json_report
from agentproof.storage import SQLiteRunRepository
from agentproof.trace_storage import SQLiteTraceRepository
from agentproof.traces import evaluate_trace


def load_suite(path: str) -> EvaluationSuite:
    raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    tests = tuple(
        TestCase(
            item["id"],
            item.get("input"),
            tuple(AssertionSpec(**a) for a in item.get("assertions", [])),
            item.get("category", "general"),
            item.get("timeout_seconds", 10.0),
            item.get("metadata", {}),
        )
        for item in raw.get("tests", [])
    )
    return EvaluationSuite(
        raw.get("name", ""),
        raw.get("version", ""),
        tests,
        raw.get("schema_version", "1.0"),
        raw.get("scoring_weights", {}),
        raw.get("metadata", {}),
    )


def load_trace_fixture(path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load a trace fixture with 'trace' and 'checks' arrays."""
    raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Trace fixture must be a JSON object")
    events = raw.get("trace")
    checks = raw.get("checks")
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise ValueError("Trace fixture 'trace' must be an array of JSON objects")
    if not isinstance(checks, list) or not all(isinstance(item, dict) for item in checks):
        raise ValueError("Trace fixture 'checks' must be an array of JSON objects")
    return events, checks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentproof")
    p.add_argument("command", choices=["run", "runs", "run-show", "trace-eval"])
    p.add_argument(
        "suite", nargs="?", help="Suite path, run ID, or trace fixture path depending on command"
    )
    p.add_argument("--report", default="agentproof-report.json")
    p.add_argument("--db", default="agentproof.sqlite3")
    p.add_argument(
        "--no-history",
        action="store_true",
        help="Do not persist trace-eval inputs and evidence in the local SQLite history",
    )
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--adapter", choices=["simulated", "openai-compatible"], default="simulated")
    p.add_argument("--model", default=os.environ.get("AGENTPROOF_MODEL"))
    p.add_argument(
        "--base-url", default=os.environ.get("AGENTPROOF_BASE_URL", "https://api.openai.com/v1")
    )
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.add_argument("--request-timeout", type=float, default=30.0)
    args = p.parse_args(argv)

    if args.command == "trace-eval":
        if not args.suite:
            p.error("trace-eval requires a trace fixture path")
        try:
            events, checks = load_trace_fixture(args.suite)
            report = evaluate_trace(events, checks)
            Path(args.report).write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            trace_id = None
            if not args.no_history:
                trace_id = SQLiteTraceRepository(args.db).save_evaluation(events, checks, report)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            print(f"AgentProof error: {exc}", file=sys.stderr)
            return 2
        print(
            f"Trace evaluation: {'PASS' if report['passed'] else 'FAIL'}\n"
            f"Score: {report['score']:.1%}\n"
            f"Checks: {report['summary']}\n"
            f"Report: {args.report}"
            + (f"\nTrace history ID: {trace_id}\nHistory: {args.db}" if trace_id else "")
        )
        return 0 if report["passed"] else 1

    repo = SQLiteRunRepository(args.db)
    if args.command == "runs":
        print(json.dumps(repo.list_runs(args.limit), indent=2, default=str))
        return 0
    if args.command == "run-show":
        if not args.suite:
            p.error("run-show requires a run id")
        run = repo.get_run(args.suite)
        if not run:
            print("Run not found", file=sys.stderr)
            return 2
        print(json.dumps(run.to_dict(), indent=2, default=str))
        return 0
    if not args.suite:
        p.error("run requires a suite path")

    try:
        suite = load_suite(args.suite)
        if args.adapter == "simulated":
            adapter: AgentAdapter = SimulatedAdapter()
            config = {"mode": "simulated"}
            provider = "simulated"
            model = "synthetic"
        else:
            if not args.model:
                raise ValueError(
                    "The openai-compatible adapter requires --model or AGENTPROOF_MODEL."
                )
            adapter = OpenAICompatibleAdapter(
                model=args.model,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                request_timeout=args.request_timeout,
            )
            config = {
                "model": args.model,
                "base_url": args.base_url.rstrip("/"),
                "request_timeout": args.request_timeout,
            }
            provider = "openai-compatible"
            model = args.model
        run = run_suite(suite, adapter, adapter_config=config)
        repo.save_run(run, provider=provider, model=model)
        write_json_report(run, args.report)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"AgentProof error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Run: {run.run_id}\n"
        f"Score: {run.score:.1%}\n"
        f"Results: {run.summary}\n"
        f"Simulated: {run.simulated}\n"
        f"Report: {args.report}\n"
        f"History: {args.db}"
    )
    return 1 if any(run.summary.get(k, 0) for k in ("failed", "error", "timeout")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
