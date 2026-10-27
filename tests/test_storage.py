from __future__ import annotations
import tempfile
from pathlib import Path
from agentproof.models import EvaluationRun, TestResult, TestStatus
from agentproof.storage import SQLiteRunRepository
from agentproof.analytics import overview, trends

def sample(run_id: str, score: float) -> EvaluationRun:
    return EvaluationRun(run_id,"suite","1.0","fp","simulated",True,"2026-10-27T10:00:00+00:00",10.0,(TestResult("t1",TestStatus.PASSED,score,5.0),),score,{s.value:(1 if s is TestStatus.PASSED else 0) for s in TestStatus})

def test_sqlite_round_trip() -> None:
    with tempfile.TemporaryDirectory() as d:
        repo=SQLiteRunRepository(Path(d)/"runs.sqlite3"); run=sample("r1",1.0); repo.save_run(run,provider="simulated",model="synthetic")
        loaded=repo.get_run("r1")
        assert loaded is not None and loaded.run_id=="r1" and loaded.results[0].status is TestStatus.PASSED
        assert repo.list_runs()[0]["model"]=="synthetic"

def test_analytics_empty_and_trend() -> None:
    with tempfile.TemporaryDirectory() as d:
        repo=SQLiteRunRepository(Path(d)/"runs.sqlite3"); assert overview(repo)["total_runs"]==0
        repo.save_run(sample("r1",1.0)); assert trends(repo)[0]["score"]==1.0
