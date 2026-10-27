# Roadmap

## Phase 1 — foundation (complete)
- Versioned suites, deterministic assertions, isolated runner, regression comparison, tests and CI.

## Phase 2 — provider integration (complete)
- Optional OpenAI-compatible Chat Completions adapter with environment-only credentials.

## Phase 3 — evaluation platform (complete)
- SQLite run history behind a repository abstraction.
- Persisted test-level evidence and run metadata.
- Regression intelligence with new/removed, regressed, recovered and persistent failures.
- Analytics for scores, pass/error rates, suites and models.
- Local JSON HTTP API.
- Data-backed dashboard with Overview, Evaluations, Test Suites, Regression, Analytics, Models and Settings sections.

## Phase 4A — trace evaluation primitives (complete)
- Deterministic checks for tool presence/absence and call counts.
- Ordered tool-call sequence checks.
- Nested tool-argument comparisons.
- Tool-result and final-answer checks.
- Per-check evidence and explicit limitations.
- Next: connect trace capture to an agent execution adapter and persist traces alongside run results.

## Phase 5 — production platform
- Hosted Postgres/Supabase persistence.
- Authentication, organizations and project permissions.
- Async evaluation jobs and durable workers.
- Provider/agent trace capture, trajectory evaluation and safety suites.
- Scheduling, notifications, report sharing and production deployment.

AgentProof does not claim Phase 4B capabilities until they are implemented and tested.
