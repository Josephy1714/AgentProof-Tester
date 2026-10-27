"""AgentProof: a reproducible evaluation foundation for AI agents."""
from agentproof.models import AssertionSpec, EvaluationRun, EvaluationSuite, TestCase, TestStatus
from agentproof.runner import run_suite

__version__ = "0.1.0"
__all__ = ["AssertionSpec", "EvaluationRun", "EvaluationSuite", "TestCase", "TestStatus", "run_suite", "__version__"]
