# Python API and suite format

The current supported entry point is `run_suite(suite, adapter, adapter_config=None)`. It validates a typed `EvaluationSuite`, invokes the adapter for each test, evaluates deterministic assertions, and returns an `EvaluationRun`. The local CLI currently selects `SimulatedAdapter` explicitly.

## Assertion schema

Supported assertion types are `equals`, `contains`, `is_type`, `numeric_tolerance`, `regex`, and `has_key`. Optional `path` addresses nested object fields using dot notation and list indices. `regex` uses `pattern`; `contains` uses `value`; `numeric_tolerance` uses `expected` and a non-negative `tolerance`.

Every test must include one or more assertions. Only schema version `1.0` is currently accepted. Invalid suite definitions fail validation before adapter execution.

## Example

```json
{
  "name": "sample-suite",
  "version": "1.0.0",
  "schema_version": "1.0",
  "tests": [{
    "id": "returns-status",
    "input": {"simulated_output": {"status": "ok"}},
    "assertions": [{"type": "equals", "path": "status", "expected": "ok"}]
  }]
}
```

## Result semantics

Each test result has a status of `passed`, `failed`, `error`, `timeout`, or `skipped`. Assertion failures are different from adapter exceptions and timeouts. The run has a random execution ID and a stable configuration fingerprint. Scores are the unweighted mean of assertion outcomes per test and then the unweighted mean of test scores; category weights are validated but not yet applied.

The current simulated adapter is for development only. Do not interpret its output as a live model evaluation.
