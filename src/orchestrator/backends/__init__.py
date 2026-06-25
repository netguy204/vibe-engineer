# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - Backend implementations package
# Chunk: docs/chunks/backend_config - Backend factory for config-driven backend selection
"""Concrete AgentBackend implementations and factory.

The :func:`create_backend` factory maps a config string to a concrete
:class:`~orchestrator.backend.AgentBackend` instance. It is the single
construction site for backends — callers (``create_scheduler``) never
import a backend class directly.
"""

from orchestrator.backend import AgentBackend
from orchestrator.backends.claude import ClaudeBackend

# Registry mapping config values to backend constructors.
# Each value is a zero-arg callable returning an AgentBackend instance.
BACKEND_REGISTRY: dict[str, type] = {
    "claude": ClaudeBackend,
}


def create_backend(name: str) -> AgentBackend:
    """Resolve a backend config value to a concrete AgentBackend instance.

    Args:
        name: Backend identifier from OrchestratorConfig.backend

    Returns:
        A fresh AgentBackend instance

    Raises:
        ValueError: If *name* is not in the registry. The message includes
            the bad value and the sorted list of known backends.
    """
    cls = BACKEND_REGISTRY.get(name)
    if cls is None:
        available = sorted(BACKEND_REGISTRY.keys())
        raise ValueError(
            f"Unknown backend {name!r}. Available backends: {', '.join(available)}"
        )
    return cls()
