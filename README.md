# AgentProof

**An evaluation and regression-testing foundation for AI agents.** AgentProof aims to help developers test agent behavior, compare versions, and understand failures using reproducible suites and explicit evidence.

> **Current status:** early foundation. The current adapter is simulated and intended for local development. It does not evaluate a live external AI agent, and no hosted evaluation API or production dashboard is claimed to exist yet.

## Implemented

- Typed suite, assertion, run, and result models.
- Suite validation for duplicate IDs, unsupported schema/assertion types, missing assertions, invalid timeouts/weights, and malformed regular expressions.
- Deterministic assertions: equality, containment, type, numeric tolerance, regex, and object-key presence.
- Per-test exception and timeout reporting so later tests continue.
- Canonical SHA-256 configuration fingerprints and separate execution IDs.
- Regression comparisons for new/removed tests, pass-to-fail regressions, recoveries, status changes, and score deltas.
- JSON suite input, JSON report output, CLI, tests, and CI checks.

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

The CLI explicitly uses `SimulatedAdapter`. Outputs are synthetic fixtures, not evidence of real model performance.

## Project layout

- `agentproof/models.py`: typed contracts.
- `agentproof/validation.py`: validation and configuration fingerprinting.
- `agentproof/assertions.py`: deterministic assertion evaluation.
- `agentproof/adapters/`: adapter contract and simulated adapter.
- `agentproof/runner.py`: run orchestration and JSON reporting.
- `agentproof/regression.py`: comparisons between completed runs.
- `agentproof/cli.py`: local command-line interface.
- `examples/basic_suite.json`: example suite.
- `tests/`: engine and regression tests.
- `docs/`: architecture and roadmap.

## Development checks

```bash
ruff check .
mypy agentproof
pytest
```

## Limitations and next steps

- Only schema version `1.0` is accepted.
- Current scoring is the unweighted mean of test scores; category weights are validated but not applied yet.
- Thread-based timeouts report overruns but cannot forcibly terminate code already running inside a thread. Untrusted execution requires process/container isolation.
- Real provider integrations, persistent run history, authentication, a hosted API, and a production dashboard are not yet implemented.

See [architecture](docs/architecture.md) and [roadmap](docs/roadmap.md).