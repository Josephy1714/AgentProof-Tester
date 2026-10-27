"""Typed data contracts for AgentProof."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

class TestStatus(StrEnum):
    __test__ = False
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

@dataclass(frozen=True, slots=True)
class AssertionSpec:
    type: str
    path: str | None = None
    expected: Any = None
    value: Any = None
    tolerance: float | None = None
    pattern: str | None = None

@dataclass(frozen=True, slots=True)
class TestCase:
    __test__ = False
    id: str
    input: Any
    assertions: tuple[AssertionSpec, ...]
    category: str = "general"
    timeout_seconds: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class EvaluationSuite:
    name: str
    version: str
    tests: tuple[TestCase, ...]
    schema_version: str = "1.0"
    scoring_weights: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class AssertionResult:
    assertion_type: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None

@dataclass(frozen=True, slots=True)
class TestResult:
    test_id: str
    status: TestStatus
    score: float
    duration_ms: float
    assertion_results: tuple[AssertionResult, ...] = ()
    output: Any = None
    error_type: str | None = None
    error_message: str | None = None
    category: str = "general"

@dataclass(frozen=True, slots=True)
class EvaluationRun:
    run_id: str
    suite_name: str
    suite_version: str
    config_fingerprint: str
    adapter_name: str
    simulated: bool
    started_at: str
    duration_ms: float
    results: tuple[TestResult, ...]
    score: float
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
