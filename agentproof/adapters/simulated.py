"""Deterministic adapter for local development only."""
from typing import Any
from agentproof.adapters.base import AgentAdapter

class SimulatedAdapter(AgentAdapter):
    name = "simulated"
    is_simulated = True
    def invoke(self, payload: Any) -> Any:
        if isinstance(payload, dict) and "simulated_output" in payload:
            return payload["simulated_output"]
        return {"echo": payload, "mode": "simulated"}
