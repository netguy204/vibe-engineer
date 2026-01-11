# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
"""Tests for the orchestrator HTTP API."""

import pytest
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


class TestStatusEndpoint:
    """Tests for GET /status endpoint."""

    def test_returns_status_info(self, client):
        """Status endpoint returns daemon information."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert data["running"] is True
        assert data["pid"] is not None
        assert "uptime_seconds" in data
        assert "work_unit_counts" in data
        assert data["version"] == "0.1.0"

    def test_work_unit_counts_empty_initially(self, client):
        """Work unit counts are empty when no work units exist."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert data["work_unit_counts"] == {}

    def test_work_unit_counts_after_creation(self, client):
        """Work unit counts reflect created units."""
        # Create some work units
        client.post("/work-units", json={"chunk": "chunk_1", "status": "READY"})
        client.post("/work-units", json={"chunk": "chunk_2", "status": "READY"})
        client.post("/work-units", json={"chunk": "chunk_3", "status": "RUNNING"})

        response = client.get("/status")
        data = response.json()

        assert data["work_unit_counts"]["READY"] == 2
        assert data["work_unit_counts"]["RUNNING"] == 1


class TestListWorkUnitsEndpoint:
    """Tests for GET /work-units endpoint."""

    def test_returns_empty_list_initially(self, client):
        """Returns empty list when no work units exist."""
        response = client.get("/work-units")

        assert response.status_code == 200
        data = response.json()

        assert data["work_units"] == []
        assert data["count"] == 0

    def test_lists_all_work_units(self, client):
        """Lists all work units."""
        client.post("/work-units", json={"chunk": "chunk_1"})
        client.post("/work-units", json={"chunk": "chunk_2"})

        response = client.get("/work-units")
        data = response.json()

        assert data["count"] == 2
        chunks = [u["chunk"] for u in data["work_units"]]
        assert "chunk_1" in chunks
        assert "chunk_2" in chunks

    def test_filters_by_status(self, client):
        """Filters work units by status."""
        client.post("/work-units", json={"chunk": "ready_chunk", "status": "READY"})
        client.post("/work-units", json={"chunk": "running_chunk", "status": "RUNNING"})

        response = client.get("/work-units?status=READY")
        data = response.json()

        assert data["count"] == 1
        assert data["work_units"][0]["chunk"] == "ready_chunk"

    def test_invalid_status_filter_returns_error(self, client):
        """Invalid status filter returns error."""
        response = client.get("/work-units?status=INVALID")

        assert response.status_code == 400
        assert "Invalid status" in response.json()["error"]


class TestGetWorkUnitEndpoint:
    """Tests for GET /work-units/{chunk} endpoint."""

    def test_returns_work_unit(self, client):
        """Returns work unit details."""
        client.post("/work-units", json={
            "chunk": "test_chunk",
            "phase": "PLAN",
            "status": "RUNNING",
        })

        response = client.get("/work-units/test_chunk")

        assert response.status_code == 200
        data = response.json()

        assert data["chunk"] == "test_chunk"
        assert data["phase"] == "PLAN"
        assert data["status"] == "RUNNING"

    def test_not_found(self, client):
        """Returns 404 for non-existent work unit."""
        response = client.get("/work-units/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["error"]


class TestCreateWorkUnitEndpoint:
    """Tests for POST /work-units endpoint."""

    def test_creates_work_unit_with_defaults(self, client):
        """Creates work unit with default values."""
        response = client.post("/work-units", json={"chunk": "new_chunk"})

        assert response.status_code == 201
        data = response.json()

        assert data["chunk"] == "new_chunk"
        assert data["phase"] == "GOAL"  # default
        assert data["status"] == "READY"  # default
        assert data["blocked_by"] == []

    def test_creates_work_unit_with_all_fields(self, client):
        """Creates work unit with all fields specified."""
        response = client.post("/work-units", json={
            "chunk": "full_chunk",
            "phase": "IMPLEMENT",
            "status": "BLOCKED",
            "blocked_by": ["dep_a", "dep_b"],
            "worktree": "/path/to/worktree",
        })

        assert response.status_code == 201
        data = response.json()

        assert data["chunk"] == "full_chunk"
        assert data["phase"] == "IMPLEMENT"
        assert data["status"] == "BLOCKED"
        assert data["blocked_by"] == ["dep_a", "dep_b"]
        assert data["worktree"] == "/path/to/worktree"

    def test_missing_chunk_returns_error(self, client):
        """Returns error when chunk is missing."""
        response = client.post("/work-units", json={"phase": "GOAL"})

        assert response.status_code == 400
        assert "Missing required field" in response.json()["error"]

    def test_invalid_phase_returns_error(self, client):
        """Returns error for invalid phase."""
        response = client.post("/work-units", json={
            "chunk": "bad_phase",
            "phase": "INVALID",
        })

        assert response.status_code == 400
        assert "Invalid phase" in response.json()["error"]

    def test_invalid_status_returns_error(self, client):
        """Returns error for invalid status."""
        response = client.post("/work-units", json={
            "chunk": "bad_status",
            "status": "INVALID",
        })

        assert response.status_code == 400
        assert "Invalid status" in response.json()["error"]

    def test_duplicate_returns_conflict(self, client):
        """Returns 409 conflict for duplicate chunk."""
        client.post("/work-units", json={"chunk": "dup_chunk"})

        response = client.post("/work-units", json={"chunk": "dup_chunk"})

        assert response.status_code == 409
        assert "already exists" in response.json()["error"]

    def test_invalid_json_returns_error(self, client):
        """Returns error for invalid JSON."""
        response = client.post(
            "/work-units",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]


class TestUpdateWorkUnitEndpoint:
    """Tests for PATCH /work-units/{chunk} endpoint."""

    def test_updates_status(self, client):
        """Updates work unit status."""
        client.post("/work-units", json={"chunk": "update_chunk"})

        response = client.patch("/work-units/update_chunk", json={"status": "RUNNING"})

        assert response.status_code == 200
        assert response.json()["status"] == "RUNNING"

    def test_updates_phase(self, client):
        """Updates work unit phase."""
        client.post("/work-units", json={"chunk": "phase_chunk"})

        response = client.patch("/work-units/phase_chunk", json={"phase": "PLAN"})

        assert response.status_code == 200
        assert response.json()["phase"] == "PLAN"

    def test_updates_blocked_by(self, client):
        """Updates blocked_by list."""
        client.post("/work-units", json={"chunk": "blocked_chunk"})

        response = client.patch("/work-units/blocked_chunk", json={
            "blocked_by": ["dep_chunk"],
        })

        assert response.status_code == 200
        assert response.json()["blocked_by"] == ["dep_chunk"]

    def test_updates_worktree(self, client):
        """Updates worktree path."""
        client.post("/work-units", json={"chunk": "wt_chunk"})

        response = client.patch("/work-units/wt_chunk", json={
            "worktree": "/new/worktree",
        })

        assert response.status_code == 200
        assert response.json()["worktree"] == "/new/worktree"

    def test_updates_multiple_fields(self, client):
        """Updates multiple fields at once."""
        client.post("/work-units", json={"chunk": "multi_chunk"})

        response = client.patch("/work-units/multi_chunk", json={
            "phase": "IMPLEMENT",
            "status": "RUNNING",
            "worktree": "/worktree",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "IMPLEMENT"
        assert data["status"] == "RUNNING"
        assert data["worktree"] == "/worktree"

    def test_not_found(self, client):
        """Returns 404 for non-existent work unit."""
        response = client.patch("/work-units/nonexistent", json={"status": "RUNNING"})

        assert response.status_code == 404

    def test_invalid_status_returns_error(self, client):
        """Returns error for invalid status."""
        client.post("/work-units", json={"chunk": "bad_update"})

        response = client.patch("/work-units/bad_update", json={"status": "INVALID"})

        assert response.status_code == 400
        assert "Invalid status" in response.json()["error"]

    def test_invalid_blocked_by_returns_error(self, client):
        """Returns error when blocked_by is not a list."""
        client.post("/work-units", json={"chunk": "bad_blocked"})

        response = client.patch("/work-units/bad_blocked", json={
            "blocked_by": "not_a_list",
        })

        assert response.status_code == 400
        assert "blocked_by must be a list" in response.json()["error"]


class TestDeleteWorkUnitEndpoint:
    """Tests for DELETE /work-units/{chunk} endpoint."""

    def test_deletes_work_unit(self, client):
        """Deletes work unit."""
        client.post("/work-units", json={"chunk": "delete_chunk"})

        response = client.delete("/work-units/delete_chunk")

        assert response.status_code == 200
        assert response.json()["deleted"] is True
        assert response.json()["chunk"] == "delete_chunk"

        # Verify deleted
        get_response = client.get("/work-units/delete_chunk")
        assert get_response.status_code == 404

    def test_not_found(self, client):
        """Returns 404 for non-existent work unit."""
        response = client.delete("/work-units/nonexistent")

        assert response.status_code == 404


class TestStatusHistoryEndpoint:
    """Tests for GET /work-units/{chunk}/history endpoint."""

    def test_returns_initial_status(self, client):
        """Returns initial status in history."""
        client.post("/work-units", json={"chunk": "history_chunk"})

        response = client.get("/work-units/history_chunk/history")

        assert response.status_code == 200
        data = response.json()

        assert data["chunk"] == "history_chunk"
        assert len(data["history"]) == 1
        assert data["history"][0]["old_status"] is None
        assert data["history"][0]["new_status"] == "READY"

    def test_returns_status_transitions(self, client):
        """Returns all status transitions."""
        client.post("/work-units", json={"chunk": "trans_chunk"})
        client.patch("/work-units/trans_chunk", json={"status": "RUNNING"})
        client.patch("/work-units/trans_chunk", json={"status": "DONE"})

        response = client.get("/work-units/trans_chunk/history")
        data = response.json()

        assert len(data["history"]) == 3
        assert data["history"][0]["new_status"] == "READY"
        assert data["history"][1]["old_status"] == "READY"
        assert data["history"][1]["new_status"] == "RUNNING"
        assert data["history"][2]["old_status"] == "RUNNING"
        assert data["history"][2]["new_status"] == "DONE"

    def test_not_found(self, client):
        """Returns 404 for non-existent work unit."""
        response = client.get("/work-units/nonexistent/history")

        assert response.status_code == 404
