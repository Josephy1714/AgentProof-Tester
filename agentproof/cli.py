"""CLI for running JSON suites with the simulated adapter."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
from agentproof.adapters import SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.runner import run_suite, write_json_report
from agentproof.validation import SuiteValidationError

def load_suite(path: str) -> EvaluationSuite:
    raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    tests = tuple(TestCase(item["id"], item.get("input"), tuple(AssertionSpec(**a) for a in item.get("assertions", [])), item.get("category", "general"), item.get("timeout_seconds", 10.0), item.get("metadata", {})) for item in raw.get("tests", []))
    return EvaluationSuite(raw.get("name", ""), raw.get("version", ""), tests, raw.get("schema_version", "1.0"), raw.get("scoring_weights", {}), raw.get("metadata", {}))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentproof")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("suite")
    parser.add_argument("--report", default="agentproof-report.json")
    args = parser.parse_args(argv)
    try:
        run = run_suite(load_suite(args.suite), SimulatedAdapter())
        write_json_report(run, args.report)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, SuiteValidationError) as exc:
        print(f"AgentProof error: {exc}", file=sys.stderr); return 2
    print(f"Run: {run.run_id}\nScore: {run.score:.1%}\nResults: {run.summary}\nSimulated: {run.simulated}\nReport: {args.report}")
    return 1 if any(run.summary.get(key, 0) for key in ("failed", "error", "timeout")) else 0

if __name__ == "__main__":
    raise SystemExit(main())
