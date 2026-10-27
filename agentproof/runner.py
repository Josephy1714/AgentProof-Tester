"""Evaluation runner with per-test failure isolation and explicit simulation metadata."""
from __future__ import annotations
import json, queue, threading, time, uuid
from datetime import datetime, timezone
from typing import Any
from agentproof.adapters.base import AgentAdapter
from agentproof.assertions import evaluate_assertion
from agentproof.models import EvaluationRun, EvaluationSuite, TestResult, TestStatus
from agentproof.validation import configuration_fingerprint, validate_suite

def _invoke(adapter: AgentAdapter, payload: Any, timeout: float) -> Any:
    result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
    def target() -> None:
        try: result_queue.put((True, adapter.invoke(payload)))
        except Exception as exc: result_queue.put((False, exc))
    worker = threading.Thread(target=target, daemon=True, name="agentproof-adapter")
    worker.start(); worker.join(timeout)
    if worker.is_alive(): raise TimeoutError(f"Adapter exceeded {timeout:g}s timeout")
    ok, value = result_queue.get_nowait()
    if not ok: raise value
    return value

def run_suite(suite: EvaluationSuite, adapter: AgentAdapter, adapter_config: dict[str, Any] | None = None) -> EvaluationRun:
    validate_suite(suite)
    start = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    fingerprint = configuration_fingerprint(suite, adapter.name, adapter_config)
    results: list[TestResult] = []
    for test in suite.tests:
        test_start = time.perf_counter()
        try: output = _invoke(adapter, test.input, test.timeout_seconds)
        except TimeoutError as exc:
            results.append(TestResult(test.id, TestStatus.TIMEOUT, 0.0, (time.perf_counter()-test_start)*1000, error_type="TimeoutError", error_message=str(exc), category=test.category)); continue
        except Exception as exc:
            results.append(TestResult(test.id, TestStatus.ERROR, 0.0, (time.perf_counter()-test_start)*1000, error_type=type(exc).__name__, error_message=str(exc), category=test.category)); continue
        assertions = tuple(evaluate_assertion(spec, output) for spec in test.assertions)
        score = sum(item.passed for item in assertions) / len(assertions)
        status = TestStatus.PASSED if all(item.passed for item in assertions) else TestStatus.FAILED
        results.append(TestResult(test.id, status, score, (time.perf_counter()-test_start)*1000, assertions, output, category=test.category))
    duration = (time.perf_counter()-start)*1000
    score = sum(item.score for item in results)/len(results) if results else 0.0
    summary = {status.value: sum(item.status == status for item in results) for status in TestStatus}
    return EvaluationRun(uuid.uuid4().hex, suite.name, suite.version, fingerprint, adapter.name, adapter.is_simulated, started_at, duration, tuple(results), score, summary)

def write_json_report(run: EvaluationRun, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(run.to_dict(), handle, indent=2, ensure_ascii=False, default=str, allow_nan=False)
        handle.write("\n")
