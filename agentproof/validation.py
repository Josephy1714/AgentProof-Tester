"""Suite validation and canonical evaluation fingerprints."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict
from typing import Any

from agentproof.models import EvaluationSuite

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
SUPPORTED_ASSERTIONS = {"equals", "contains", "is_type", "numeric_tolerance", "regex", "has_key"}
TYPE_NAMES = {"string", "integer", "number", "boolean", "array", "object", "null"}

class SuiteValidationError(ValueError):
    """Raised when a suite cannot be evaluated safely."""

def _positive_finite(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise SuiteValidationError(f"{label} must be finite and greater than zero")

def validate_suite(suite: EvaluationSuite) -> None:
    if not suite.name.strip() or not suite.version.strip():
        raise SuiteValidationError("Suite name and version must not be empty")
    if suite.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SuiteValidationError(f"Unsupported schema_version: {suite.schema_version}")
    ids = [test.id for test in suite.tests]
    if any(not item.strip() for item in ids):
        raise SuiteValidationError("Test IDs must not be empty")
    if len(ids) != len(set(ids)):
        raise SuiteValidationError("Test IDs must be unique within a suite")
    for test in suite.tests:
        _positive_finite(test.timeout_seconds, f"timeout_seconds for {test.id}")
        if not test.assertions:
            raise SuiteValidationError(f"Test {test.id!r} has no assertions; execution-only tests are unsupported")
        for assertion in test.assertions:
            if assertion.type not in SUPPORTED_ASSERTIONS:
                raise SuiteValidationError(f"Unsupported assertion type {assertion.type!r}")
            if assertion.type == "is_type" and assertion.expected not in TYPE_NAMES:
                raise SuiteValidationError(f"Unsupported is_type target {assertion.expected!r}")
            if assertion.type == "regex":
                if not isinstance(assertion.pattern, str):
                    raise SuiteValidationError("Regex assertions require a string pattern")
                try:
                    re.compile(assertion.pattern)
                except re.error as exc:
                    raise SuiteValidationError(f"Invalid regex: {exc}") from exc
            if assertion.type == "numeric_tolerance":
                tol = assertion.tolerance
                if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or tol < 0:
                    raise SuiteValidationError("numeric_tolerance requires a finite, non-negative tolerance")
    for category, weight in suite.scoring_weights.items():
        if not category or isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise SuiteValidationError("Scoring weights must have categories and finite non-negative values")
    if suite.scoring_weights and sum(suite.scoring_weights.values()) <= 0:
        raise SuiteValidationError("At least one scoring weight must be greater than zero")

def _canonical(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonical(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise SuiteValidationError("Non-finite values cannot be fingerprinted")
    return value

def configuration_fingerprint(suite: EvaluationSuite, adapter_name: str, adapter_config: dict[str, Any] | None = None) -> str:
    payload = {"suite": _canonical(suite), "adapter_name": adapter_name, "adapter_config": _canonical(adapter_config or {})}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()
