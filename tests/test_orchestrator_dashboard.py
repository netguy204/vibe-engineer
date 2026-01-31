# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_dashboard - Dashboard integration tests
"""Tests for the orchestrator web dashboard and WebSocket support."""

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


class TestDashboardEndpoint:
    """Tests for GET / dashboard endpoint."""

    def test_dashboard_renders_html(self, client):
        """Dashboard endpoint returns HTML content."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE html>" in response.text
        assert "Orchestrator Dashboard" in response.text

    def test_dashboard_shows_empty_state(self, client):
        """Dashboard shows empty state when no work units exist."""
        response = client.get("/")

        assert response.status_code == 200
        assert "No items need attention" in response.text
        assert "No work units in the system" in response.text

    def test_dashboard_shows_attention_items(self, client):
        """Dashboard displays attention queue items."""
        # Create a work unit needing attention
        client.post("/work-units", json={
            "chunk": "test_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "test_chunk" in response.text
        assert "IMPLEMENT" in response.text

    def test_dashboard_shows_work_unit_grid(self, client):
        """Dashboard displays work unit status grid."""
        # Create work units in different states
        client.post("/work-units", json={
            "chunk": "running_chunk",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })
        client.post("/work-units", json={
            "chunk": "ready_chunk",
            "status": "READY",
            "phase": "PLAN",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "running_chunk" in response.text
        assert "ready_chunk" in response.text
        # Check for status groupings
        assert "Running" in response.text
        assert "Ready" in response.text


class TestWebSocketEndpoint:
    """Tests for WebSocket /ws endpoint."""

    def test_websocket_connects(self, client):
        """WebSocket endpoint accepts connections."""
        with client.websocket_connect("/ws") as websocket:
            # Connection should succeed
            # Receive initial state message
            data = websocket.receive_json()
            assert data["type"] == "initial_state"
            assert "work_units" in data["data"]
            assert "attention_items" in data["data"]

    def test_websocket_sends_initial_state(self, client):
        """WebSocket sends initial state on connection."""
        # Create a work unit first
        client.post("/work-units", json={
            "chunk": "test_chunk",
            "status": "READY",
            "phase": "PLAN",
        })

        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()

            assert data["type"] == "initial_state"
            assert len(data["data"]["work_units"]) == 1
            assert data["data"]["work_units"][0]["chunk"] == "test_chunk"


class TestFormSubmissions:
    """Tests for HTML form submission handling."""

    def test_answer_form_submission(self, client):
        """Answer endpoint handles form submissions."""
        # Create work unit needing attention
        client.post("/work-units", json={
            "chunk": "question_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        # Submit answer via form
        response = client.post(
            "/work-units/question_chunk/answer",
            data={"answer": "This is my answer"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

        # Should redirect to dashboard
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        # Verify work unit was updated
        get_response = client.get("/work-units/question_chunk")
        data = get_response.json()
        assert data["status"] == "READY"
        assert data["pending_answer"] == "This is my answer"

    def test_answer_json_submission(self, client):
        """Answer endpoint still handles JSON submissions."""
        # Create work unit needing attention
        client.post("/work-units", json={
            "chunk": "json_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        # Submit answer via JSON
        response = client.post(
            "/work-units/json_chunk/answer",
            json={"answer": "JSON answer"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "READY"
        assert data["pending_answer"] == "JSON answer"

    def test_resolve_form_submission_parallelize(self, client):
        """Resolve endpoint handles form submissions for parallelize."""
        # Create work unit needing attention for conflict
        client.post("/work-units", json={
            "chunk": "conflict_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
            "blocked_by": ["other_chunk"],
        })

        # Submit resolve via form
        response = client.post(
            "/work-units/conflict_chunk/resolve",
            data={"other_chunk": "other_chunk", "verdict": "parallelize"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

        # Should redirect to dashboard
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        # Verify work unit was updated - blocked_by should be cleared
        get_response = client.get("/work-units/conflict_chunk")
        data = get_response.json()
        assert "other_chunk" not in data["blocked_by"]

    def test_resolve_form_submission_serialize(self, client):
        """Resolve endpoint handles form submissions for serialize."""
        # Create work unit needing attention
        client.post("/work-units", json={
            "chunk": "serialize_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        # Submit resolve via form
        response = client.post(
            "/work-units/serialize_chunk/resolve",
            data={"other_chunk": "blocker_chunk", "verdict": "serialize"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )

        # Should redirect to dashboard
        assert response.status_code == 303

        # Verify work unit was updated - should be blocked
        get_response = client.get("/work-units/serialize_chunk")
        data = get_response.json()
        assert data["status"] == "BLOCKED"
        assert "blocker_chunk" in data["blocked_by"]


class TestDashboardWithData:
    """Tests for dashboard with various data scenarios."""

    def test_dashboard_shows_blocked_units(self, client):
        """Dashboard shows blocked work units with blocking info."""
        # Create a blocking situation
        client.post("/work-units", json={
            "chunk": "blocked_chunk",
            "status": "BLOCKED",
            "phase": "IMPLEMENT",
            "blocked_by": ["blocker1", "blocker2"],
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "blocked_chunk" in response.text
        assert "Blocked" in response.text
        # Check that blocking info is shown
        assert "blocker1" in response.text

    def test_dashboard_shows_done_units(self, client):
        """Dashboard shows completed work units."""
        client.post("/work-units", json={
            "chunk": "done_chunk",
            "status": "DONE",
            "phase": "COMPLETE",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "done_chunk" in response.text
        assert "Done" in response.text

    def test_dashboard_attention_item_with_reason(self, client):
        """Dashboard shows attention reason for items."""
        # Create work unit with attention reason
        create_response = client.post("/work-units", json={
            "chunk": "reason_chunk",
            "status": "NEEDS_ATTENTION",
            "phase": "IMPLEMENT",
        })

        # Update with attention reason via PATCH
        client.patch("/work-units/reason_chunk", json={
            "status": "NEEDS_ATTENTION",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "reason_chunk" in response.text


class TestLogStreamWebSocket:
    """Tests for WebSocket /ws/log/{chunk} endpoint."""

    def test_log_stream_connects(self, client):
        """Log stream WebSocket endpoint accepts connections."""
        # Create a work unit first
        client.post("/work-units", json={
            "chunk": "stream_test",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })

        with client.websocket_connect("/ws/log/stream_test") as websocket:
            # Connection should succeed - should receive an info message
            # about waiting for logs or existing log data
            data = websocket.receive_json()
            # Should be either 'info' (no logs yet) or 'log_line' (has logs)
            assert data["type"] in ("info", "log_line")

    def test_log_stream_chunk_not_found(self, client):
        """Log stream returns error for non-existent chunk."""
        with client.websocket_connect("/ws/log/nonexistent_chunk") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "not found" in data["content"]

    def test_log_stream_sends_existing_logs(self, client, tmp_path):
        """Log stream sends existing log content."""
        # Create a work unit
        client.post("/work-units", json={
            "chunk": "logs_test",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })

        # Create a log file with test content
        log_dir = tmp_path / ".ve" / "chunks" / "logs_test" / "log"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "implement.txt"
        log_file.write_text(
            "[2026-01-31T19:30:56.669473+00:00] AssistantMessage("
            "content=[ToolUseBlock(id='toolu_test', name='Read', "
            "input={'file_path': '/test.py'})])\n"
        )

        with client.websocket_connect("/ws/log/logs_test") as websocket:
            # Should receive phase header
            data = websocket.receive_json()
            assert data["type"] == "log_line"
            assert data.get("is_header") is True
            assert "IMPLEMENT" in data["content"]

            # Should receive the log entry
            data = websocket.receive_json()
            assert data["type"] == "log_line"
            assert "Read" in data["content"]

    def test_log_stream_no_logs_yet(self, client):
        """Log stream sends info message when no logs exist."""
        # Create a work unit without any logs
        client.post("/work-units", json={
            "chunk": "no_logs_chunk",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })

        with client.websocket_connect("/ws/log/no_logs_chunk") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "info"
            assert "Waiting" in data["content"]


class TestDashboardLogTiling:
    """Tests for dashboard tile expansion UI."""

    def test_running_tiles_have_expand_button(self, client):
        """Running work unit tiles have expand button."""
        # Create a running work unit
        client.post("/work-units", json={
            "chunk": "expandable_chunk",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert "expandable_chunk" in response.text
        # Check for expandable class and expand button
        assert "expandable" in response.text
        assert "expand-button" in response.text

    def test_non_running_tiles_no_expand_button(self, client):
        """Non-running work unit tiles do not have expand button."""
        # Create work units in non-running states
        client.post("/work-units", json={
            "chunk": "ready_tile",
            "status": "READY",
            "phase": "PLAN",
        })
        client.post("/work-units", json={
            "chunk": "done_tile",
            "status": "DONE",
            "phase": "COMPLETE",
        })

        response = client.get("/")

        assert response.status_code == 200
        # Ready and done tiles should not be expandable
        # Count how many expand buttons there are
        expand_button_count = response.text.count('class="expand-button"')
        # Should be zero since no RUNNING work units
        assert expand_button_count == 0

    def test_log_panel_present_in_html(self, client):
        """Log panel container is present in dashboard HTML."""
        # Create a running work unit to trigger log panel rendering
        client.post("/work-units", json={
            "chunk": "panel_test",
            "status": "RUNNING",
            "phase": "IMPLEMENT",
        })

        response = client.get("/")

        assert response.status_code == 200
        assert 'id="log-panel"' in response.text
        assert 'id="log-content"' in response.text
        assert "log-panel-close" in response.text

    def test_log_panel_not_present_without_running(self, client):
        """Log panel container is not present when no running units."""
        # Create only non-running work units
        client.post("/work-units", json={
            "chunk": "ready_only",
            "status": "READY",
            "phase": "PLAN",
        })

        response = client.get("/")

        assert response.status_code == 200
        # Log panel should not be rendered without running units
        assert 'id="log-panel"' not in response.text
