# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_retry_command - Retry command tests
"""Tests for the orchestrator retry endpoints and CLI commands."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from starlette.testclient import TestClient

from orchestrator.api import create_app


@pytest.fixture
def app(tmp_path):
    """Create a test application with a temporary database."""
    return create_app(tmp_path)


@pytest.fixture
def client(app):
    """Create a test client for the API."""
    return TestClient(app)


class TestRetryEndpoint:
    """Tests for POST /work-units/{chunk}/retry endpoint."""

    def test_retry_transitions_to_ready(self, client):
        """Retry transitions NEEDS_ATTENTION work unit to READY."""
        # Create a NEEDS_ATTENTION work unit
        client.post("/work-units", json={
            "chunk": "test_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        # Retry it
        response = client.post("/work-units/test_chunk/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "READY"
        assert data["chunk"] == "test_chunk"

    def test_retry_clears_session_id(self, client, app):
        """Retry clears the session_id field."""
        from orchestrator.models import WorkUnitStatus

        # Create a NEEDS_ATTENTION work unit with session_id
        client.post("/work-units", json={
            "chunk": "session_test",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })
        # Update to add session_id and transition to NEEDS_ATTENTION
        store = app.state.store
        unit = store.get_work_unit("session_test")
        unit.session_id = "dead-session-123"
        unit.status = WorkUnitStatus.NEEDS_ATTENTION
        unit.attention_reason = "Agent crashed"
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Retry
        response = client.post("/work-units/session_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] is None

    def test_retry_clears_attention_reason(self, client):
        """Retry clears the attention_reason field."""
        # Create NEEDS_ATTENTION with reason
        client.post("/work-units", json={
            "chunk": "reason_test",
            "status": "NEEDS_ATTENTION",
            "phase": "PLAN",
        })
        # Set the attention_reason via PATCH
        client.patch("/work-units/reason_test", json={
            "attention_reason": "Agent asked a question",
        })

        # Retry
        response = client.post("/work-units/reason_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["attention_reason"] is None

    def test_retry_resets_api_retry_count(self, client, app):
        """Retry resets api_retry_count to 0."""
        # Create work unit with api_retry_count > 0
        client.post("/work-units", json={
            "chunk": "retry_count_test",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        store = app.state.store
        unit = store.get_work_unit("retry_count_test")
        unit.api_retry_count = 3
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Retry
        response = client.post("/work-units/retry_count_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["api_retry_count"] == 0

    def test_retry_clears_next_retry_at(self, client, app):
        """Retry clears next_retry_at field."""
        # Create work unit with next_retry_at set
        client.post("/work-units", json={
            "chunk": "next_retry_test",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        store = app.state.store
        unit = store.get_work_unit("next_retry_test")
        unit.next_retry_at = datetime.now(timezone.utc)
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Retry
        response = client.post("/work-units/next_retry_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["next_retry_at"] is None

    def test_retry_clears_invalid_worktree(self, client, app):
        """Retry clears worktree field when path doesn't exist."""
        # Create work unit with non-existent worktree path
        client.post("/work-units", json={
            "chunk": "worktree_invalid_test",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        store = app.state.store
        unit = store.get_work_unit("worktree_invalid_test")
        unit.worktree = "/nonexistent/path/that/does/not/exist"
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Retry
        response = client.post("/work-units/worktree_invalid_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["worktree"] is None

    def test_retry_preserves_valid_worktree(self, client, app, tmp_path):
        """Retry preserves worktree field when path exists."""
        # Create a valid worktree path
        worktree_path = tmp_path / "valid_worktree"
        worktree_path.mkdir()

        # Create work unit with valid worktree path
        client.post("/work-units", json={
            "chunk": "worktree_valid_test",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        store = app.state.store
        unit = store.get_work_unit("worktree_valid_test")
        unit.worktree = str(worktree_path)
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Retry
        response = client.post("/work-units/worktree_valid_test/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["worktree"] == str(worktree_path)

    def test_retry_rejects_non_needs_attention(self, client):
        """Retry rejects work units not in NEEDS_ATTENTION status."""
        for status in ["READY", "RUNNING", "BLOCKED", "DONE"]:
            chunk_name = f"reject_{status.lower()}"
            client.post("/work-units", json={
                "chunk": chunk_name,
                "status": status,
                "phase": "IMPLEMENT",
            })

            response = client.post(f"/work-units/{chunk_name}/retry")

            assert response.status_code == 400, f"Expected 400 for status {status}"
            assert "NEEDS_ATTENTION" in response.json()["error"]

    def test_retry_not_found(self, client):
        """Retry returns 404 for non-existent chunk."""
        response = client.post("/work-units/nonexistent_chunk/retry")

        assert response.status_code == 404
        assert "not found" in response.json()["error"]


class TestRetryAllEndpoint:
    """Tests for POST /work-units/retry-all endpoint."""

    def test_retry_all_retries_all_needs_attention(self, client):
        """Retry-all retries all NEEDS_ATTENTION work units."""
        # Create multiple NEEDS_ATTENTION work units
        for i in range(3):
            client.post("/work-units", json={
                "chunk": f"attention_chunk_{i}",
                "status": "NEEDS_ATTENTION",
                "phase": "IMPLEMENT",
            })

        response = client.post("/work-units/retry-all")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["chunks"]) == 3
        assert set(data["chunks"]) == {"attention_chunk_0", "attention_chunk_1", "attention_chunk_2"}

        # Verify all are now READY
        for i in range(3):
            unit_response = client.get(f"/work-units/attention_chunk_{i}")
            assert unit_response.json()["status"] == "READY"

    def test_retry_all_with_phase_filter(self, client):
        """Retry-all with phase filter only retries matching phase."""
        # Create NEEDS_ATTENTION at different phases
        client.post("/work-units", json={
            "chunk": "review_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "REVIEW",
        })
        client.post("/work-units", json={
            "chunk": "implement_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "plan_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "PLAN",
        })

        # Retry only REVIEW phase
        response = client.post("/work-units/retry-all?phase=REVIEW")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["chunks"] == ["review_chunk"]

        # Verify only review_chunk is READY
        assert client.get("/work-units/review_chunk").json()["status"] == "READY"
        assert client.get("/work-units/implement_chunk").json()["status"] == "NEEDS_ATTENTION"
        assert client.get("/work-units/plan_chunk").json()["status"] == "NEEDS_ATTENTION"

    def test_retry_all_skips_other_statuses(self, client):
        """Retry-all only affects NEEDS_ATTENTION work units."""
        # Create work units with various statuses
        client.post("/work-units", json={
            "chunk": "ready_chunk",
            "status": "READY",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "running_chunk",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "attention_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        response = client.post("/work-units/retry-all")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["chunks"] == ["attention_chunk"]

        # Verify other statuses unchanged
        assert client.get("/work-units/ready_chunk").json()["status"] == "READY"
        assert client.get("/work-units/running_chunk").json()["status"] == "RUNNING"

    def test_retry_all_returns_count_and_chunks(self, client):
        """Retry-all returns count and list of chunk names."""
        client.post("/work-units", json={
            "chunk": "chunk_a",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "chunk_b",
            "status": "NEEDS_ATTENTION",
            "phase": "PLAN",
        })

        response = client.post("/work-units/retry-all")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "chunks" in data
        assert data["count"] == 2
        assert set(data["chunks"]) == {"chunk_a", "chunk_b"}

    def test_retry_all_empty_returns_zero(self, client):
        """Retry-all returns zero count when no NEEDS_ATTENTION work units."""
        # Create work units with other statuses
        client.post("/work-units", json={
            "chunk": "ready_chunk",
            "status": "READY",
            "phase": "IMPLEMENT",
        })

        response = client.post("/work-units/retry-all")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["chunks"] == []

    def test_retry_all_invalid_phase_returns_error(self, client):
        """Retry-all with invalid phase filter returns 400."""
        response = client.post("/work-units/retry-all?phase=INVALID_PHASE")

        assert response.status_code == 400
        assert "Invalid phase" in response.json()["error"]

    def test_retry_all_clears_state_for_each(self, client, app):
        """Retry-all clears session_id and attention_reason for all retried units."""
        # Create NEEDS_ATTENTION work units with various state
        client.post("/work-units", json={
            "chunk": "state_test_1",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "state_test_2",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        store = app.state.store
        for chunk_name in ["state_test_1", "state_test_2"]:
            unit = store.get_work_unit(chunk_name)
            unit.session_id = f"session-{chunk_name}"
            unit.attention_reason = f"Reason for {chunk_name}"
            unit.api_retry_count = 2
            unit.updated_at = datetime.now(timezone.utc)
            store.update_work_unit(unit)

        # Retry all
        response = client.post("/work-units/retry-all")

        assert response.status_code == 200
        assert response.json()["count"] == 2

        # Verify state was cleared
        for chunk_name in ["state_test_1", "state_test_2"]:
            unit_response = client.get(f"/work-units/{chunk_name}")
            data = unit_response.json()
            assert data["session_id"] is None
            assert data["attention_reason"] is None
            assert data["api_retry_count"] == 0
