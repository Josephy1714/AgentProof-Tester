"""Base contract for agent adapters."""
from abc import ABC, abstractmethod
from typing import Any

class AgentAdapter(ABC):
    name = "adapter"
    is_simulated = False
    @abstractmethod
    def invoke(self, payload: Any) -> Any:
        """Invoke the agent once and return its output."""
