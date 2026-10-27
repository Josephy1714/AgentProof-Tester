# Trace evaluation

AgentProof includes a dependency-free deterministic evaluator for recorded agent traces. It does not itself capture live tool calls from a provider or execute tools.

## Run a trace evaluation from the CLI

A trace case is a JSON object with two arrays: `trace` (ordered event objects) and `checks` (check definitions). The example is ready to run:

```bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
```

The command prints PASS/FAIL, score and counts, and writes per-check evidence to the JSON report. It exits with code **0** when all checks pass, **1** when valid checks fail, and **2** when the input cannot be loaded or is malformed. It does not create or update the SQLite run-history database. This command evaluates a recorded fixture only; it does not call a model or run a live agent.

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

## Python API

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

The report contains an overall pass, score, summary counts, and per-check evidence. Checks are deterministic string/structure comparisons, not semantic safety judgments. Empty check lists pass with score 1.0. Malformed or unsupported check definitions raise **ValueError**; a valid check that does not match returns a failed result.

## Current boundary

This module evaluates traces supplied by the caller. The existing OpenAI-compatible adapter currently performs a single chat-completion request and does not capture or execute tool calls. Live trace capture, persistence, API endpoints, dashboard trace exploration, and model-specific tool execution remain future work. Do not treat these checks as a complete prompt-injection or safety evaluation system.
