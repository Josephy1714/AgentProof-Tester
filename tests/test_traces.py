from __future__ import annotations

import pytest

from agentproof.traces import evaluate_trace


@pytest.fixture
def trace() -> list[dict[str, object]]:
    return [
        {"event_type": "assistant_message", "content": "I will look that up."},
        {"event_type": "tool_call", "name": "search", "arguments": {"query": "weather", "options": {"limit": 3}}},
        {"event_type": "tool_result", "name": "search", "output": {"results": ["sunny", "windy"]}},
        {"event_type": "tool_call", "name": "weather", "arguments": {"city": "Nairobi"}},
        {"event_type": "tool_result", "name": "weather", "output": "sunny, 24 C"},
        {"event_type": "assistant_message", "content": "Nairobi is sunny at 24 C."},
    ]


def test_trace_checks_pass_and_return_evidence(trace: list[dict[str, object]]) -> None:
    result = evaluate_trace(trace, [
        {"type": "tool_called", "name": "search"},
        {"type": "tool_not_called", "name": "delete_file"},
        {"type": "tool_call_count", "expected": 2},
        {"type": "max_tool_calls", "expected": 2},
        {"type": "tool_sequence", "expected": ["search", "weather"]},
        {"type": "tool_argument_equals", "name": "search", "path": "options.limit", "expected": 3},
        {"type": "tool_result_contains", "name": "weather", "value": "24 C"},
        {"type": "final_answer_contains", "value": "Nairobi"},
    ])
    assert result["passed"] is True
    assert result["summary"] == {"total": 8, "passed": 8, "failed": 0}


def test_trace_failures_are_reported_not_raised(trace: list[dict[str, object]]) -> None:
    result = evaluate_trace(trace, [
        {"type": "tool_not_called", "name": "search"},
        {"type": "max_tool_calls", "expected": 1},
        {"type": "tool_argument_equals", "name": "search", "path": "missing.key", "expected": "x"},
    ])
    assert result["passed"] is False
    assert result["summary"]["failed"] == 3
    assert all(item["message"] for item in result["results"])


def test_invalid_check_is_rejected(trace: list[dict[str, object]]) -> None:
    with pytest.raises(ValueError, match="Unsupported trace check"):
        evaluate_trace(trace, [{"type": "magic"}])


def test_empty_checks_are_a_pass_with_perfect_score() -> None:
    assert evaluate_trace([], []) == {
        "passed": True,
        "score": 1.0,
        "summary": {"total": 0, "passed": 0, "failed": 0},
        "results": [],
    }


def test_sequence_requires_order() -> None:
    result = evaluate_trace([
        {"event_type": "tool_call", "name": "weather"},
        {"event_type": "tool_call", "name": "search"},
    ], [{"type": "tool_sequence", "expected": ["search", "weather"]}])
    assert result["passed"] is False
