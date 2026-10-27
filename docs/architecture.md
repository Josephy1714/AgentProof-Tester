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
```

## Current layers

- `agentproof/models.py` — immutable typed contracts.
- `agentproof/validation.py` — suite validation and configuration fingerprints.
- `agentproof/assertions.py` — deterministic assertions.
- `agentproof/adapters/` — simulated and OpenAI-compatible providers.
- `agentproof/runner.py` — isolated test execution and result generation.
- `agentproof/storage.py` — replaceable repository boundary with SQLite implementation.
- `agentproof/regression.py` — run-to-run change analysis.
- `agentproof/analytics.py` — metrics derived from stored runs.
- `agentproof/api.py` — small standard-library HTTP API used by the dashboard.
- `apps/web/` — data-backed dashboard UI.

## Persistence

SQLite is deliberately the first implementation: it has no service dependency and is appropriate for local development and portfolio demonstrations. The runner remains usable without persistence, while the CLI persists completed runs by default. The `RunRepository` boundary is intended to allow a future Postgres/Supabase implementation without coupling the evaluator to a database vendor.

## Dashboard

The dashboard does not ship fabricated KPI values. It requests overview, run, regression, trend, model, and suite data from the API. An empty database produces an explicit empty state and instructions for creating the first synthetic run.

## Security boundaries

Provider keys are environment-only. Evaluation outputs may contain sensitive inputs or model responses and should be treated as sensitive data. SQLite is local development storage, not a production multi-tenant security boundary.

## Future extensions

- Postgres/Supabase persistence.
- Authentication and organizations.
- Async jobs and durable workers.
- Agent trace and tool-call capture.
- Scheduled benchmarks and notifications.
- Production deployment and observability.
