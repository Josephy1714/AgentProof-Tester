"""Compare runs without confusing new/removed tests with regressions."""
from typing import Any
from agentproof.models import EvaluationRun, TestStatus

def compare_runs(previous: EvaluationRun, current: EvaluationRun) -> dict[str, Any]:
    before = {item.test_id: item for item in previous.results}
    after = {item.test_id: item for item in current.results}
    if len(before) != len(previous.results) or len(after) != len(current.results):
        raise ValueError("Cannot compare runs containing duplicate test IDs")
    added, removed = sorted(after.keys()-before.keys()), sorted(before.keys()-after.keys())
    regressed, recovered, changes = [], [], []
    for test_id in sorted(before.keys() & after.keys()):
        old, new = before[test_id], after[test_id]
        if old.status == TestStatus.PASSED and new.status != TestStatus.PASSED: regressed.append(test_id)
        elif old.status != TestStatus.PASSED and new.status == TestStatus.PASSED: recovered.append(test_id)
        if old.status != new.status: changes.append({"test_id": test_id, "from": old.status.value, "to": new.status.value})
    same_suite = previous.suite_name == current.suite_name
    return {"previous_run_id": previous.run_id, "current_run_id": current.run_id,
        "new_tests": added, "removed_tests": removed, "regressed_tests": regressed,
        "recovered_tests": recovered, "status_changes": changes,
        "previous_score": previous.score, "current_score": current.score,
        "score_delta": round(current.score-previous.score, 6), "comparable": same_suite,
        "warnings": [] if same_suite else ["Runs use different suite names; interpret score delta cautiously."]}
