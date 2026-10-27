from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from agentproof import tool_execution


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def response(message: dict[str, Any], *, model: str = "test-model") -> dict[str, Any]:
    return {
        "model": model,
        "choices": [{"message": message, "finish_reason": "stop"}],
        "usage": {"total_tokens": 12},
    }


def test_run_tool_agent_executes_registered_handler_and_captures_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = [
        response(
            {
                "role": "assistant",
                "content": "Searching now.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "lookup",
                            "arguments": '{"query":"weather"}',
                        },
                    }
                ],
            }
        ),
        response({"role": "assistant", "content": "It is sunny."}),
    ]
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        requests.append(json.loads(request.data.decode()))
        assert timeout == 3
        return FakeResponse(payloads.pop(0))

    monkeypatch.setattr(tool_execution, "urlopen", fake_urlopen)
    result = tool_execution.run_tool_agent(
        [{"role": "user", "content": "Weather?"}],
        [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Look up a query",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                },
            }
        ],
        {"lookup": lambda args: {"answer": f"Sunny for {args['query']}"}},
        model="test-model",
        api_key="test-secret",
        request_timeout=3,
    )

    assert result["completed"] is True
    assert result["final_answer"] == "It is sunny."
    assert result["turns"] == 2
    assert [event["event_type"] for event in result["trace"]] == [
        "assistant_message",
        "tool_call",
        "tool_result",
        "assistant_message",
    ]
    assert result["trace"][1]["arguments"] == {"query": "weather"}
    assert result["trace"][2]["output"] == {"answer": "Sunny for weather"}
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert "test-secret" not in json.dumps(result)


def test_run_tool_agent_bounds_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        return FakeResponse(
            response(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "ping", "arguments": "{}"},
                        }
                    ],
                }
            )
        )

    monkeypatch.setattr(tool_execution, "urlopen", fake_urlopen)
    result = tool_execution.run_tool_agent(
        [{"role": "user", "content": "Ping"}],
        [{"type": "function", "function": {"name": "ping", "parameters": {"type": "object"}}}],
        {"ping": lambda args: "pong"},
        model="test",
        api_key="secret",
        max_turns=1,
    )
    assert result["completed"] is False
    assert result["stop_reason"] == "max_turns"
    assert result["turns"] == 1
    assert result["trace"][-1]["output"] == "pong"


def test_missing_handler_is_rejected_before_network_call() -> None:
    with pytest.raises(ValueError, match="No local handler"):
        tool_execution.run_tool_agent(
            [{"role": "user", "content": "hello"}],
            [{"type": "function", "function": {"name": "missing"}}],
            {},
            model="test",
            api_key="secret",
        )
