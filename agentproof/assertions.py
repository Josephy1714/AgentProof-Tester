"""Deterministic assertions; these do not claim semantic model judgment."""
from __future__ import annotations

import math
import re
from typing import Any

from agentproof.models import AssertionResult, AssertionSpec

def _path(value: Any, path: str | None) -> Any:
    if not path:
        return value
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"Missing path component {part!r}")
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise KeyError(f"Cannot resolve path component {part!r}")
    return current

def evaluate_assertion(spec: AssertionSpec, output: Any) -> AssertionResult:
    try:
        actual = _path(output, spec.path)
        if spec.type == "equals":
            passed = actual == spec.expected
        elif spec.type == "contains":
            passed = spec.value in actual
        elif spec.type == "is_type":
            types = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict, "null": type(None)}
            passed = isinstance(actual, types[spec.expected]) and not (spec.expected == "integer" and isinstance(actual, bool))
        elif spec.type == "numeric_tolerance":
            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
                passed = False
            elif isinstance(spec.expected, bool) or not isinstance(spec.expected, (int, float)) or not math.isfinite(spec.expected):
                raise ValueError("Expected value must be finite and numeric")
            else:
                passed = abs(actual - spec.expected) <= (spec.tolerance or 0)
        elif spec.type == "regex":
            passed = isinstance(actual, str) and re.search(spec.pattern or "", actual) is not None
        elif spec.type == "has_key":
            passed = isinstance(actual, dict) and spec.expected in actual
        else:
            raise ValueError(f"Unsupported assertion: {spec.type!r}")
        return AssertionResult(spec.type, passed, "Assertion passed" if passed else "Assertion did not match", spec.expected, actual)
    except (KeyError, IndexError, TypeError, ValueError, re.error) as exc:
        return AssertionResult(spec.type, False, f"Assertion could not be evaluated: {exc}", spec.expected, None)
