# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_worktree_process_reap - Tests for process reaping before worktree removal
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

import logging
import signal
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import psutil
import pytest

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


def _make_mock_proc(pid, cwd, cmdline=None):
    """Helper: build a mock psutil.Process with info dict pre-populated."""
    proc = MagicMock(spec=psutil.Process)
    proc.pid = pid
    proc.info = {"pid": pid, "cwd": cwd, "cmdline": cmdline or []}
    return proc


class TestReapWorktreeProcesses:
    """Tests for WorktreeManager._reap_worktree_processes."""

    def test_reap_sends_sigterm_then_sigkill_to_survivors(self, git_repo, caplog):
        """Processes in the worktree get SIGTERM, then SIGKILL if they survive."""
        manager = WorktreeManager(git_repo)
        worktree_path = git_repo / ".ve" / "chunks" / "mychunk" / "worktree"

        mock_proc = _make_mock_proc(pid=9999, cwd=str(worktree_path / "subdir"))
        # Process is still running after grace period → triggers SIGKILL
        mock_proc.is_running.return_value = True

        with patch("orchestrator.worktree.psutil.process_iter", return_value=[mock_proc]), \
             patch("orchestrator.worktree.time.sleep"), \
             patch("orchestrator.worktree.os.getpid", return_value=1), \
             caplog.at_level(logging.WARNING, logger="orchestrator.worktree"):
            manager._reap_worktree_processes(worktree_path)

        mock_proc.send_signal.assert_any_call(signal.SIGTERM)
        mock_proc.send_signal.assert_any_call(signal.SIGKILL)
        assert any("Reaping" in r.message for r in caplog.records)
        assert any("SIGKILL" in r.message for r in caplog.records)

    def test_reap_skips_sigkill_for_exited_processes(self, git_repo):
        """Processes that exit after SIGTERM are not SIGKILL'd."""
        manager = WorktreeManager(git_repo)
        worktree_path = git_repo / ".ve" / "chunks" / "mychunk" / "worktree"

        mock_proc = _make_mock_proc(pid=9999, cwd=str(worktree_path))
        # Process already gone → is_running returns False
        mock_proc.is_running.return_value = False

        with patch("orchestrator.worktree.psutil.process_iter", return_value=[mock_proc]), \
             patch("orchestrator.worktree.time.sleep"), \
             patch("orchestrator.worktree.os.getpid", return_value=1):
            manager._reap_worktree_processes(worktree_path)

        # SIGTERM should have been sent
        mock_proc.send_signal.assert_any_call(signal.SIGTERM)
        # SIGKILL must NOT have been sent
        sigkill_calls = [c for c in mock_proc.send_signal.call_args_list
                         if c == call(signal.SIGKILL)]
        assert not sigkill_calls

    def test_reap_ignores_processes_outside_worktree(self, git_repo):
        """Processes whose cwd is elsewhere are not touched."""
        manager = WorktreeManager(git_repo)
        worktree_path = git_repo / ".ve" / "chunks" / "mychunk" / "worktree"

        mock_proc = _make_mock_proc(pid=8888, cwd="/some/other/path")

        with patch("orchestrator.worktree.psutil.process_iter", return_value=[mock_proc]), \
             patch("orchestrator.worktree.time.sleep"), \
             patch("orchestrator.worktree.os.getpid", return_value=1):
            manager._reap_worktree_processes(worktree_path)

        mock_proc.send_signal.assert_not_called()

    def test_reap_no_log_when_no_processes_found(self, git_repo, caplog):
        """No WARNING is emitted when there are no candidate processes."""
        manager = WorktreeManager(git_repo)
        worktree_path = git_repo / ".ve" / "chunks" / "mychunk" / "worktree"

        with patch("orchestrator.worktree.psutil.process_iter", return_value=[]), \
             patch("orchestrator.worktree.time.sleep"), \
             patch("orchestrator.worktree.os.getpid", return_value=1), \
             caplog.at_level(logging.WARNING, logger="orchestrator.worktree"):
            manager._reap_worktree_processes(worktree_path)

        assert not any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_remove_worktree_calls_reaper_before_removal(self, git_repo):
        """remove_worktree invokes _reap_worktree_processes before git removal."""
        manager = WorktreeManager(git_repo)

        # Create an actual worktree so remove_worktree has something to clean up
        worktree_path = git_repo / ".ve" / "chunks" / "mychunk" / "worktree"
        subprocess.run(
            ["git", "worktree", "add", "-b", "mychunk-branch", str(worktree_path)],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        reaper_calls = []

        original_reap = manager._reap_worktree_processes

        def recording_reap(path):
            reaper_calls.append(path)

        manager._reap_worktree_processes = recording_reap

        manager._remove_worktree_from_repo(worktree_path, git_repo)

        assert len(reaper_calls) == 1
        assert reaper_calls[0] == worktree_path
        # Worktree directory should be gone after removal
        assert not worktree_path.exists()
