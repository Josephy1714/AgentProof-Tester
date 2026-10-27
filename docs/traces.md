# Trace evaluation

AgentProof provides deterministic checks for recorded traces and a bounded OpenAI-compatible tool-calling runner. The runner captures a normalized trace; the helper in `agentproof.tool_evaluation` evaluates that trace immediately. Persistence and dashboard integration are not implemented yet.

## Trace event format

Pass an ordered list of JSON-like objects. Events use `event_type` values `tool_call`, `tool_result`, or `assistant_message`. Tool calls may include `name` and structured `arguments`; tool results may include `output` or `content`; assistant messages use `content`.

## Supported checks

- `tool_called`: require a named tool to appear.
- `tool_not_called`: assert a named tool never appears.
- `tool_call_count`: require an exact number of tool calls.
- `max_tool_calls`: enforce an upper bound on tool calls.
- `tool_sequence`: require named calls in order (other calls may occur between them).
- `tool_argument_equals`: compare a nested argument path for the first matching call.
- `tool_result_contains`: inspect the latest result for a named tool.
- `final_answer_contains`: check the last assistant message for required text.

`evaluate_trace(events, checks)` returns an overall pass, score, summary counts, and per-check evidence. Checks are deterministic string/structure comparisons, not semantic safety judgments. Empty check lists pass with score 1.0. Malformed or unsupported check definitions raise `ValueError`; a valid check that does not match returns a failed result.

## Evaluate a recorded fixture

The repository includes `examples/trace_fixture.json`. Run it without making a provider request:

```bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
```

Exit codes are CI-friendly: `0` means every check passed, `1` means at least one valid check failed, and `2` means the fixture or check definitions were invalid or unreadable. This command does not create a model evaluation run or modify run history.

## Capture and evaluate a live tool-calling conversation

Use `agentproof.tool_evaluation.run_and_evaluate_tool_agent` to execute a bounded conversation and evaluate the trace in one call:

```python
from agentproof.tool_evaluation import run_and_evaluate_tool_agent

report = run_and_evaluate_tool_agent(
    messages=[{"role": "user", "content": "Look up the weather in Nairobi."}],
    tools=[{
        "type": "function",
        "function": {
            "name": "lookup_weather",
            "description": "Look up weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }],
    handlers={
        "lookup_weather": lambda args: {
            "city": args["city"],
            "forecast": "sunny",
        }
    },
    checks=[
        {"type": "tool_called", "name": "lookup_weather"},
        {"type": "final_answer_contains", "value": "sunny"},
    ],
    model="your-tool-capable-model",
)
print(report["passed"])
print(report["evaluation"]["results"])
```

Set the API key through `OPENAI_API_KEY` or pass `api_key` explicitly. The default provider endpoint is OpenAI-compatible Chat Completions; pass `base_url` to use a compatible gateway. The run is bounded by `max_turns` (default 8). A run that reaches this limit is marked failed overall, even if all checks on the partial trace pass. The report contains execution completion status, final answer, model usage, captured events, and per-check evidence.

## Security and limitations

Registered handlers run as ordinary Python functions in the caller's process, not in a sandbox. Only register trusted handlers, validate arguments inside handlers, and avoid exposing filesystem, shell, network, or other privileged capabilities unless intentionally required. Provider requests may incur charges; credentials are not included in the returned report.

Live tool-run results are not yet persisted to SQLite, exposed through the HTTP API, or displayed in the dashboard. These checks do not guarantee factual correctness, resistance to prompt injection, or overall safety.
