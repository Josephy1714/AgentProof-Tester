import pytest
from agentproof.adapters import SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase, TestStatus
from agentproof.runner import run_suite
from agentproof.validation import SuiteValidationError, configuration_fingerprint, validate_suite

def make_suite(*tests):
    return EvaluationSuite("demo", "1", tuple(tests))

def test_runner_records_pass_and_failure():
    good = TestCase("good", {"simulated_output": {"ok": True}}, (AssertionSpec("equals", "ok", True),))
    bad = TestCase("bad", {"simulated_output": {"ok": False}}, (AssertionSpec("equals", "ok", True),))
    run = run_suite(make_suite(good, bad), SimulatedAdapter())
    assert [r.status for r in run.results] == [TestStatus.PASSED, TestStatus.FAILED]
    assert run.simulated

def test_duplicate_ids_rejected():
    case = TestCase("same", {}, (AssertionSpec("equals", expected=1),))
    with pytest.raises(SuiteValidationError, match="unique"): validate_suite(make_suite(case, case))

def test_missing_assertions_rejected():
    with pytest.raises(SuiteValidationError, match="no assertions"):
        validate_suite(make_suite(TestCase("empty", {}, ())))

def test_fingerprint_changes_when_assertion_changes():
    a = make_suite(TestCase("a", {"x": 1}, (AssertionSpec("equals", expected=1),)))
    b = make_suite(TestCase("a", {"x": 1}, (AssertionSpec("equals", expected=2),)))
    assert configuration_fingerprint(a, "simulated") != configuration_fingerprint(b, "simulated")

def test_invalid_regex_rejected():
    with pytest.raises(SuiteValidationError, match="Invalid regex"):
        validate_suite(make_suite(TestCase("r", {}, (AssertionSpec("regex", pattern="["),))))
