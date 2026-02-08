# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator worktree manager - SPLIT FILE.

This file has been split into focused modules for better maintainability.
Tests have been moved to the following files:

- test_orchestrator_worktree_core.py - Core manager tests (paths, creation, cleanup, merge)
- test_orchestrator_worktree_operations.py - Operations (commit, multi-repo creation/removal/merge)
- test_orchestrator_worktree_symlinks.py - Task context symlinks
- test_orchestrator_worktree_persistence.py - Base branch persistence, checkout-free merge, locking
- test_orchestrator_worktree_multirepo.py - Multi-repo specific tests

This file is kept as a reference and to ensure backward compatibility with
any test collection that explicitly imports from this module.
"""

import subprocess
import pytest
from pathlib import Path

from orchestrator.worktree import WorktreeManager, WorktreeError


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository for testing.

    This fixture is re-exported for backward compatibility.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path
