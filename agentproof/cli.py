"""CLI for running evaluation suites with simulated or live adapters."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from agentproof.adapters import OpenAICompatibleAdapter, SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.runner import run_suite, write_json_report
from agentproof.validation import SuiteValidationError


def load_suite(path: str) -> EvaluationSuite:
    raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    tests = tuple(
        TestCase(
            item["id"],
            item.get("input"),
            tuple(AssertionSpec(**assertion) for assertion in item.get("assertions", [])),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentproof")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("suite")
    parser.add_argument("--report", default="agentproof-report.json")
    parser.add_argument(
        "--adapter",
        choices=["simulated", "openai-compatible"],
        default="simulated",
        help="Use deterministic fixtures or call a live OpenAI-compatible endpoint.",
    )
    parser.add_argument("--model", default=os.environ.get("AGENTPROOF_MODEL"))
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENTPROOF_BASE_URL", "https://api.openai.com/v1"),
        help="Provider API base URL (not the /chat/completions endpoint).",
    )
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the provider API key.",
    )
    parser.add_argument("--request-timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    try:
        suite = load_suite(args.suite)
        if args.adapter == "simulated":
            adapter = SimulatedAdapter()
            adapter_config: dict[str, Any] = {"mode": "simulated"}
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
            adapter_config = {
                "model": args.model,
                "base_url": args.base_url.rstrip("/"),
                "request_timeout": args.request_timeout,
            }
        run = run_suite(suite, adapter, adapter_config=adapter_config)
        write_json_report(run, args.report)
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        SuiteValidationError,
        RuntimeError,
    ) as exc:
        print(f"AgentProof error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Run: {run.run_id}\nScore: {run.score:.1%}\nResults: {run.summary}"
        f"\nSimulated: {run.simulated}\nReport: {args.report}"
    )
    return 1 if any(run.summary.get(key, 0) for key in ("failed", "error", "timeout")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
