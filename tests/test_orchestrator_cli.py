# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator CLI commands - SPLIT FILE.

This file has been split into focused modules for better maintainability.
Tests have been moved to the following files:

- test_orchestrator_cli_core.py - Core CLI commands (start, stop, status, ps, work-unit create/status)
- test_orchestrator_cli_operations.py - Operation commands (delete, inject, queue, prioritize, config)
- test_orchestrator_cli_display.py - Display commands (work-unit show, url)
- test_orchestrator_cli_attention.py - Attention-related commands (ps attention_reason)
- test_orchestrator_cli_batch.py - Batch operations (inject-batch)
- test_orchestrator_cli_tail.py - Tail command

This file is kept as a reference and to ensure backward compatibility with
any test collection that explicitly imports from this module.
"""

# Re-export the runner fixture for backward compatibility
import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    """Create a Click CLI test runner.

    This fixture is defined in the split files but re-exported here
    for backward compatibility.
    """
    return CliRunner()
