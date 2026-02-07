# Chunk: docs/chunks/orch_daemon_stale_files - Stale file cleanup on SIGKILL fallback
"""Tests for daemon state file cleanup.

These tests verify that all state files (PID, socket, port) are properly
cleaned up after daemon shutdown, including the SIGKILL fallback scenario.
"""

import os
import signal
from unittest import mock

import pytest

from orchestrator.daemon import (
    _cleanup_state_files,
    get_pid_path,
    get_port_path,
    get_socket_path,
    stop_daemon,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with .ve subdirectory."""
    ve_dir = tmp_path / ".ve"
    ve_dir.mkdir(parents=True)
    return tmp_path


class TestCleanupStateFiles:
    """Tests for _cleanup_state_files helper function."""

    def test_removes_all_files(self, project_dir):
        """Cleanup removes PID, socket, and port files."""
        pid_path = get_pid_path(project_dir)
        socket_path = get_socket_path(project_dir)
        port_path = get_port_path(project_dir)

        # Create all three files
        pid_path.write_text("12345\n")
        socket_path.write_text("")  # Socket file content doesn't matter
        port_path.write_text("8080\n")

        # Verify files exist
        assert pid_path.exists()
        assert socket_path.exists()
        assert port_path.exists()

        # Call cleanup
        _cleanup_state_files(project_dir)

        # Verify all files are removed
        assert not pid_path.exists()
        assert not socket_path.exists()
        assert not port_path.exists()

    def test_handles_missing_files_gracefully(self, project_dir):
        """Cleanup doesn't raise when some files don't exist."""
        pid_path = get_pid_path(project_dir)

        # Only create PID file, leave others missing
        pid_path.write_text("12345\n")

        # Should not raise
        _cleanup_state_files(project_dir)

        # PID file should be removed
        assert not pid_path.exists()

    def test_handles_all_files_missing(self, project_dir):
        """Cleanup doesn't raise when no files exist."""
        # No files created

        # Should not raise
        _cleanup_state_files(project_dir)

    def test_handles_partial_files(self, project_dir):
        """Cleanup handles any combination of existing files."""
        socket_path = get_socket_path(project_dir)
        port_path = get_port_path(project_dir)

        # Only create socket and port, no PID
        socket_path.write_text("")
        port_path.write_text("8080\n")

        # Should not raise
        _cleanup_state_files(project_dir)

        # Existing files should be removed
        assert not socket_path.exists()
        assert not port_path.exists()


class TestStopDaemonCleansAllFiles:
    """Tests for stop_daemon state file cleanup."""

    def test_cleans_all_files_after_sigterm(self, project_dir):
        """stop_daemon cleans up all state files after SIGTERM shutdown."""
        pid_path = get_pid_path(project_dir)
        socket_path = get_socket_path(project_dir)
        port_path = get_port_path(project_dir)

        # Create all state files
        pid_path.write_text(f"{os.getpid()}\n")  # Use a real PID initially
        socket_path.write_text("")
        port_path.write_text("8080\n")

        # Mock the process as running initially, then not running after SIGTERM
        call_count = [0]

        def mock_is_running(pid):
            call_count[0] += 1
            # First call: process exists (to proceed with SIGTERM)
            # Subsequent calls: process exited (SIGTERM worked)
            return call_count[0] <= 1

        with mock.patch("orchestrator.daemon.is_process_running", side_effect=mock_is_running):
            with mock.patch("os.kill") as mock_kill:
                result = stop_daemon(project_dir)

        # Should have sent SIGTERM
        mock_kill.assert_called_once()
        assert mock_kill.call_args[0][1] == signal.SIGTERM

        # All state files should be cleaned up
        assert not pid_path.exists()
        assert not socket_path.exists()
        assert not port_path.exists()

        assert result is True

    def test_cleans_all_files_after_sigkill_fallback(self, project_dir):
        """stop_daemon cleans up all state files after SIGKILL fallback."""
        pid_path = get_pid_path(project_dir)
        socket_path = get_socket_path(project_dir)
        port_path = get_port_path(project_dir)

        # Create all state files
        test_pid = 99999  # Use fake PID
        pid_path.write_text(f"{test_pid}\n")
        socket_path.write_text("")
        port_path.write_text("8080\n")

        # Mock: process running until SIGKILL is sent
        sigkill_sent = [False]

        def mock_is_running(pid):
            # Process dies only after SIGKILL
            return not sigkill_sent[0]

        def mock_kill(pid, sig):
            if sig == signal.SIGKILL:
                sigkill_sent[0] = True

        with mock.patch("orchestrator.daemon.is_process_running", side_effect=mock_is_running):
            with mock.patch("os.kill", side_effect=mock_kill):
                with mock.patch("time.sleep"):  # Speed up the test
                    result = stop_daemon(project_dir, timeout=0.1)

        # All state files should be cleaned up
        assert not pid_path.exists()
        assert not socket_path.exists()
        assert not port_path.exists()

        assert result is True

    def test_cleans_stale_pid_file_and_other_files(self, project_dir):
        """stop_daemon cleans up all files when process not running (stale PID)."""
        pid_path = get_pid_path(project_dir)
        socket_path = get_socket_path(project_dir)
        port_path = get_port_path(project_dir)

        # Create all state files with stale PID
        pid_path.write_text("999999\n")  # Non-existent process
        socket_path.write_text("")
        port_path.write_text("8080\n")

        with mock.patch("orchestrator.daemon.is_process_running", return_value=False):
            result = stop_daemon(project_dir)

        # All state files should be cleaned up
        assert not pid_path.exists()
        assert not socket_path.exists()
        assert not port_path.exists()

        # Returns False because daemon wasn't actually running
        assert result is False
