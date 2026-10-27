# Trace evaluation

AgentProof provides deterministic checks for recorded traces, bounded OpenAI-compatible tool-calling execution, and SQLite-backed history for trace evaluations.

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

Example:

```python
from agentproof.traces import evaluate_trace

trace = [
    {"event_type": "tool_call", "name": "search", "arguments": {"query": "weather"}},
    {"event_type": "tool_result", "name": "search", "output": "Sunny"},
    {"event_type": "assistant_message", "content": "The forecast is sunny."},
]
report = evaluate_trace(trace, [
    {"type": "tool_called", "name": "search"},
    {"type": "max_tool_calls", "expected": 2},
    {"type": "final_answer_contains", "value": "sunny"},
])
```

The report contains an overall pass, score, summary counts, and per-check evidence. Checks are deterministic string/structure comparisons, not semantic safety judgments. Empty check lists pass with score 1.0. Malformed or unsupported check definitions raise `ValueError`; a valid check that does not match returns a failed result.

## Command-line usage and history

Run the included fixture without making a provider request:

```bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
```

By default, this writes a JSON report and saves the input trace, check definitions, summary and per-check evidence in the local SQLite database selected by `--db` (default `agentproof.sqlite3`). Use `--no-history` to avoid storing trace payloads. When persistence is enabled, the command prints the generated trace history ID.

Exit codes are CI-friendly: `0` means every check passed, `1` means at least one valid check failed, and `2` means the fixture, check definitions, or runtime operation was invalid or failed.

Trace history is separate from standard suite-run history. The local API exposes:

- `GET /api/traces?limit=20&offset=0` — recent summary records without full trace payloads.
- `GET /api/traces/<trace-id>` — full trace, check definitions, and per-check evidence.

The listing limit is bounded by the repository implementation. These endpoints use the same SQLite database path configured by `AGENTPROOF_DB`. The server binds to `127.0.0.1` by default and refuses a non-loopback bind (for example, `0.0.0.0`) unless `AGENTPROOF_API_TOKEN` is set. For an additional access-control layer, set `AGENTPROOF_API_TOKEN` to a long, random secret; all API GET requests then require `Authorization: Bearer <token>`. Requests with a missing or invalid token receive HTTP 401. Leave the variable unset for the existing local-only development workflow. Never commit the token or expose this development server directly to the public internet: bearer authentication does not provide TLS, user accounts, tenant isolation, rate limiting, or a production hosting architecture.

## Capturing and evaluating a live tool-calling conversation

Use `agentproof.tool_evaluation.run_and_evaluate_tool_agent` to execute a bounded conversation and evaluate the captured trace in one call:

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

Set the API key through `OPENAI_API_KEY` or pass `api_key` explicitly. The default endpoint is OpenAI-compatible Chat Completions; pass `base_url` to use a compatible gateway. The run is bounded by `max_turns` (default 8). Reaching the turn limit makes the overall report fail, even if checks on the partial trace pass. The report includes completion status, final answer, model usage, captured events, and per-check evidence. Live execution is a Python API; the CLI command above evaluates recorded fixtures and does not initiate provider calls. Live provider requests may incur charges.

**Security:** registered handlers run as ordinary Python functions in the caller's process, not in a sandbox. Only register trusted handlers, validate arguments inside handlers, and avoid exposing filesystem, shell, network, or other privileged capabilities unless intentionally required. Credentials are not included in returned reports.

## Current boundaries

- Trace history is not mixed with normal suite-run history.
- Trace history is currently API-only; the existing dashboard does not yet provide a trace-history view.
- The API is intended for local development and does not provide authentication or production multi-tenant isolation.
- Deterministic trace checks do not guarantee factual correctness, prompt-injection resistance, or overall agent safety.
