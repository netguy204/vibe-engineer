# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
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


class TestInjectEndpointValidation:
    """Tests for POST /work-units/inject endpoint with validation."""

    @pytest.fixture
    def app_with_chunks(self, tmp_path):
        """Create a test application with a chunks directory."""
        # Create docs/chunks directory
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        return create_app(tmp_path)

    @pytest.fixture
    def client_with_chunks(self, app_with_chunks):
        """Create a test client with chunk support."""
        return TestClient(app_with_chunks)

    def _create_chunk(self, tmp_path, chunk_name: str, status: str, has_plan_content: bool = True):
        """Helper to create a chunk with GOAL.md and optionally PLAN.md."""
        chunk_dir = tmp_path / "docs" / "chunks" / chunk_name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        # Write GOAL.md with frontmatter
        goal_path = chunk_dir / "GOAL.md"
        goal_path.write_text(f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
created_after: []
---

# Chunk Goal

Test chunk content.
""")

        # Write PLAN.md
        plan_path = chunk_dir / "PLAN.md"
        if has_plan_content:
            plan_path.write_text("""# Implementation Plan

## Approach

This is a real implementation approach with actual content.

## Sequence

### Step 1: Do the thing

Details about doing the thing.
""")
        else:
            # Template-only content
            plan_path.write_text("""# Implementation Plan

## Approach

<!--
Template comment only.
-->

## Sequence

<!--
Steps here.
-->
""")

    def test_inject_nonexistent_chunk_returns_error(self, client_with_chunks, tmp_path):
        """Inject endpoint returns error for non-existent chunk."""
        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "nonexistent_chunk"}
        )

        assert response.status_code == 400
        assert "not found" in response.json()["error"].lower()

    def test_inject_implementing_chunk_without_plan_returns_error(self, client_with_chunks, tmp_path):
        """IMPLEMENTING chunk without populated plan fails validation."""
        self._create_chunk(tmp_path, "implementing_no_plan", "IMPLEMENTING", has_plan_content=False)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "implementing_no_plan"}
        )

        assert response.status_code == 400
        assert "IMPLEMENTING" in response.json()["error"]

    def test_inject_implementing_chunk_with_plan_succeeds(self, client_with_chunks, tmp_path):
        """IMPLEMENTING chunk with populated plan passes validation."""
        self._create_chunk(tmp_path, "implementing_with_plan", "IMPLEMENTING", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "implementing_with_plan"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["chunk"] == "implementing_with_plan"
        assert data["status"] == "READY"

    def test_inject_future_chunk_succeeds_with_warnings(self, client_with_chunks, tmp_path):
        """FUTURE chunk with empty plan succeeds but includes warnings."""
        self._create_chunk(tmp_path, "future_chunk", "FUTURE", has_plan_content=False)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "future_chunk"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["chunk"] == "future_chunk"
        # Should have warnings about starting with PLAN phase
        assert "warnings" in data
        assert any("FUTURE" in w for w in data["warnings"])

    def test_inject_active_chunk_without_plan_returns_error(self, client_with_chunks, tmp_path):
        """ACTIVE chunk without populated plan fails validation."""
        self._create_chunk(tmp_path, "active_no_plan", "ACTIVE", has_plan_content=False)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "active_no_plan"}
        )

        assert response.status_code == 400
        assert "ACTIVE" in response.json()["error"]

    def test_inject_superseded_chunk_returns_error(self, client_with_chunks, tmp_path):
        """SUPERSEDED chunk cannot be injected."""
        self._create_chunk(tmp_path, "superseded_chunk", "SUPERSEDED", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "superseded_chunk"}
        )

        assert response.status_code == 400
        error = response.json()["error"].lower()
        assert "terminal" in error or "superseded" in error

    def test_inject_historical_chunk_returns_error(self, client_with_chunks, tmp_path):
        """HISTORICAL chunk cannot be injected."""
        self._create_chunk(tmp_path, "historical_chunk", "HISTORICAL", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "historical_chunk"}
        )

        assert response.status_code == 400
        error = response.json()["error"].lower()
        assert "terminal" in error or "historical" in error

    def test_inject_duplicate_returns_conflict(self, client_with_chunks, tmp_path):
        """Injecting same chunk twice returns conflict."""
        self._create_chunk(tmp_path, "dup_chunk", "IMPLEMENTING", has_plan_content=True)

        # First inject succeeds
        response1 = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "dup_chunk"}
        )
        assert response1.status_code == 201

        # Second inject fails with conflict
        response2 = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "dup_chunk"}
        )
        assert response2.status_code == 409
        assert "already exists" in response2.json()["error"]

    def test_inject_with_priority(self, client_with_chunks, tmp_path):
        """Inject with custom priority."""
        self._create_chunk(tmp_path, "priority_chunk", "IMPLEMENTING", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "priority_chunk", "priority": 10}
        )

        assert response.status_code == 201
        assert response.json()["priority"] == 10

    def test_inject_detects_initial_phase_plan(self, client_with_chunks, tmp_path):
        """Inject detects PLAN phase when GOAL.md exists but PLAN.md is empty."""
        self._create_chunk(tmp_path, "plan_phase", "FUTURE", has_plan_content=False)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "plan_phase"}
        )

        assert response.status_code == 201
        assert response.json()["phase"] == "PLAN"

    def test_inject_detects_initial_phase_implement(self, client_with_chunks, tmp_path):
        """Inject detects IMPLEMENT phase when both GOAL.md and PLAN.md have content."""
        self._create_chunk(tmp_path, "impl_phase", "IMPLEMENTING", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "impl_phase"}
        )

        assert response.status_code == 201
        assert response.json()["phase"] == "IMPLEMENT"

    def test_inject_with_explicit_phase_override(self, client_with_chunks, tmp_path):
        """Inject with explicit phase overrides detection."""
        self._create_chunk(tmp_path, "override_phase", "IMPLEMENTING", has_plan_content=True)

        response = client_with_chunks.post(
            "/work-units/inject",
            json={"chunk": "override_phase", "phase": "PLAN"}
        )

        assert response.status_code == 201
        assert response.json()["phase"] == "PLAN"


class TestAttentionEndpoint:
    """Tests for GET /attention endpoint."""

    def test_returns_empty_initially(self, client):
        """Returns empty list when no NEEDS_ATTENTION work units."""
        response = client.get("/attention")

        assert response.status_code == 200
        data = response.json()
        assert data["attention_items"] == []
        assert data["count"] == 0

    def test_returns_needs_attention_items(self, client):
        """Returns NEEDS_ATTENTION work units with enriched data."""
        # Create a NEEDS_ATTENTION work unit
        client.post("/work-units", json={
            "chunk": "attention_chunk",
            "phase": "PLAN",
            "status": "NEEDS_ATTENTION",
        })

        response = client.get("/attention")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        item = data["attention_items"][0]
        assert item["chunk"] == "attention_chunk"
        assert item["phase"] == "PLAN"
        assert item["status"] == "NEEDS_ATTENTION"
        assert "blocks_count" in item
        assert "time_waiting" in item
        # goal_summary may be None if chunk directory doesn't exist

    def test_excludes_non_needs_attention(self, client):
        """Only NEEDS_ATTENTION work units are returned."""
        # Create work units with various statuses
        client.post("/work-units", json={"chunk": "ready_chunk", "status": "READY"})
        client.post("/work-units", json={"chunk": "running_chunk", "status": "RUNNING"})
        client.post("/work-units", json={"chunk": "attention_chunk", "status": "NEEDS_ATTENTION"})

        response = client.get("/attention")
        data = response.json()

        assert data["count"] == 1
        assert data["attention_items"][0]["chunk"] == "attention_chunk"


class TestAnswerEndpoint:
    """Tests for POST /work-units/{chunk}/answer endpoint."""

    def test_answers_and_transitions_to_ready(self, client):
        """Answer stores pending_answer and transitions to READY."""
        # Create a NEEDS_ATTENTION work unit
        client.post("/work-units", json={
            "chunk": "question_chunk",
            "phase": "PLAN",
            "status": "NEEDS_ATTENTION",
        })

        # Submit answer
        response = client.post("/work-units/question_chunk/answer", json={
            "answer": "Use JWT for authentication",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["chunk"] == "question_chunk"
        assert data["status"] == "READY"
        assert data["pending_answer"] == "Use JWT for authentication"
        assert data["attention_reason"] is None  # Cleared

    def test_rejects_wrong_status(self, client):
        """Returns error if work unit is not NEEDS_ATTENTION."""
        # Create a READY work unit
        client.post("/work-units", json={"chunk": "ready_chunk", "status": "READY"})

        response = client.post("/work-units/ready_chunk/answer", json={
            "answer": "Some answer",
        })

        assert response.status_code == 400
        assert "not in NEEDS_ATTENTION state" in response.json()["error"]

    def test_not_found(self, client):
        """Returns 404 for unknown chunk."""
        response = client.post("/work-units/nonexistent/answer", json={
            "answer": "Some answer",
        })

        assert response.status_code == 404

    def test_missing_answer_field(self, client):
        """Returns error when answer field is missing."""
        client.post("/work-units", json={
            "chunk": "question_chunk",
            "status": "NEEDS_ATTENTION",
        })

        response = client.post("/work-units/question_chunk/answer", json={})

        assert response.status_code == 400
        assert "Missing required field: answer" in response.json()["error"]

    def test_answer_must_be_string(self, client):
        """Returns error when answer is not a string."""
        client.post("/work-units", json={
            "chunk": "question_chunk",
            "status": "NEEDS_ATTENTION",
        })

        response = client.post("/work-units/question_chunk/answer", json={
            "answer": 12345,
        })

        assert response.status_code == 400
        assert "must be a string" in response.json()["error"]

    def test_invalid_json(self, client):
        """Returns error for invalid JSON."""
        client.post("/work-units", json={
            "chunk": "question_chunk",
            "status": "NEEDS_ATTENTION",
        })

        response = client.post(
            "/work-units/question_chunk/answer",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]


class TestResolveConflictEndpoint:
    """Tests for POST /work-units/{chunk}/resolve endpoint."""

    def test_serialize_verdict_transitions_to_blocked(self, client):
        """SERIALIZE verdict transitions status from NEEDS_ATTENTION to BLOCKED."""
        # Create a work unit in NEEDS_ATTENTION state (simulating conflict detection)
        client.post("/work-units", json={
            "chunk": "chunk_a",
            "status": "NEEDS_ATTENTION",
        })

        # Create the other chunk that we'll serialize after
        client.post("/work-units", json={
            "chunk": "chunk_b",
            "status": "RUNNING",
        })

        # Resolve with SERIALIZE verdict
        response = client.post("/work-units/chunk_a/resolve", json={
            "other_chunk": "chunk_b",
            "verdict": "serialize",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "SERIALIZE"
        assert "chunk_b" in data["blocked_by"]

        # Verify the work unit status is now BLOCKED
        get_response = client.get("/work-units/chunk_a")
        assert get_response.status_code == 200
        unit = get_response.json()
        assert unit["status"] == "BLOCKED"

    def test_serialize_verdict_clears_attention_reason(self, client):
        """SERIALIZE verdict clears the attention_reason field."""
        # Create a work unit in NEEDS_ATTENTION state with attention_reason
        create_response = client.post("/work-units", json={
            "chunk": "chunk_a",
            "status": "NEEDS_ATTENTION",
        })

        # Set attention_reason via PATCH
        client.patch("/work-units/chunk_a", json={
            "attention_reason": "Conflict with chunk_b: overlapping files",
        })

        # Create the other chunk
        client.post("/work-units", json={
            "chunk": "chunk_b",
            "status": "RUNNING",
        })

        # Resolve with SERIALIZE verdict
        response = client.post("/work-units/chunk_a/resolve", json={
            "other_chunk": "chunk_b",
            "verdict": "serialize",
        })

        assert response.status_code == 200

        # Verify attention_reason is cleared
        get_response = client.get("/work-units/chunk_a")
        unit = get_response.json()
        assert unit["attention_reason"] is None

    def test_resolve_endpoint_returns_error_for_invalid_verdict(self, client):
        """Returns error for invalid verdict."""
        # Create work units
        client.post("/work-units", json={"chunk": "chunk_a", "status": "NEEDS_ATTENTION"})
        client.post("/work-units", json={"chunk": "chunk_b", "status": "RUNNING"})

        response = client.post("/work-units/chunk_a/resolve", json={
            "other_chunk": "chunk_b",
            "verdict": "invalid",
        })

        assert response.status_code == 400
        assert "verdict" in response.json()["error"].lower()

    def test_resolve_endpoint_returns_error_for_unknown_chunk(self, client):
        """Returns 404 for unknown chunk."""
        response = client.post("/work-units/nonexistent/resolve", json={
            "other_chunk": "chunk_b",
            "verdict": "serialize",
        })

        assert response.status_code == 404


class TestBlockedLifecycleIntegration:
    """Integration tests for the full blocked work unit lifecycle.

    These tests verify the complete flow:
    1. Work unit detects conflict
    2. Operator resolves with SERIALIZE verdict
    3. Work unit transitions to BLOCKED
    4. Blocker completes
    5. Work unit automatically transitions to READY
    """

    @pytest.fixture
    def scheduler_app(self, tmp_path):
        """Create a test application with a real scheduler for integration tests."""
        from orchestrator.api import create_app
        from orchestrator.state import StateStore, get_default_db_path
        from orchestrator.scheduler import Scheduler
        from orchestrator.models import OrchestratorConfig
        from unittest.mock import MagicMock, AsyncMock

        app = create_app(tmp_path)

        # Get the state store from the app
        db_path = get_default_db_path(tmp_path)
        store = StateStore(db_path)
        store.initialize()

        # Create mock worktree manager and agent runner
        mock_worktree_manager = MagicMock()
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        mock_agent_runner = MagicMock()
        mock_agent_runner.run_phase = AsyncMock()

        config = OrchestratorConfig(max_agents=2, dispatch_interval_seconds=0.1)

        scheduler = Scheduler(
            store=store,
            worktree_manager=mock_worktree_manager,
            agent_runner=mock_agent_runner,
            config=config,
            project_dir=tmp_path,
        )

        return app, store, scheduler, tmp_path

    def test_full_blocked_lifecycle_flow(self, scheduler_app):
        """Test complete flow: conflict → SERIALIZE → BLOCKED → completion → READY."""
        import asyncio
        from datetime import datetime, timezone
        from orchestrator.models import WorkUnit, WorkUnitPhase, WorkUnitStatus
        from starlette.testclient import TestClient

        app, store, scheduler, tmp_path = scheduler_app
        client = TestClient(app)

        # Set up chunk directories for the scheduler
        for chunk_name in ["chunk_a", "chunk_b"]:
            chunk_dir = tmp_path / "docs" / "chunks" / chunk_name
            chunk_dir.mkdir(parents=True, exist_ok=True)
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: ACTIVE
---

# {chunk_name}
"""
            )

        # Step 1: Create two work units - chunk_a is RUNNING, chunk_b is NEEDS_ATTENTION
        # (simulating conflict detection put chunk_b in NEEDS_ATTENTION)
        response_a = client.post("/work-units", json={
            "chunk": "chunk_a",
            "phase": "COMPLETE",
            "status": "RUNNING",
        })
        assert response_a.status_code == 201

        response_b = client.post("/work-units", json={
            "chunk": "chunk_b",
            "phase": "PLAN",
            "status": "NEEDS_ATTENTION",
        })
        assert response_b.status_code == 201

        # Step 2: Operator resolves conflict - serialize chunk_b after chunk_a
        resolve_response = client.post("/work-units/chunk_b/resolve", json={
            "other_chunk": "chunk_a",
            "verdict": "serialize",
        })
        assert resolve_response.status_code == 200
        assert resolve_response.json()["verdict"] == "SERIALIZE"

        # Step 3: Verify chunk_b is now BLOCKED
        get_b = client.get("/work-units/chunk_b")
        assert get_b.json()["status"] == "BLOCKED"
        assert "chunk_a" in get_b.json()["blocked_by"]

        # Step 4: Simulate chunk_a completing via scheduler's _advance_phase
        # Get the work unit from store
        work_unit_a = store.get_work_unit("chunk_a")

        # Run _advance_phase to transition chunk_a to DONE
        asyncio.run(scheduler._advance_phase(work_unit_a))

        # Step 5: Verify chunk_a is DONE
        get_a_done = client.get("/work-units/chunk_a")
        assert get_a_done.json()["status"] == "DONE"

        # Step 6: Verify chunk_b is now READY (automatically unblocked)
        get_b_ready = client.get("/work-units/chunk_b")
        assert get_b_ready.json()["status"] == "READY"
        assert "chunk_a" not in get_b_ready.json()["blocked_by"]