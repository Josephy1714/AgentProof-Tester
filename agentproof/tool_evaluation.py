"""Run a bounded tool-calling agent and evaluate its captured trace."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from agentproof.tool_execution import ToolHandler, run_tool_agent
from agentproof.traces import evaluate_trace


def run_and_evaluate_tool_agent(
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    handlers: Mapping[str, ToolHandler],
    checks: Sequence[Mapping[str, Any]],
    *,
    model: str,
    base_url: str = "https://api.openai.com/v1",
    api_key: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    request_timeout: float = 30.0,
    max_turns: int = 8,
) -> dict[str, Any]:
    """Execute a bounded tool conversation and evaluate its trace.

    A run passes only if the provider conversation completes and every trace
    check passes. A run that reaches the turn limit is marked failed even if
    the checks that could be evaluated against its partial trace pass.
    """
    execution = run_tool_agent(
        messages,
        tools,
        handlers,
        model=model,
        base_url=base_url,
        api_key=api_key,
        api_key_env=api_key_env,
        request_timeout=request_timeout,
        max_turns=max_turns,
    )
    evaluation = evaluate_trace(execution["trace"], checks)
    completed = execution["completed"] is True
    return {
        "passed": completed and evaluation["passed"],
        "execution_completed": completed,
        "stop_reason": execution.get("stop_reason"),
        "final_answer": execution["final_answer"],
        "model": execution["model"],
        "usage": execution["usage"],
        "turns": execution["turns"],
        "trace": execution["trace"],
        "evaluation": evaluation,
    }
