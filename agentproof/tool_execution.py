"""Execute OpenAI-compatible tool calls and capture a normalized trace.

Only explicitly registered Python handlers can run. This module does not
provide a sandbox; callers are responsible for the capabilities they register.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ToolHandler = Callable[[dict[str, Any]], Any]


def run_tool_agent(
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]],
    handlers: Mapping[str, ToolHandler],
    *,
    model: str,
    base_url: str = "https://api.openai.com/v1",
    api_key: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    request_timeout: float = 30.0,
    max_turns: int = 8,
) -> dict[str, Any]:
    """Run a bounded tool-calling conversation and return its trace.

    The trace records assistant messages, tool calls, and tool results in
    observed order. Tool handler exceptions become error results so the model
    can recover. API credentials are never returned in the result.
    """
    if not model.strip():
        raise ValueError("model must not be empty")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("base_url must start with http:// or https://")
    if request_timeout <= 0:
        raise ValueError("request_timeout must be greater than zero")
    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")
    if not messages or any(
        not isinstance(message.get("role"), str) for message in messages
    ):
        raise ValueError("messages must be a non-empty sequence with string roles")
    if not tools:
        raise ValueError("at least one tool definition is required")

    key = api_key or os.environ.get(api_key_env)
    if not key:
        raise ValueError(f"Missing API key. Set the {api_key_env} environment variable.")

    declared_names: set[str] = set()
    for tool in tools:
        function = tool.get("function")
        name = function.get("name") if isinstance(function, Mapping) else None
        if not isinstance(name, str) or not name:
            raise ValueError("each tool must define function.name")
        if name not in handlers:
            raise ValueError(f"No local handler registered for tool {name!r}")
        declared_names.add(name)

    conversation: list[dict[str, Any]] = [dict(message) for message in messages]
    trace: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    response_model = model
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    for turn in range(max_turns):
        body = json.dumps(
            {
                "model": model,
                "messages": conversation,
                "tools": list(tools),
                "tool_choice": "auto",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=request_timeout) as response:
                payload: Any = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Provider returned HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise RuntimeError(f"Could not reach provider: {exc.reason}") from None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Provider returned invalid JSON: {exc}") from None

        try:
            choice = payload["choices"][0]
            assistant = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Provider response is missing choices[0].message") from exc
        if not isinstance(assistant, dict):
            raise RuntimeError("Provider assistant message must be an object")

        response_model = str(payload.get("model", model))
        raw_usage = payload.get("usage")
        if isinstance(raw_usage, dict):
            usage = raw_usage
        conversation.append(assistant)

        content = assistant.get("content")
        if isinstance(content, str) and content:
            trace.append({"event_type": "assistant_message", "content": content})

        raw_calls = assistant.get("tool_calls")
        if not raw_calls:
            return {
                "final_answer": content if isinstance(content, str) else "",
                "trace": trace,
                "model": response_model,
                "usage": usage,
                "turns": turn + 1,
                "completed": True,
            }
        if not isinstance(raw_calls, list):
            raise RuntimeError("Provider tool_calls must be an array")

        for call in raw_calls:
            if not isinstance(call, dict):
                raise RuntimeError("Provider tool call must be an object")
            function = call.get("function")
            name = function.get("name") if isinstance(function, dict) else None
            arguments_text = function.get("arguments") if isinstance(function, dict) else None
            call_id = call.get("id")
            if not isinstance(name, str) or name not in declared_names:
                raise RuntimeError(f"Provider requested undeclared tool {name!r}")
            if not isinstance(call_id, str) or not call_id:
                raise RuntimeError("Provider tool call is missing its id")
            if not isinstance(arguments_text, str):
                raise RuntimeError(f"Arguments for tool {name!r} must be a JSON string")
            try:
                arguments = json.loads(arguments_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON arguments for tool {name!r}: {exc}") from exc
            if not isinstance(arguments, dict):
                raise RuntimeError(f"Arguments for tool {name!r} must decode to an object")

            trace.append(
                {
                    "event_type": "tool_call",
                    "name": name,
                    "arguments": arguments,
                    "call_id": call_id,
                }
            )
            try:
                result = handlers[name](arguments)
                result_text = json.dumps(result, ensure_ascii=False, default=str)
                trace.append(
                    {
                        "event_type": "tool_result",
                        "name": name,
                        "output": result,
                        "call_id": call_id,
                    }
                )
            except Exception as exc:
                result_text = json.dumps({"error": f"{type(exc).__name__}: {exc}"})
                trace.append(
                    {
                        "event_type": "tool_result",
                        "name": name,
                        "output": {"error": f"{type(exc).__name__}: {exc}"},
                        "is_error": True,
                        "call_id": call_id,
                    }
                )
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_text,
                }
            )

    return {
        "final_answer": "",
        "trace": trace,
        "model": response_model,
        "usage": usage,
        "turns": max_turns,
        "completed": False,
        "stop_reason": "max_turns",
    }
