# Architecture

AgentProof separates evaluation execution from persistence, analytics, and presentation.

```text
Agent adapters -> Evaluation runner -> EvaluationRun
                                      |
                                      v
                              RunRepository
                                      |
                                  SQLite (local)
                                      |
                         +------------+------------+
                         |                         |
                    Analytics                Regression
                         |                         |
                         +------------+------------+
                                      |
                                HTTP API
                                      |
                              Dashboard UI

Recorded trace -> Trace evaluator -> Per-check evidence
```

## Current layers

- `agentproof/models.py` — immutable typed contracts.
- `agentproof/validation.py` — suite validation and configuration fingerprints.
- `agentproof/assertions.py` — deterministic output assertions.
- `agentproof/adapters/` — simulated and OpenAI-compatible providers.
- `agentproof/runner.py` — isolated test execution and result generation.
- `agentproof/storage.py` — replaceable repository boundary with SQLite implementation.
- `agentproof/regression.py` — run-to-run change analysis.
- `agentproof/analytics.py` — metrics derived from stored runs.
- `agentproof/api.py` — small standard-library HTTP API used by the dashboard.
- `agentproof/traces.py` — deterministic checks over caller-supplied recorded tool traces.
- `apps/web/` — data-backed dashboard UI.

## Trace evaluation boundary

Trace checks accept an ordered sequence of structured events and return a score, summary counts and per-check evidence. Supported checks cover tool presence/absence, call counts, tool order, nested arguments, tool result content and final answer text. This module does not capture or execute tool calls, infer semantic intent, or provide a complete safety evaluation. Live trace capture and persistence are planned follow-up work.

## Persistence

SQLite is deliberately the first implementation: it has no service dependency and is appropriate for local development and portfolio demonstrations. The runner remains usable without persistence, while the CLI persists completed runs by default. The `RunRepository` boundary is intended to allow a future Postgres/Supabase implementation without coupling the evaluator to a database vendor.

## Dashboard

The dashboard does not ship fabricated KPI values. It requests overview, run, regression, trend, model, and suite data from the API. An empty database produces an explicit empty state and instructions for creating the first synthetic run.

## Security boundaries

Provider keys are environment-only. Evaluation inputs, traces and outputs may contain sensitive data and should be treated as sensitive. SQLite is local development storage, not a production multi-tenant security boundary.

## Future extensions

- Live agent/tool trace capture and persistence.
- Hosted Postgres/Supabase persistence.
- Authentication and organizations.
- Async jobs and durable workers.
- Semantic safety and adversarial robustness evaluations.
- Scheduled benchmarks and notifications.
- Production deployment and observability.
