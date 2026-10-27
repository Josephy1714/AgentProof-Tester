"""Deterministic evaluation helpers for recorded agent/tool traces.

A trace is a sequence of mappings with an event_type and optional fields:
name, arguments, output, and content. Supported event types are tool_call,
tool_result, and assistant_message.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SUPPORTED_TRACE_CHECKS = {
    "tool_called",
    "tool_not_called",
    "tool_call_count",
    "max_tool_calls",
    "tool_sequence",
    "tool_argument_equals",
    "tool_result_contains",
    "final_answer_contains",
}


def _path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, Mapping):
            if part not in current:
                raise KeyError(part)
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise KeyError(part)
    return current


def _tool_calls(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [event for event in events if event.get("event_type") == "tool_call"]


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return expected in actual
    if isinstance(actual, (list, tuple, set, dict)):
        return expected in actual
    return False


def evaluate_trace(
    events: Sequence[Mapping[str, Any]],
    checks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate deterministic checks against a recorded trace.

    Raises ValueError for malformed or unsupported checks. A failed check is
    returned as evidence; it does not abort evaluation of later checks.
    """
    calls = _tool_calls(events)
    results: list[dict[str, Any]] = []

    for index, check in enumerate(checks):
        check_type = check.get("type")
        if not isinstance(check_type, str) or check_type not in SUPPORTED_TRACE_CHECKS:
            raise ValueError(f"Unsupported trace check at index {index}: {check_type!r}")

        name = check.get("name")
        expected = check.get("expected")
        actual: Any = None
        passed = False
        message = "Trace check did not match"

        if check_type == "tool_called":
            if not isinstance(name, str) or not name:
                raise ValueError("tool_called requires a non-empty name")
            actual = any(event.get("name") == name for event in calls)
            passed = actual
            message = "Tool was called" if passed else f"Tool {name!r} was not called"

        elif check_type == "tool_not_called":
            if not isinstance(name, str) or not name:
                raise ValueError("tool_not_called requires a non-empty name")
            actual = any(event.get("name") == name for event in calls)
            passed = not actual
            message = f"Tool {name!r} was not called" if passed else f"Forbidden tool {name!r} was called"

        elif check_type == "tool_call_count":
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
                raise ValueError("tool_call_count requires a non-negative integer expected value")
            actual = len(calls)
            passed = actual == expected
            message = f"Observed {actual} tool calls; expected exactly {expected}"

        elif check_type == "max_tool_calls":
            if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
                raise ValueError("max_tool_calls requires a non-negative integer expected value")
            actual = len(calls)
            passed = actual <= expected
            message = f"Observed {actual} tool calls; maximum allowed is {expected}"

        elif check_type == "tool_sequence":
            if not isinstance(expected, list) or any(not isinstance(item, str) for item in expected):
                raise ValueError("tool_sequence requires expected to be a list of tool names")
            observed = [str(event.get("name", "")) for event in calls]
            cursor = 0
            for tool_name in observed:
                if cursor < len(expected) and tool_name == expected[cursor]:
                    cursor += 1
            actual = observed
            passed = cursor == len(expected)
            message = "Expected tool sequence observed in order" if passed else "Expected tool sequence was not observed in order"

        elif check_type == "tool_argument_equals":
            if not isinstance(name, str) or not name:
                raise ValueError("tool_argument_equals requires a non-empty name")
            path = check.get("path")
            if not isinstance(path, str) or not path:
                raise ValueError("tool_argument_equals requires a non-empty path")
            matching = next((event for event in calls if event.get("name") == name), None)
            try:
                actual = _path(matching.get("arguments"), path) if matching is not None else None
                passed = matching is not None and actual == expected
            except (KeyError, IndexError, TypeError):
                passed = False
            message = "Tool argument matched" if passed else f"Tool {name!r} argument {path!r} did not match"

        elif check_type == "tool_result_contains":
            if not isinstance(name, str) or not name:
                raise ValueError("tool_result_contains requires a non-empty name")
            matching_result = next(
                (event for event in reversed(events)
                 if event.get("event_type") == "tool_result" and event.get("name") == name),
                None,
            )
            actual = matching_result.get("output") if matching_result is not None else None
            if actual is None and matching_result is not None:
                actual = matching_result.get("content")
            passed = _contains(actual, check.get("value", expected))
            message = "Tool result contained expected value" if passed else f"Tool result for {name!r} did not contain expected value"

        elif check_type == "final_answer_contains":
            final_event = next(
                (event for event in reversed(events) if event.get("event_type") == "assistant_message"),
                None,
            )
            actual = final_event.get("content") if final_event is not None else None
            needle = check.get("value", expected)
            if not isinstance(needle, str):
                raise ValueError("final_answer_contains requires a string expected value")
            passed = isinstance(actual, str) and needle in actual
            message = "Final answer contained expected text" if passed else "Final answer did not contain expected text"

        results.append({
            "index": index,
            "type": check_type,
            "passed": passed,
            "message": message,
            "expected": check.get("value", expected),
            "actual": actual,
        })

    total = len(results)
    passed_count = sum(bool(result["passed"]) for result in results)
    return {
        "passed": passed_count == total,
        "score": passed_count / total if total else 1.0,
        "summary": {"total": total, "passed": passed_count, "failed": total - passed_count},
        "results": results,
    }
