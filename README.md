# AgentProof

**An evaluation and regression-testing platform foundation for AI agents.** AgentProof helps developers run reproducible suites, inspect evidence, compare versions, and track quality over time.

> **Current status:** evaluation engine + deterministic simulated adapter + opt-in OpenAI-compatible adapter + SQLite run history + regression analytics + local dashboard API + data-backed dashboard + deterministic trace checks + bounded live tool-call trace capture + trace evaluation history/API. Hosted auth, cloud persistence and distributed jobs are future work.

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
- SQLite persistence for trace evaluation inputs and per-check evidence, with API endpoints for trace history.
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

The trace evaluator checks a sequence of structured events and returns per-check evidence. It does not require a model call when evaluating fixtures.

```bash
python -m agentproof.cli trace-eval examples/trace_fixture.json --report trace-report.json
```

By default, the command writes the JSON report and stores the trace, checks, and evidence in the local SQLite history. Use `--no-history` to avoid storing trace payloads. Exit codes are 0 for all checks passing, 1 for valid checks failing, and 2 for invalid input or runtime errors.

Trace history API endpoints:

- `/api/traces` — recent trace-evaluation summaries
- `/api/traces/<trace-id>` — full trace, checks and per-check results

See [Trace evaluation](docs/traces.md) for event format, supported checks, history behavior, and the live tool-execution Python API. Live trace capture is not yet a CLI command or a dashboard view.

## Live provider evaluation

```bash
export OPENAI_API_KEY="your-key"
python -m agentproof.cli run examples/live_provider_suite.json --adapter openai-compatible --model "your-model-id"
```

For another OpenAI-compatible gateway, use `--base-url`. Live requests may incur provider charges. API keys are never written into fingerprints or reports.

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
- `/api/traces`
- `/api/traces/<trace-id>`

The existing dashboard includes KPI cards, score trends, test-health visualization, recent runs, run-level evidence, regression summaries, model/suite analytics, and responsive empty/error states. Trace history is currently API-only.

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

Tool-calling agent -> Normalized trace -> Trace checks -> TraceRepository -> SQLite
                                                               |
                                                           Trace API
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

See `docs/roadmap.md`. Next priorities are dashboard trace exploration, integration of live tool runs with trace evaluation, hosted persistence, authentication, async jobs, scheduling and production deployment.

## License

MIT.
