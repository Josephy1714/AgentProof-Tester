from __future__ import annotations

from typing import Any

from agentproof import tool_evaluation


def _execution(*, completed: bool = True) -> dict[str, Any]:
    return {
        "completed": completed,
        "stop_reason": None if completed else "max_turns",
        "final_answer": "The answer is 42.",
        "model": "test-model",
        "usage": {"total_tokens": 10},
        "turns": 2,
        "trace": [
            {"event_type": "tool_call", "name": "lookup", "arguments": {"id": 42}},
            {"event_type": "tool_result", "name": "lookup", "output": {"value": 42}},
            {"event_type": "assistant_message", "content": "The answer is 42."},
        ],
    }


def test_run_and_evaluate_tool_agent_returns_trace_evidence(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(tool_evaluation, "run_tool_agent", lambda *args, **kwargs: _execution())
    report = tool_evaluation.run_and_evaluate_tool_agent(
        [{"role": "user", "content": "Find 42"}],
        [{"type": "function", "function": {"name": "lookup"}}],
        {"lookup": lambda args: args},
        [
            {"type": "tool_called", "name": "lookup"},
            {"type": "tool_argument_equals", "name": "lookup", "path": "id", "expected": 42},
            {"type": "final_answer_contains", "value": "42"},
        ],
        model="test-model",
        api_key="test-secret",
    )

    assert report["passed"] is True
    assert report["execution_completed"] is True
    assert report["evaluation"]["summary"] == {"total": 3, "passed": 3, "failed": 0}
    assert len(report["trace"]) == 3
    assert "test-secret" not in str(report)


def test_incomplete_execution_fails_even_if_trace_checks_pass(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        tool_evaluation, "run_tool_agent", lambda *args, **kwargs: _execution(completed=False)
    )
    report = tool_evaluation.run_and_evaluate_tool_agent(
        [{"role": "user", "content": "Find 42"}],
        [{"type": "function", "function": {"name": "lookup"}}],
        {"lookup": lambda args: args},
        [{"type": "tool_called", "name": "lookup"}],
        model="test-model",
        api_key="test-secret",
    )

    assert report["evaluation"]["passed"] is True
    assert report["execution_completed"] is False
    assert report["stop_reason"] == "max_turns"
    assert report["passed"] is False
