# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orchestrator_api_decompose - API package decomposition
"""HTTP API package for the orchestrator daemon.

This package provides REST endpoints for work unit management and daemon status.
The API is built with Starlette for minimal dependencies.

Exports:
    create_app: Factory function to create the Starlette application
"""

from orchestrator.api.app import create_app

__all__ = ["create_app"]
