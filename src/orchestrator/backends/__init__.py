# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - Backend implementations package
# Chunk: docs/chunks/backend_config - Backend factory for config-driven backend selection
# Chunk: docs/chunks/backend_cursor - CursorBackend registration
"""Concrete AgentBackend implementations and factory.

The :func:`create_backend` factory maps a config string to a concrete
:class:`~orchestrator.backend.AgentBackend` instance. It is the single
construction site for backends — callers (``create_scheduler``) never
import a backend class directly.
"""

import logging

from orchestrator.backend import AgentBackend
from orchestrator.backends.claude import ClaudeBackend

logger = logging.getLogger(__name__)

# Registry mapping config values to AgentBackend classes.
# Each value is an AgentBackend subclass; create_backend() instantiates it.
# CursorBackend is lazily imported so the module loads cleanly even when
# cursor-agent is not installed — the binary check happens at run() time.
BACKEND_REGISTRY: dict[str, type] = {
    "claude": ClaudeBackend,
}

try:
    from orchestrator.backends.cursor import CursorBackend

    BACKEND_REGISTRY["cursor"] = CursorBackend
except Exception as e:  # pragma: no cover - degrade gracefully but visibly
    # A genuine import failure in cursor.py (not just a missing dependency)
    # would otherwise silently de-register the cursor backend. Log it so the
    # cause is visible while still allowing the orchestrator to run on claude.
    logger.warning("cursor backend unavailable: %s", e)


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
