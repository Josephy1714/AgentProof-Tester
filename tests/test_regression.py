from agentproof.adapters import SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.regression import compare_runs
from agentproof.runner import run_suite

def make_run(test_id, expected, actual):
    suite = EvaluationSuite("regression", "1", (TestCase(test_id, {"simulated_output": actual}, (AssertionSpec("equals", "value", expected),)),))
    return run_suite(suite, SimulatedAdapter())

def test_pass_to_fail_is_regression():
    assert compare_runs(make_run("stable", 1, {"value": 1}), make_run("stable", 2, {"value": 1}))["regressed_tests"] == ["stable"]

def test_fail_to_pass_is_recovery():
    assert compare_runs(make_run("stable", 2, {"value": 1}), make_run("stable", 1, {"value": 1}))["recovered_tests"] == ["stable"]

def test_new_and_removed_tests_are_not_regressions():
    diff = compare_runs(make_run("old", 1, {"value": 1}), make_run("new", 1, {"value": 0}))
    assert diff["new_tests"] == ["new"] and diff["removed_tests"] == ["old"]
    assert diff["regressed_tests"] == []

def test_score_delta():
    diff = compare_runs(make_run("stable", 1, {"value": 1}), make_run("stable", 2, {"value": 1}))
    assert diff["score_delta"] == -1.0
