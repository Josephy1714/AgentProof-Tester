# API

Start the local data API with:

```bash
python -m agentproof.api
```

It listens on `127.0.0.1:8000` and reads `AGENTPROOF_DB` or `agentproof.sqlite3`.

## Endpoints

- `GET /api/dashboard/overview` — KPI metrics from stored runs.
- `GET /api/runs?limit=50&offset=0&suite=&model=` — newest persisted runs.
- `GET /api/runs/<run_id>` — run metadata plus test-level evidence.
- `GET /api/runs/<run_id>/regression` — comparison against the previous run for the same suite.
- `GET /api/analytics/trends` — chronological score/test health data.
- `GET /api/analytics/models` — model aggregates from run metadata.
- `GET /api/analytics/suites` — suite aggregates.

The API is intentionally dependency-free and local-first. It is a foundation for a future authenticated hosted API, not a production multi-tenant service.

## Run history CLI

```bash
python -m agentproof.cli run examples/basic_suite.json
python -m agentproof.cli runs
python -m agentproof.cli run-show <run-id>
```

The first command persists the completed run to SQLite and also writes the JSON report.
