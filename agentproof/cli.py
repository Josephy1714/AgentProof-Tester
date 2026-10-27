"""CLI for running evaluations and inspecting local history."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from typing import Any
from agentproof.adapters import AgentAdapter, OpenAICompatibleAdapter, SimulatedAdapter
from agentproof.models import AssertionSpec, EvaluationSuite, TestCase
from agentproof.runner import run_suite, write_json_report
from agentproof.storage import SQLiteRunRepository

def load_suite(path: str) -> EvaluationSuite:
    raw: dict[str,Any]=json.loads(Path(path).read_text(encoding="utf-8"))
    tests=tuple(TestCase(item["id"],item.get("input"),tuple(AssertionSpec(**a) for a in item.get("assertions",[])),item.get("category","general"),item.get("timeout_seconds",10.0),item.get("metadata",{})) for item in raw.get("tests",[]))
    return EvaluationSuite(raw.get("name",""),raw.get("version",""),tests,raw.get("schema_version","1.0"),raw.get("scoring_weights",{}),raw.get("metadata",{}))

def main(argv: list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="agentproof"); p.add_argument("command",choices=["run","runs","run-show"]); p.add_argument("suite",nargs="?"); p.add_argument("--report",default="agentproof-report.json"); p.add_argument("--db",default="agentproof.sqlite3"); p.add_argument("--limit",type=int,default=20); p.add_argument("--adapter",choices=["simulated","openai-compatible"],default="simulated"); p.add_argument("--model",default=os.environ.get("AGENTPROOF_MODEL")); p.add_argument("--base-url",default=os.environ.get("AGENTPROOF_BASE_URL","https://api.openai.com/v1")); p.add_argument("--api-key-env",default="OPENAI_API_KEY"); p.add_argument("--request-timeout",type=float,default=30.0); args=p.parse_args(argv)
    repo=SQLiteRunRepository(args.db)
    if args.command=="runs":
        print(json.dumps(repo.list_runs(args.limit),indent=2,default=str)); return 0
    if args.command=="run-show":
        if not args.suite: p.error("run-show requires a run id")
        run=repo.get_run(args.suite)
        if not run: print("Run not found",file=sys.stderr); return 2
        print(json.dumps(run.to_dict(),indent=2,default=str)); return 0
    if not args.suite: p.error("run requires a suite path")
    try:
        suite=load_suite(args.suite)
        if args.adapter=="simulated": adapter:AgentAdapter=SimulatedAdapter(); config={"mode":"simulated"}; provider="simulated"; model="synthetic"
        else:
            if not args.model: raise ValueError("The openai-compatible adapter requires --model or AGENTPROOF_MODEL.")
            adapter=OpenAICompatibleAdapter(model=args.model,base_url=args.base_url,api_key_env=args.api_key_env,request_timeout=args.request_timeout); config={"model":args.model,"base_url":args.base_url.rstrip("/"),"request_timeout":args.request_timeout}; provider="openai-compatible"; model=args.model
        run=run_suite(suite,adapter,adapter_config=config); repo.save_run(run,provider=provider,model=model); write_json_report(run,args.report)
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError,RuntimeError) as exc:
        print(f"AgentProof error: {exc}",file=sys.stderr); return 2
    print(f"Run: {run.run_id}\nScore: {run.score:.1%}\nResults: {run.summary}\nSimulated: {run.simulated}\nReport: {args.report}\nHistory: {args.db}")
    return 1 if any(run.summary.get(k,0) for k in ("failed","error","timeout")) else 0

if __name__=="__main__": raise SystemExit(main())
