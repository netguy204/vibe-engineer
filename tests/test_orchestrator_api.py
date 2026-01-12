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


# Chunk: docs/chunks/orch_inject_validate - Tests for inject endpoint validation
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


# Chunk: docs/chunks/orch_attention_queue - Attention queue API tests
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
