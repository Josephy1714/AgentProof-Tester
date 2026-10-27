# AgentProof

**An evaluation and regression-testing foundation for AI agents.** AgentProof helps developers test agent behavior, compare versions, and understand failures using reproducible suites and explicit evidence.

> **Current status:** early foundation. A deterministic simulated adapter and an opt-in OpenAI-compatible Chat Completions adapter are implemented. The dashboard is still a static UI preview; there is no hosted evaluation API or production dashboard yet.

## Implemented

- Typed suite, assertion, run, and result models.
- Suite validation for duplicate IDs, unsupported schema/assertion types, missing assertions, invalid timeouts/weights, and malformed regular expressions.
- Deterministic assertions: equality, containment, type, numeric tolerance, regex, and object-key presence.
- Per-test exception and timeout reporting so later tests continue.
- Canonical SHA-256 configuration fingerprints and separate execution IDs.
- Regression comparisons for new/removed tests, pass-to-fail regressions, recoveries, status changes, and score deltas.
- JSON suite input, JSON report output, CLI, tests, and CI checks.
- Optional live adapter for OpenAI-compatible `/chat/completions` APIs, implemented with Python's standard library and no additional runtime dependencies.

## Quick start (Python 3.12+)

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -r requirements-dev.txt
pytest
python -m agentproof.cli run examples/basic_suite.json --report agentproof-report.json
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -r requirements-dev.txt
pytest
python -m agentproof.cli run examples/basic_suite.json --report agentproof-report.json
```

The default CLI mode uses `SimulatedAdapter`. Synthetic fixtures are useful for testing AgentProof itself, but are not evidence of real model performance.

## Run a live provider evaluation

The live adapter sends requests to an OpenAI-compatible Chat Completions endpoint. **Live requests may incur provider charges.** Keep API keys in environment variables; do not commit keys or put them in suite files.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-key"
python -m agentproof.cli run examples/live_provider_suite.json --adapter openai-compatible --model "your-model-id" --report live-report.json
```

macOS/Linux:

```bash
export OPENAI_API_KEY="your-key"
python -m agentproof.cli run examples/live_provider_suite.json --adapter openai-compatible --model "your-model-id" --report live-report.json
```

For a compatible provider or local gateway, supply its API base URL (the base URL should not include `/chat/completions`):

```bash
python -m agentproof.cli run examples/live_provider_suite.json --adapter openai-compatible --model "your-model-id" --base-url "https://provider.example/v1"
```

Configuration options:
- `--model` or `AGENTPROOF_MODEL`: model identifier required by the provider.
- `--base-url` or `AGENTPROOF_BASE_URL`: API base URL; defaults to `https://api.openai.com/v1`.
- `--api-key-env`: environment variable containing the API key; defaults to `OPENAI_API_KEY`.
- `--request-timeout`: per-request network timeout in seconds; defaults to 30.

Suite inputs can be plain strings, objects with a `prompt` string, or objects with a `messages` list of role/content strings. If the assistant response content is valid JSON, AgentProof parses it into a structured value so assertions can inspect fields. Otherwise, output is returned as an object containing `content`, `model`, and `usage`.

The API key is not included in the adapter configuration fingerprint or report. Treat reports as potentially sensitive because they can contain test inputs and model outputs.

## Project layout

- `agentproof/models.py`: typed contracts.
- `agentproof/validation.py`: validation and configuration fingerprinting.
- `agentproof/assertions.py`: deterministic assertion evaluation.
- `agentproof/adapters/`: adapter contract, simulated adapter, and OpenAI-compatible adapter.
- `agentproof/runner.py`: run orchestration and JSON reporting.
- `agentproof/regression.py`: comparisons between completed runs.
- `agentproof/cli.py`: local command-line interface.
- `examples/`: simulated and live-provider suites.
- `tests/`: engine, regression, and adapter tests.
- `docs/`: architecture and roadmap.

## Development checks

```bash
ruff check .
mypy agentproof
pytest
```

## Limitations and next steps

- The live adapter supports OpenAI-compatible Chat Completions only; provider-specific APIs and tool-calling/trajectory capture are not implemented.
- Provider response formats vary. The live example is a smoke test, not a guarantee of model compliance or a benchmark.
- Only schema version `1.0` is accepted.
- Current scoring is the unweighted mean of test scores; category weights are validated but not applied yet.
- Thread-based timeouts report overruns but cannot forcibly terminate code already running inside a thread. Untrusted execution requires process/container isolation.
- Persistent run history, a hosted API, authentication, and a dashboard backed by actual run data are not yet implemented.
- No production deployment is claimed.

See [architecture](docs/architecture.md) and [roadmap](docs/roadmap.md).
