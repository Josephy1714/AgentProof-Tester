# Roadmap

## Phase 1 — foundation
- Versioned suites, deterministic assertions, isolated runner, regression comparison, tests and CI.

## Phase 2 — provider integration
- Optional OpenAI-compatible Chat Completions adapter with environment-only credentials.

## Phase 3 — evaluation platform (current)
- SQLite run history behind a repository abstraction.
- Persisted test-level evidence and run metadata.
- Regression intelligence with new/removed, regressed, recovered and persistent failures.
- Analytics for scores, pass/error rates, suites and models.
- Local JSON HTTP API.
- Data-backed dashboard with Overview, Evaluations, Test Suites, Regression, Analytics, Models and Settings sections.

## Phase 4 — production platform
- Hosted Postgres/Supabase persistence.
- Authentication, organizations and project permissions.
- Async evaluation jobs and durable workers.
- Agent traces, tool-call/trajectory evaluation and safety suites.
- Scheduling, notifications, report sharing and production deployment.

The current release does not claim those Phase 4 capabilities.
