# Architecture

AgentProof separates suite contracts, deterministic assertions, adapters, execution, and regression comparison. A suite is validated before execution. Each test invokes an adapter once and evaluates assertions against its output. Adapter exceptions and timeouts become explicit statuses, and later tests continue. A SHA-256 fingerprint identifies the canonical suite and adapter configuration; each execution has a separate run ID.

The included adapter is simulated only. A future hosted runner must isolate untrusted execution, bound resource use, redact secrets, authenticate callers, and persist artifacts safely before accepting public workloads.

## Current limitations

Scoring is currently the arithmetic mean of test scores; category weights are validated but not applied yet. Thread-based timeouts cannot terminate an adapter thread. Provider metrics, model judging, durable storage, authentication, a live API, and a production dashboard are not implemented.
