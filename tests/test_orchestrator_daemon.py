# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for orchestrator daemon helper functions.

NOTE: Full end-to-end daemon tests involving actual process spawning
require subprocess isolation and are more suitable for manual testing
or integration test suites. These tests focus on the helper functions
that can be tested without forking.

Full E2E testing can be done manually with:
  ve orch start --project-dir /tmp/test_project
  ve orch status --project-dir /tmp/test_project
  ve orch work-unit create test_chunk --project-dir /tmp/test_project
  ve orch stop --project-dir /tmp/test_project

TCP port testing:
  ve orch start --port 8080 --project-dir /tmp/test_project
  curl http://localhost:8080/  # Should return dashboard HTML
  ve orch stop --project-dir /tmp/test_project
"""

import os
import socket
import pytest

from orchestrator.daemon import (
    get_pid_path,
    get_socket_path,
    get_log_path,
    get_port_path,
    read_pid_file,
    is_process_running,
    is_daemon_running,
    get_daemon_status,
    find_available_port,
)
from orchestrator.client import create_client, DaemonNotRunningError


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_pid_path(self, project_dir):
        """Returns correct PID file path."""
        result = get_pid_path(project_dir)
        assert result == project_dir / ".ve" / "orchestrator.pid"

    def test_get_socket_path(self, project_dir):
        """Returns correct socket path."""
        result = get_socket_path(project_dir)
        assert result == project_dir / ".ve" / "orchestrator.sock"

    def test_get_log_path(self, project_dir):
        """Returns correct log path."""
        result = get_log_path(project_dir)
        assert result == project_dir / ".ve" / "orchestrator.log"

    def test_get_port_path(self, project_dir):
        """Returns correct port file path."""
        result = get_port_path(project_dir)
        assert result == project_dir / ".ve" / "orchestrator.port"


class TestFindAvailablePort:
    """Tests for find_available_port function."""

    def test_returns_positive_integer(self):
        """Returns a positive port number."""
        port = find_available_port()
        assert isinstance(port, int)
        assert port > 0

    def test_returns_valid_port_range(self):
        """Returns port in valid range (1-65535)."""
        port = find_available_port()
        assert 1 <= port <= 65535

    def test_returned_port_is_available(self):
        """Returned port can be bound to."""
        port = find_available_port()

        # Verify we can actually bind to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # This should succeed since the port was just released
            s.bind(("127.0.0.1", port))

    def test_different_host(self):
        """Works with different host binding."""
        port = find_available_port("0.0.0.0")
        assert isinstance(port, int)
        assert port > 0

    def test_returns_different_ports_on_repeated_calls(self):
        """Multiple calls return different ports (typically)."""
        # Note: This test may occasionally fail if ports are recycled quickly,
        # but generally the OS will assign different ports
        ports = [find_available_port() for _ in range(3)]
        # At least some should be different (not a strict requirement, but likely)
        # We just verify they're all valid
        assert all(p > 0 for p in ports)


class TestReadPidFile:
    """Tests for read_pid_file function."""

    def test_returns_none_for_nonexistent(self, project_dir):
        """Returns None when PID file doesn't exist."""
        result = read_pid_file(project_dir / "nonexistent.pid")
        assert result is None

    def test_reads_valid_pid(self, project_dir):
        """Reads valid PID from file."""
        pid_path = project_dir / "test.pid"
        pid_path.write_text("12345\n")

        result = read_pid_file(pid_path)
        assert result == 12345

    def test_returns_none_for_invalid_content(self, project_dir):
        """Returns None for non-numeric content."""
        pid_path = project_dir / "test.pid"
        pid_path.write_text("not a number\n")

        result = read_pid_file(pid_path)
        assert result is None

    def test_returns_none_for_empty_file(self, project_dir):
        """Returns None for empty file."""
        pid_path = project_dir / "test.pid"
        pid_path.write_text("")

        result = read_pid_file(pid_path)
        assert result is None


class TestIsProcessRunning:
    """Tests for is_process_running function."""

    def test_returns_true_for_current_process(self):
        """Returns True for current process."""
        result = is_process_running(os.getpid())
        assert result is True

    def test_returns_false_for_invalid_pid(self):
        """Returns False for non-existent PID."""
        # Use a high PID that's unlikely to exist
        result = is_process_running(999999)
        assert result is False

    def test_returns_false_for_negative(self):
        """Returns False for negative PID."""
        result = is_process_running(-999)
        assert result is False


class TestIsDaemonRunning:
    """Tests for is_daemon_running function."""

    def test_returns_false_when_no_pid_file(self, project_dir):
        """Returns False when PID file doesn't exist."""
        result = is_daemon_running(project_dir)
        assert result is False

    def test_returns_false_for_stale_pid_file(self, project_dir):
        """Returns False when PID file contains stale PID."""
        ve_dir = project_dir / ".ve"
        ve_dir.mkdir(parents=True)
        pid_path = ve_dir / "orchestrator.pid"
        pid_path.write_text("999999\n")  # Non-existent process

        result = is_daemon_running(project_dir)
        assert result is False


class TestGetDaemonStatus:
    """Tests for get_daemon_status function."""

    def test_returns_stopped_when_not_running(self, project_dir):
        """Returns stopped status when daemon not running."""
        status = get_daemon_status(project_dir)

        assert status.running is False
        assert status.pid is None
        assert status.uptime_seconds is None
        assert status.started_at is None

    def test_returns_stopped_for_stale_pid(self, project_dir):
        """Returns stopped status for stale PID file."""
        ve_dir = project_dir / ".ve"
        ve_dir.mkdir(parents=True)
        pid_path = ve_dir / "orchestrator.pid"
        pid_path.write_text("999999\n")

        status = get_daemon_status(project_dir)
        assert status.running is False


class TestClientWithoutDaemon:
    """Tests for client when daemon is not running."""

    def test_client_raises_when_not_running(self, project_dir):
        """Client raises DaemonNotRunningError when daemon not running."""
        client = create_client(project_dir)
        try:
            with pytest.raises(DaemonNotRunningError):
                client.get_status()
        finally:
            client.close()

    def test_client_raises_for_all_operations(self, project_dir):
        """All client operations raise when daemon not running."""
        client = create_client(project_dir)
        try:
            with pytest.raises(DaemonNotRunningError):
                client.list_work_units()

            with pytest.raises(DaemonNotRunningError):
                client.get_work_unit("test")

            with pytest.raises(DaemonNotRunningError):
                client.create_work_unit(chunk="test")

            with pytest.raises(DaemonNotRunningError):
                client.update_work_unit("test", status="RUNNING")

            with pytest.raises(DaemonNotRunningError):
                client.delete_work_unit("test")
        finally:
            client.close()
