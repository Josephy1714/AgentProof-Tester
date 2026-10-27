# AgentProof

**An evaluation and regression-testing platform foundation for AI agents.** AgentProof helps developers run reproducible suites, inspect evidence, compare versions, and track quality over time.

> **Current status:** evaluation engine + deterministic simulated adapter + opt-in OpenAI-compatible adapter + SQLite run history + regression analytics + local dashboard API + data-backed dashboard + deterministic trace checks + bounded live tool execution and trace evaluation. Hosted auth, cloud persistence, distributed jobs, and dashboard trace exploration remain future work.

## Implemented

- Typed suites, assertions, test results and evaluation runs.
- Validation for malformed suites, unsupported assertions, duplicate IDs, timeouts, weights and regex patterns.
- Deterministic equality, containment, type, numeric tolerance, regex and object-key assertions.
- Per-test exception and timeout isolation.
- Configuration fingerprints and execution IDs.
- OpenAI-compatible Chat Completions adapter with environment-only API keys.
- SQLite persistence behind a `RunRepository` abstraction.
- Persisted test-level model outputs and assertion evidence.
- Regression analysis for new/removed tests, regressions, recoveries, persistent failures, score/pass/error deltas and duration changes.
- Analytics for overview metrics, trends, model performance and suite performance.
- Local JSON HTTP API.
- Dashboard sections: Overview, Evaluations, Test Suites, Regression, Analytics, Models and Settings.
- Responsive charts, run detail inspection, empty states and data-backed KPIs.
- Deterministic recorded-trace checks for tool presence/absence, call counts, ordered tool sequences, nested arguments, tool results and final-answer text.
- Bounded OpenAI-compatible function-tool execution with caller-registered handlers and normalized trace capture.
- Python helper that runs a tool-calling conversation, evaluates its captured trace, and marks turn-limited executions as failed.
- Tests and CI with Ruff, mypy and pytest.

## Quick start

Python 3.12+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . -r requirements-dev.txt
pytest
python -m agentproof.cli run examples/basic_suite.json
python -m agentproof.api
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -r requirements-dev.txt
pytest
python -m agentproof.cli run examples/basic_suite.json
python -m agentproof.api
```

Open `apps/web/index.html` through the repository's web hosting or local static server while the API is running. The dashboard reads real API data; it does not contain fabricated KPI values.

## Run history

The CLI persists completed evaluations to `agentproof.sqlite3` by default:

```bash
python -m agentproof.cli runs
python -m agentproof.cli run-show <run-id>
```

Use `AGENTPROOF_DB` or `--db` to select another local database path. SQLite files are ignored by git.

## Recorded trace evaluation

The trace evaluator checks an ordered sequence of structured events. It supports tool presence/absence, call counts, ordered call sequences, nested arguments, tool results and final-answer text.

```python
from agentproof.traces import evaluate_trace

trace = [
    {"event_type": "tool_call", "name": "search", "arguments": {"query": "weather"}},
    {"event_type": "tool_result", "name": "search", "output": "Sunny"},
    {"event_type": "assistant_message", "content": "The forecast is sunny."},
]
report = evaluate_trace(trace, [
    {"type": "tool_called", "name": "search"},
    {"type": "tool_not_called", "name": "delete_file"},
    {"type": "max_tool_calls", "expected": 2},
    {"type": "final_answer_contains", "value": "sunny"},
])
```

Run a recorded JSON fixture without making a provider request:

```bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
```

The command exits with code 0 when all checks pass, 1 when valid checks fail, and 2 for invalid input or runtime errors. It writes per-check evidence to the report and does not create a run-history database entry.

## Live tool execution and evaluation

The Python API can capture a bounded tool-calling conversation and evaluate the captured trace in one call:

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
print(report["passed"], report["evaluation"]["results"])
```

Set `OPENAI_API_KEY` in the environment, or pass `api_key` explicitly. Configure `base_url` for another OpenAI-compatible gateway. The run is bounded by `max_turns` (default 8); reaching the limit makes the overall report fail even if the checks on the partial trace pass. The report includes the captured trace, per-check evidence, model usage and completion status. This helper does not yet persist traces or expose them through the CLI, HTTP API or dashboard.

**Security:** registered handlers run as ordinary Python functions in your process, not in a sandbox. Only register trusted handlers, validate arguments inside them, and avoid exposing privileged capabilities unless intentionally required. Live provider requests may incur charges. API keys are not included in returned reports.

## Live provider evaluation

```bash
export OPENAI_API_KEY="your-key"
python -m agentproof.cli run examples/live_provider_suite.json --adapter openai-compatible --model "your-model-id"
```

Live requests may incur provider charges. API keys are never written into fingerprints or reports.

## Dashboard and API

Start the local API:

```bash
python -m agentproof.api
```

Endpoints include:

- `/api/dashboard/overview`
- `/api/runs`
- `/api/runs/<id>`
- `/api/runs/<id>/regression`
- `/api/analytics/trends`
- `/api/analytics/models`
- `/api/analytics/suites`

The dashboard includes KPI cards, score trends, test-health visualization, recent runs, run-level evidence, regression summaries, model/suite analytics, and responsive empty/error states. Trace-specific views are not implemented yet.

## Architecture

```text
Adapters -> Evaluation Runner -> EvaluationRun -> RunRepository -> SQLite
                                             |          |
                                             v          v
                                         Regression  Analytics
                                             \          /
                                              HTTP API
                                                 |
                                            Web Dashboard

Tool Agent -> Captured Trace -> Trace Checks -> Per-check Evidence
```

The storage boundary is intentionally replaceable so a future Postgres/Supabase implementation can be introduced without coupling evaluation logic to a database vendor.

## Development checks

```bash
ruff check .
mypy agentproof
pytest
```

## Security

Keep provider keys in environment variables. Evaluation inputs, traces and outputs may contain sensitive information. SQLite and the current local HTTP API are development/portfolio infrastructure, not a production multi-tenant security boundary. Trace checks are deterministic and do not replace semantic safety testing.

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).

## License

MIT.
