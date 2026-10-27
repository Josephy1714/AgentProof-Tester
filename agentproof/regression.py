"""Structured run-to-run regression intelligence."""
from __future__ import annotations
from typing import Any
from agentproof.models import EvaluationRun, TestStatus


def compare_runs(previous: EvaluationRun, current: EvaluationRun) -> dict[str, Any]:
    before={x.test_id:x for x in previous.results}; after={x.test_id:x for x in current.results}
    if len(before)!=len(previous.results) or len(after)!=len(current.results): raise ValueError("Cannot compare runs containing duplicate test IDs")
    added=sorted(after.keys()-before.keys()); removed=sorted(before.keys()-after.keys())
    regressed=[]; recovered=[]; persistent=[]; changes=[]
    for test_id in sorted(before.keys() & after.keys()):
        old,new=before[test_id],after[test_id]
        if old.status==TestStatus.PASSED and new.status!=TestStatus.PASSED: regressed.append(test_id)
        elif old.status!=TestStatus.PASSED and new.status==TestStatus.PASSED: recovered.append(test_id)
        elif old.status!=TestStatus.PASSED and new.status!=TestStatus.PASSED: persistent.append(test_id)
        if old.status!=new.status: changes.append({"test_id":test_id,"from":old.status.value,"to":new.status.value})
    def rate(run: EvaluationRun, key: str) -> float:
        total=max(1,len(run.results)); return run.summary.get(key,0)/total
    return {"previous_run_id":previous.run_id,"current_run_id":current.run_id,"new_tests":added,"removed_tests":removed,"regressed_tests":regressed,"recovered_tests":recovered,"persistent_failures":persistent,"status_changes":changes,"previous_score":previous.score,"current_score":current.score,"score_delta":round(current.score-previous.score,6),"previous_pass_rate":rate(previous,"passed"),"current_pass_rate":rate(current,"passed"),"pass_rate_delta":round(rate(current,"passed")-rate(previous,"passed"),6),"previous_error_rate":(previous.summary.get("error",0)+previous.summary.get("timeout",0))/max(1,len(previous.results)),"current_error_rate":(current.summary.get("error",0)+current.summary.get("timeout",0))/max(1,len(current.results)),"error_rate_delta":round(((current.summary.get("error",0)+current.summary.get("timeout",0))/max(1,len(current.results)))-((previous.summary.get("error",0)+previous.summary.get("timeout",0))/max(1,len(previous.results))),6),"duration_delta_ms":round(current.duration_ms-previous.duration_ms,3),"comparable":previous.suite_name==current.suite_name,"warnings":[] if previous.suite_name==current.suite_name else ["Runs use different suite names; interpret score delta cautiously."]}
