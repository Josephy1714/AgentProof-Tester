# Trace evaluation

AgentProof includes a dependency-free deterministic evaluator for recorded agent traces. It can evaluate caller-supplied events and can capture traces from bounded OpenAI-compatible tool-calling runs.

## Trace event format

Pass an ordered list of JSON-like objects. Events use **event_type** values **tool_call**, **tool_result**, or **assistant_message**. Tool calls may include **name** and structured **arguments**; tool results may include **output** or **content**; assistant messages use **content**.

## Supported checks

- **tool_called**: require a named tool to appear.
- **tool_not_called**: assert a named tool never appears.
- **tool_call_count**: require an exact number of tool calls.
- **max_tool_calls**: enforce an upper bound on tool calls.
- **tool_sequence**: require named calls in order (other calls may occur between them).
- **tool_argument_equals**: compare a nested argument path for the first matching call.
- **tool_result_contains**: inspect the latest result for a named tool.
- **final_answer_contains**: check the last assistant message for required text.

Example:

~~~python
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
~~~

The report contains an overall pass, score, summary counts, and per-check evidence. Checks are deterministic string/structure comparisons, not semantic safety judgments. Empty check lists pass with score 1.0. Malformed or unsupported check definitions raise **ValueError**; a valid check that does not match returns a failed result.

## Command-line usage and history

The repository includes a fixture at `examples/trace_fixture.json`. Run it without making a provider request:

~~~bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
~~~

By default, this writes a JSON report and saves the trace, checks, and per-check evidence in the local SQLite database selected by `--db` (default `agentproof.sqlite3`). Use `--no-history` to avoid storing the trace payload. Trace evaluation history is accessible through `/api/traces` and `/api/traces/<trace-id>` when the local API is running. The report contains the same pass/score/summary/per-check evidence returned by `evaluate_trace`.

Exit codes are CI-friendly: `0` means every check passed, `1` means at least one valid check failed, and `2` means the fixture or check definitions were invalid or unreadable.

## Capturing traces from a live tool-calling conversation

`agentproof.tool_execution.run_tool_agent` makes bounded Chat Completions requests with function tools, executes only explicitly registered Python handlers, and returns the final answer plus ordered `tool_call`, `tool_result`, and `assistant_message` events. It accepts OpenAI-compatible tool schemas and a mapping of tool names to Python callables. Set the provider key in the environment (default `OPENAI_API_KEY`) or pass `api_key` explicitly.

Example outline:

~~~python
from agentproof.tool_execution import run_tool_agent

result = run_tool_agent(
    [{"role": "user", "content": "Look up the weather in Nairobi."}],
    [{"type": "function", "function": {
        "name": "lookup_weather",
        "description": "Look up weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }}],
    {"lookup_weather": lambda args: {"city": args["city"], "forecast": "sunny"}},
    model="your-tool-capable-model",
)
trace = result["trace"]
checks = [{"type": "tool_called", "name": "lookup_weather"}]
report = evaluate_trace(trace, checks)
~~~

The loop is bounded by `max_turns` (default 8). If the limit is reached, `completed` is false and `stop_reason` is `max_turns`. Handler exceptions are captured as tool-result errors and returned to the model for possible recovery. Live trace capture is currently a Python API; the CLI trace-eval command evaluates fixtures rather than initiating provider calls.

**Security:** registered handlers run as ordinary Python functions in your process, not in a sandbox. Only register tools you trust, validate arguments inside handlers, and avoid exposing filesystem, shell, network, or other privileged capabilities unless intentionally required. Provider requests may incur charges.

## Current boundary

Trace evaluation history is separate from standard suite-run history. The API exposes summary listings and individual trace records, but the existing dashboard does not yet provide a trace-history view. Do not treat these checks as a complete prompt-injection or safety evaluation system.
