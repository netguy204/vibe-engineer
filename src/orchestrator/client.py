# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_attention_queue - Attention queue client methods
"""HTTP client for communicating with the orchestrator daemon.

Provides a Python interface for CLI commands to interact with the daemon.
"""

from pathlib import Path
from typing import Optional

import httpx

from orchestrator.daemon import get_socket_path, is_daemon_running


class OrchestratorClientError(Exception):
    """Exception raised for client-related errors."""

    pass


class DaemonNotRunningError(OrchestratorClientError):
    """Exception raised when the daemon is not running."""

    pass


class OrchestratorClient:
    """HTTP client for the orchestrator daemon.

    Handles communication with the daemon via Unix domain socket.
    """

    def __init__(self, project_dir: Path, timeout: float = 10.0):
        """Initialize the client.

        Args:
            project_dir: The project directory
            timeout: Request timeout in seconds
        """
        self.project_dir = project_dir
        self.socket_path = get_socket_path(project_dir)
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _ensure_running(self) -> None:
        """Ensure the daemon is running.

        Raises:
            DaemonNotRunningError: If daemon is not running
        """
        if not is_daemon_running(self.project_dir):
            raise DaemonNotRunningError(
                "Orchestrator daemon is not running. Start it with: ve orch start"
            )

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            # Create transport for Unix socket
            transport = httpx.HTTPTransport(uds=str(self.socket_path))
            self._client = httpx.Client(
                transport=transport,
                base_url="http://localhost",  # Required but ignored for UDS
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an HTTP request to the daemon.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: API path
            json: Optional JSON body
            params: Optional query parameters

        Returns:
            Response JSON as dict

        Raises:
            DaemonNotRunningError: If daemon is not running
            OrchestratorClientError: If request fails
        """
        self._ensure_running()

        try:
            client = self._get_client()
            response = client.request(method, path, json=json, params=params)

            # Parse response
            try:
                data = response.json()
            except Exception:
                raise OrchestratorClientError(
                    f"Invalid response from daemon: {response.text}"
                )

            # Check for errors
            if response.status_code >= 400:
                error_msg = data.get("error", f"HTTP {response.status_code}")
                raise OrchestratorClientError(error_msg)

            return data

        except httpx.ConnectError:
            raise DaemonNotRunningError(
                "Cannot connect to orchestrator daemon. Is it running?"
            )
        except httpx.TimeoutException:
            raise OrchestratorClientError("Request to daemon timed out")

    # Status

    def get_status(self) -> dict:
        """Get daemon status.

        Returns:
            Daemon status information
        """
        return self._request("GET", "/status")

    # Work Units

    def list_work_units(self, status: Optional[str] = None) -> dict:
        """List all work units.

        Args:
            status: Optional status filter

        Returns:
            Dict with work_units list and count
        """
        params = {"status": status} if status else None
        return self._request("GET", "/work-units", params=params)

    def get_work_unit(self, chunk: str) -> dict:
        """Get a specific work unit.

        Args:
            chunk: Chunk name

        Returns:
            Work unit details
        """
        return self._request("GET", f"/work-units/{chunk}")

    def create_work_unit(
        self,
        chunk: str,
        phase: str = "GOAL",
        status: str = "READY",
        blocked_by: Optional[list[str]] = None,
        worktree: Optional[str] = None,
    ) -> dict:
        """Create a new work unit.

        Args:
            chunk: Chunk name
            phase: Initial phase (default: GOAL)
            status: Initial status (default: READY)
            blocked_by: List of blocking chunks
            worktree: Git worktree path

        Returns:
            Created work unit details
        """
        body = {
            "chunk": chunk,
            "phase": phase,
            "status": status,
        }
        if blocked_by:
            body["blocked_by"] = blocked_by
        if worktree:
            body["worktree"] = worktree

        return self._request("POST", "/work-units", json=body)

    def update_work_unit(
        self,
        chunk: str,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        blocked_by: Optional[list[str]] = None,
        worktree: Optional[str] = None,
    ) -> dict:
        """Update a work unit.

        Args:
            chunk: Chunk name
            phase: New phase (optional)
            status: New status (optional)
            blocked_by: New blocked_by list (optional)
            worktree: New worktree path (optional)

        Returns:
            Updated work unit details
        """
        body = {}
        if phase is not None:
            body["phase"] = phase
        if status is not None:
            body["status"] = status
        if blocked_by is not None:
            body["blocked_by"] = blocked_by
        if worktree is not None:
            body["worktree"] = worktree

        return self._request("PATCH", f"/work-units/{chunk}", json=body)

    def delete_work_unit(self, chunk: str) -> dict:
        """Delete a work unit.

        Args:
            chunk: Chunk name

        Returns:
            Deletion confirmation
        """
        return self._request("DELETE", f"/work-units/{chunk}")

    def get_status_history(self, chunk: str) -> dict:
        """Get status transition history for a work unit.

        Args:
            chunk: Chunk name

        Returns:
            Status history
        """
        return self._request("GET", f"/work-units/{chunk}/history")

    # Attention queue methods

    def get_attention_queue(self) -> dict:
        """Get the prioritized attention queue.

        Returns:
            Dict with attention_items list and count
        """
        return self._request("GET", "/attention")

    def answer_work_unit(self, chunk: str, answer: str) -> dict:
        """Submit an answer to a NEEDS_ATTENTION work unit.

        Args:
            chunk: Chunk name
            answer: Operator's answer text

        Returns:
            Updated work unit details
        """
        return self._request(
            "POST",
            f"/work-units/{chunk}/answer",
            json={"answer": answer},
        )


def create_client(project_dir: Path, timeout: float = 10.0) -> OrchestratorClient:
    """Create an orchestrator client.

    Args:
        project_dir: The project directory
        timeout: Request timeout in seconds

    Returns:
        Configured OrchestratorClient
    """
    return OrchestratorClient(project_dir, timeout=timeout)
