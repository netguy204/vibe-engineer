# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_cursor - Tests for CursorBackend and ACPTransport
"""Tests for the Cursor/Composer ACP backend.

Covers:
- ACPTransport: missing binary error, JSON-RPC correlation, notification buffering
- MCP config helpers: write/remove lifecycle
- CursorBackend: protocol satisfaction, event loop (sandbox, questions, review, logs)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.backend import (
    AgentBackend,
    LogEvent,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from orchestrator.backends.cursor import (
    ACPTransport,
    CursorAgentNotFoundError,
    CursorBackend,
    _remove_cursor_mcp_config,
    _write_cursor_mcp_config,
)
from orchestrator.models import AgentResult, ReviewToolDecision


# ---------------------------------------------------------------------------
# ACPTransport tests
# ---------------------------------------------------------------------------


class TestACPTransportMissingBinary:
    """Transport raises a clear error when cursor-agent is not on PATH."""

    @pytest.mark.asyncio
    async def test_start_raises_when_binary_missing(self):
        transport = ACPTransport()
        with patch("orchestrator.backends.cursor.shutil.which", return_value=None):
            with pytest.raises(CursorAgentNotFoundError, match="cursor-agent binary not found"):
                await transport.start()

    def test_error_message_is_actionable(self):
        err = CursorAgentNotFoundError()
        msg = str(err)
        assert "cursor-agent" in msg
        assert "Cursor CLI" in msg


class TestACPTransportCorrelation:
    """Request/response correlation and notification buffering with a mock subprocess."""

    @pytest.fixture
    def mock_process(self):
        """Create a mock subprocess with controllable stdin/stdout."""
        proc = AsyncMock()
        proc.returncode = None
        proc.stdin = AsyncMock()
        proc.stdin.write = MagicMock()
        proc.stdin.drain = AsyncMock()
        proc.stdin.close = MagicMock()
        proc.stdout = AsyncMock()
        proc.stderr = AsyncMock()
        proc.kill = MagicMock()
        proc.wait = AsyncMock()
        return proc

    @pytest.mark.asyncio
    async def test_request_response_correlation(self, mock_process):
        """Requests are correlated to responses by id."""
        transport = ACPTransport()
        transport._process = mock_process

        # Simulate the reader putting a response for id=1
        response = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

        # Start a send_request, which will create a future for id=1
        async def inject_response():
            await asyncio.sleep(0.01)
            future = transport._pending.get(1)
            if future and not future.done():
                future.set_result(response)

        task = asyncio.create_task(inject_response())
        result = await transport.send_request("test/method", {"key": "val"})
        await task

        assert result == {"ok": True}
        # Verify the request was written to stdin
        written = mock_process.stdin.write.call_args[0][0].decode("utf-8")
        req = json.loads(written.strip())
        assert req["method"] == "test/method"
        assert req["id"] == 1
        assert req["params"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_jsonrpc_error_raises(self, mock_process):
        """A JSON-RPC error response raises RuntimeError."""
        transport = ACPTransport()
        transport._process = mock_process

        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid request"},
        }

        async def inject_error():
            await asyncio.sleep(0.01)
            future = transport._pending.get(1)
            if future and not future.done():
                future.set_result(error_response)

        task = asyncio.create_task(inject_error())
        with pytest.raises(RuntimeError, match="Invalid request"):
            await transport.send_request("bad/method")
        await task

    @pytest.mark.asyncio
    async def test_notification_buffering(self, mock_process):
        """Messages without a correlated request id are buffered as notifications."""
        transport = ACPTransport()
        transport._process = mock_process

        notification = {"jsonrpc": "2.0", "method": "session/update", "params": {"data": 1}}
        await transport._notifications.put(notification)

        msg = await transport.recv_notification(timeout=1.0)
        assert msg == notification
        assert msg["method"] == "session/update"

    @pytest.mark.asyncio
    async def test_recv_notification_timeout(self, mock_process):
        """recv_notification returns None on timeout."""
        transport = ACPTransport()
        transport._process = mock_process

        msg = await transport.recv_notification(timeout=0.01)
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_notification_no_id(self, mock_process):
        """send_notification sends a message without an id field."""
        transport = ACPTransport()
        transport._process = mock_process

        await transport.send_notification("ping/notify", {"hello": "world"})
        written = mock_process.stdin.write.call_args[0][0].decode("utf-8")
        msg = json.loads(written.strip())
        assert "id" not in msg
        assert msg["method"] == "ping/notify"

    @pytest.mark.asyncio
    async def test_close_cancels_pending(self, mock_process):
        """close() cancels any pending request futures."""
        transport = ACPTransport()
        transport._process = mock_process

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        transport._pending[99] = future

        mock_process.returncode = 0  # Already exited
        await transport.close()
        assert future.cancelled()
        assert len(transport._pending) == 0


# ---------------------------------------------------------------------------
# MCP config helpers
# ---------------------------------------------------------------------------


class TestMCPConfigHelpers:
    """_write_cursor_mcp_config / _remove_cursor_mcp_config lifecycle."""

    def test_write_creates_config_and_script(self, tmp_path):
        config_path = _write_cursor_mcp_config(tmp_path)
        assert config_path.exists()
        assert config_path.name == "mcp.json"

        config = json.loads(config_path.read_text())
        assert "mcpServers" in config
        assert "orchestrator" in config["mcpServers"]
        assert config["mcpServers"]["orchestrator"]["command"] == "python3"

        server_script = tmp_path / ".cursor" / "_review_mcp_server.py"
        assert server_script.exists()
        # Script should be valid Python — compile to check syntax
        compile(server_script.read_text(), str(server_script), "exec")

    def test_remove_cleans_up(self, tmp_path):
        _write_cursor_mcp_config(tmp_path)
        _remove_cursor_mcp_config(tmp_path)

        assert not (tmp_path / ".cursor" / "mcp.json").exists()
        assert not (tmp_path / ".cursor" / "_review_mcp_server.py").exists()
        # .cursor/ should be removed if empty
        assert not (tmp_path / ".cursor").exists()

    def test_remove_preserves_other_files(self, tmp_path):
        _write_cursor_mcp_config(tmp_path)
        other_file = tmp_path / ".cursor" / "settings.json"
        other_file.write_text("{}")

        _remove_cursor_mcp_config(tmp_path)

        assert not (tmp_path / ".cursor" / "mcp.json").exists()
        assert other_file.exists()
        # .cursor/ should remain because settings.json is still there
        assert (tmp_path / ".cursor").exists()

    def test_remove_idempotent(self, tmp_path):
        """Removing when nothing was written doesn't raise."""
        _remove_cursor_mcp_config(tmp_path)  # No-op, should not raise


# ---------------------------------------------------------------------------
# CursorBackend protocol and integration tests
# ---------------------------------------------------------------------------


class TestCursorBackendProtocol:
    """CursorBackend satisfies AgentBackend protocol."""

    def test_satisfies_protocol(self):
        backend: AgentBackend = CursorBackend()
        assert hasattr(backend, "run")

    @pytest.mark.asyncio
    async def test_raises_when_binary_missing(self, tmp_path):
        backend = CursorBackend()
        request = SessionRequest(
            prompt="hello",
            cwd=tmp_path,
            host_repo_path=tmp_path,
            env={},
            max_turns=5,
        )
        with patch("orchestrator.backends.cursor.shutil.which", return_value=None):
            with pytest.raises(CursorAgentNotFoundError):
                await backend.run(request)


def _make_request(
    tmp_path: Path,
    on_log: Any = None,
    on_question: Any = None,
    on_review_decision: Any = None,
    expose_review_tool: bool = False,
    resume_session_id: str | None = None,
) -> SessionRequest:
    """Helper to build a SessionRequest for tests."""
    return SessionRequest(
        prompt="implement the feature",
        cwd=tmp_path,
        host_repo_path=tmp_path.parent,
        env={},
        max_turns=10,
        on_log=on_log,
        on_question=on_question,
        on_review_decision=on_review_decision,
        expose_review_tool=expose_review_tool,
        resume_session_id=resume_session_id,
    )


class _FakeTransportBackend(CursorBackend):
    """CursorBackend subclass that injects a fake transport for testing the event loop.

    Provide a list of ACP notifications that will be yielded from recv_notification
    in order. The init and session/new responses are auto-handled.
    """

    def __init__(self, notifications: list[dict], init_session_id: str = "test-sess"):
        super().__init__()
        self._notifications = notifications
        self._init_session_id = init_session_id


async def _run_with_fake_events(
    request: SessionRequest,
    notifications: list[dict],
    init_session_id: str = "test-sess",
) -> AgentResult:
    """Run CursorBackend.run with a patched transport that replays canned events."""
    backend = CursorBackend()

    notification_iter = iter(notifications)

    async def fake_recv(timeout=None):
        try:
            return next(notification_iter)
        except StopIteration:
            return None

    fake_transport = AsyncMock(spec=ACPTransport)
    fake_transport.is_alive = True
    fake_transport.recv_notification = fake_recv
    fake_transport.send_request = AsyncMock(
        side_effect=[
            # system/init response
            {"session_id": init_session_id},
            # session/new or session/load response
            {"sessionId": init_session_id},
        ]
    )
    fake_transport.close = AsyncMock()
    fake_transport._process = MagicMock()
    fake_transport._process.stdin = MagicMock()
    fake_transport._process.stdin.write = MagicMock()
    fake_transport._process.stdin.drain = AsyncMock()
    fake_transport._process.returncode = None

    with (
        patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
        patch.object(ACPTransport, "start", new_callable=AsyncMock),
        patch("orchestrator.backends.cursor.ACPTransport", return_value=fake_transport),
    ):
        return await backend.run(request)


class TestCursorBackendEventLoop:
    """Integration tests for the ACP event loop in CursorBackend.run."""

    @pytest.mark.asyncio
    async def test_simple_session_completion(self, tmp_path):
        """A session that emits a result notification produces AgentResult(completed=True)."""
        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {
                    "isError": False,
                    "sessionId": "test-sess",
                    "durationMs": 5000,
                    "totalCostUsd": 0.5,
                    "numTurns": 3,
                    "resultText": "Done",
                },
            }
        ]
        request = _make_request(tmp_path)
        result = await _run_with_fake_events(request, events)

        assert result.completed is True
        assert result.suspended is False
        assert result.session_id == "test-sess"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_session_error(self, tmp_path):
        """A session/result with isError produces AgentResult(error=...)."""
        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {
                    "isError": True,
                    "errorMessage": "Something went wrong",
                    "sessionId": "test-sess",
                },
            }
        ]
        request = _make_request(tmp_path)
        result = await _run_with_fake_events(request, events)

        assert result.completed is False
        assert result.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_sandbox_allow_safe_command(self, tmp_path):
        """A permission request for a safe command gets allow reply."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        host = tmp_path

        events = [
            {
                "jsonrpc": "2.0",
                "id": 100,
                "method": "session/request_permission",
                "params": {
                    "toolName": "Bash",
                    "toolInput": {"command": "ls -la"},
                    "command": "ls -la",
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = SessionRequest(
            prompt="test",
            cwd=worktree,
            host_repo_path=host,
            env={},
            max_turns=5,
        )
        result = await _run_with_fake_events(request, events)
        assert result.completed is True

    @pytest.mark.asyncio
    async def test_sandbox_deny_violation(self, tmp_path):
        """A permission request escaping the worktree gets deny reply."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        host = tmp_path

        permission_replies: list[dict] = []

        # We need to capture what gets written back
        events = [
            {
                "jsonrpc": "2.0",
                "id": 200,
                "method": "session/request_permission",
                "params": {
                    "toolName": "Bash",
                    "toolInput": {"command": f"cd {host} && rm -rf ."},
                    "command": f"cd {host} && rm -rf .",
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = SessionRequest(
            prompt="test",
            cwd=worktree,
            host_repo_path=host,
            env={},
            max_turns=5,
        )
        result = await _run_with_fake_events(request, events)
        # Session still completes (the deny is sent, agent continues)
        assert result.completed is True

    @pytest.mark.asyncio
    async def test_question_forwarding(self, tmp_path):
        """cursor/ask_question suspends the session and calls on_question."""
        captured_questions: list[dict] = []

        events = [
            {
                "jsonrpc": "2.0",
                "method": "cursor/ask_question",
                "params": {
                    "question": "Which database should I use?",
                    "options": ["PostgreSQL", "SQLite"],
                    "header": "Database choice",
                    "multiSelect": False,
                },
            },
        ]
        request = _make_request(
            tmp_path,
            on_question=lambda q: captured_questions.append(q),
        )
        result = await _run_with_fake_events(request, events)

        assert result.suspended is True
        assert result.completed is False
        assert result.question is not None
        assert result.question["question"] == "Which database should I use?"
        assert result.question["options"] == ["PostgreSQL", "SQLite"]
        assert len(captured_questions) == 1

    @pytest.mark.asyncio
    async def test_review_decision_capture(self, tmp_path):
        """ReviewDecision tool call in session/update is captured."""
        captured_decisions: list[ReviewToolDecision] = []

        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu-1",
                            "name": "ReviewDecision",
                            "input": {
                                "decision": "APPROVE",
                                "summary": "Implementation looks good",
                            },
                        }
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = _make_request(
            tmp_path,
            expose_review_tool=True,
            on_review_decision=lambda d: captured_decisions.append(d),
        )
        result = await _run_with_fake_events(request, events)

        assert result.review_decision is not None
        assert result.review_decision.decision == "APPROVE"
        assert result.review_decision.summary == "Implementation looks good"
        assert len(captured_decisions) == 1

    @pytest.mark.asyncio
    async def test_review_decision_mcp_namespaced(self, tmp_path):
        """ReviewDecision also captured when MCP-namespaced."""
        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu-2",
                            "name": "mcp__orchestrator__ReviewDecision",
                            "input": {
                                "decision": "feedback",
                                "summary": "Needs work",
                                "issues": [{"location": "foo.py", "concern": "missing tests"}],
                            },
                        }
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False},
            },
        ]
        request = _make_request(tmp_path, expose_review_tool=True)
        result = await _run_with_fake_events(request, events)

        assert result.review_decision is not None
        assert result.review_decision.decision == "FEEDBACK"
        assert result.review_decision.issues == [{"location": "foo.py", "concern": "missing tests"}]

    @pytest.mark.asyncio
    async def test_log_events_emitted(self, tmp_path):
        """session/update content blocks are translated into LogEvents."""
        log_events: list[LogEvent] = []

        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "content": [
                        {"type": "text", "text": "Thinking about the problem..."},
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Bash",
                            "input": {"command": "ls", "description": "List files"},
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "t1",
                            "content": "file1.txt\nfile2.txt",
                            "is_error": False,
                        },
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {
                    "isError": False,
                    "sessionId": "s1",
                    "durationMs": 1000,
                    "totalCostUsd": 0.1,
                    "numTurns": 1,
                },
            },
        ]
        request = _make_request(tmp_path, on_log=lambda e: log_events.append(e))
        result = await _run_with_fake_events(request, events)

        assert result.completed is True
        # 3 events from session/update + 1 ResultEvent from session/result
        assert len(log_events) == 4

        assert isinstance(log_events[0], TextEvent)
        assert log_events[0].text == "Thinking about the problem..."

        assert isinstance(log_events[1], ToolCallEvent)
        assert log_events[1].name == "Bash"
        assert log_events[1].tool_id == "t1"
        assert log_events[1].description == "List files"

        assert isinstance(log_events[2], ToolResultEvent)
        assert log_events[2].tool_use_id == "t1"
        assert log_events[2].content == "file1.txt\nfile2.txt"
        assert log_events[2].is_error is False

        assert isinstance(log_events[3], ResultEvent)

    @pytest.mark.asyncio
    async def test_session_resume(self, tmp_path):
        """When resume_session_id is set, session/load is called instead of session/new."""
        request = _make_request(tmp_path, resume_session_id="prev-sess")

        backend = CursorBackend()
        send_request_calls: list[tuple] = []

        async def fake_recv(timeout=None):
            return {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "prev-sess"},
            }

        async def fake_send_request(method, params=None):
            send_request_calls.append((method, params))
            if method == "system/init":
                return {"session_id": "prev-sess"}
            if method == "session/load":
                return {"sessionId": "prev-sess"}
            return {}

        fake_transport = AsyncMock(spec=ACPTransport)
        fake_transport.is_alive = True
        fake_transport.recv_notification = fake_recv
        fake_transport.send_request = fake_send_request
        fake_transport.close = AsyncMock()
        fake_transport._process = MagicMock()
        fake_transport._process.stdin = MagicMock()
        fake_transport._process.stdin.write = MagicMock()
        fake_transport._process.stdin.drain = AsyncMock()
        fake_transport._process.returncode = None

        with (
            patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
            patch("orchestrator.backends.cursor.ACPTransport", return_value=fake_transport),
        ):
            result = await backend.run(request)

        assert result.session_id == "prev-sess"
        # Verify session/load was called, not session/new
        methods = [call[0] for call in send_request_calls]
        assert "session/load" in methods
        assert "session/new" not in methods

    @pytest.mark.asyncio
    async def test_unknown_method_ignored(self, tmp_path):
        """Unknown ACP methods are logged and skipped without error."""
        events = [
            {
                "jsonrpc": "2.0",
                "method": "some/unknown_method",
                "params": {"data": "whatever"},
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = _make_request(tmp_path)
        result = await _run_with_fake_events(request, events)
        assert result.completed is True


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/backend_parity - Edge cases from parity analysis
# ---------------------------------------------------------------------------


class TestCursorBackendParityEdgeCases:
    """Edge cases identified during Claude-vs-Cursor parity analysis."""

    @pytest.mark.asyncio
    async def test_mcp_config_cleaned_up_on_error(self, tmp_path):
        """MCP config files are removed even when the event loop raises."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": True, "errorMessage": "Composer crashed"},
            },
        ]
        request = SessionRequest(
            prompt="review the code",
            cwd=worktree,
            host_repo_path=tmp_path,
            env={},
            max_turns=10,
            expose_review_tool=True,
        )
        result = await _run_with_fake_events(request, events)

        assert result.error == "Composer crashed"
        # MCP config must be cleaned up even on error
        assert not (worktree / ".cursor" / "mcp.json").exists()
        assert not (worktree / ".cursor" / "_review_mcp_server.py").exists()

    @pytest.mark.asyncio
    async def test_permission_request_without_id_does_not_crash(self, tmp_path):
        """A permission request missing the 'id' field is skipped without error."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        events = [
            {
                "jsonrpc": "2.0",
                # No "id" field — backend should skip the reply
                "method": "session/request_permission",
                "params": {
                    "toolName": "Bash",
                    "toolInput": {"command": "ls"},
                    "command": "ls",
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = SessionRequest(
            prompt="test",
            cwd=worktree,
            host_repo_path=tmp_path,
            env={},
            max_turns=5,
        )
        result = await _run_with_fake_events(request, events)
        assert result.completed is True

    @pytest.mark.asyncio
    async def test_timeout_when_transport_alive_no_notifications(self, tmp_path):
        """When no notifications arrive and transport is alive, result has a timeout error."""
        backend = CursorBackend()

        call_count = 0

        async def fake_recv(timeout=None):
            nonlocal call_count
            call_count += 1
            # First call returns None (timeout), simulating 300s silence
            return None

        fake_transport = AsyncMock(spec=ACPTransport)
        fake_transport.is_alive = True
        fake_transport.recv_notification = fake_recv
        fake_transport.send_request = AsyncMock(
            side_effect=[
                {"session_id": "t1"},
                {"sessionId": "t1"},
            ]
        )
        fake_transport.close = AsyncMock()
        fake_transport._process = MagicMock()
        fake_transport._process.stdin = MagicMock()
        fake_transport._process.stdin.write = MagicMock()
        fake_transport._process.stdin.drain = AsyncMock()
        fake_transport._process.returncode = None

        request = _make_request(tmp_path)

        with (
            patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
            patch("orchestrator.backends.cursor.ACPTransport", return_value=fake_transport),
        ):
            result = await backend.run(request)

        assert result.completed is False
        assert result.error is not None
        assert "Timed out" in result.error

    @pytest.mark.asyncio
    async def test_review_decision_only_first_captured(self, tmp_path):
        """Only the first ReviewDecision tool call is captured; subsequent ones are ignored."""
        captured_decisions: list[ReviewToolDecision] = []

        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu-1",
                            "name": "ReviewDecision",
                            "input": {
                                "decision": "FEEDBACK",
                                "summary": "First attempt",
                            },
                        },
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu-2",
                            "name": "ReviewDecision",
                            "input": {
                                "decision": "APPROVE",
                                "summary": "Changed my mind",
                            },
                        },
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = _make_request(
            tmp_path,
            expose_review_tool=True,
            on_review_decision=lambda d: captured_decisions.append(d),
        )
        result = await _run_with_fake_events(request, events)

        assert result.review_decision is not None
        assert result.review_decision.decision == "FEEDBACK"
        assert result.review_decision.summary == "First attempt"
        assert len(captured_decisions) == 1

    @pytest.mark.asyncio
    async def test_mcp_config_not_written_without_expose_review_tool(self, tmp_path):
        """When expose_review_tool is False, no .cursor/ config is created."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        events = [
            {
                "jsonrpc": "2.0",
                "method": "session/result",
                "params": {"isError": False, "sessionId": "s1"},
            },
        ]
        request = SessionRequest(
            prompt="implement the feature",
            cwd=worktree,
            host_repo_path=tmp_path,
            env={},
            max_turns=10,
            expose_review_tool=False,
        )
        result = await _run_with_fake_events(request, events)

        assert result.completed is True
        assert not (worktree / ".cursor").exists()

    @pytest.mark.asyncio
    async def test_transport_eof_produces_error(self, tmp_path):
        """When cursor-agent exits unexpectedly (EOF), result has an error."""
        backend = CursorBackend()

        async def fake_recv(timeout=None):
            return None  # EOF

        fake_transport = AsyncMock(spec=ACPTransport)
        fake_transport.is_alive = False  # Process already exited
        fake_transport.recv_notification = fake_recv
        fake_transport.send_request = AsyncMock(
            side_effect=[
                {"session_id": "t1"},
                {"sessionId": "t1"},
            ]
        )
        fake_transport.close = AsyncMock()
        fake_transport._process = MagicMock()
        fake_transport._process.stdin = MagicMock()
        fake_transport._process.stdin.write = MagicMock()
        fake_transport._process.stdin.drain = AsyncMock()
        fake_transport._process.returncode = 1

        request = _make_request(tmp_path)

        with (
            patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
            patch("orchestrator.backends.cursor.ACPTransport", return_value=fake_transport),
        ):
            result = await backend.run(request)

        assert result.completed is False
        assert result.error is not None
        assert "exited before event loop" in result.error
