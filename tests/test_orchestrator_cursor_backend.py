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
    async def test_incoming_request_with_colliding_id_is_not_a_response(self, mock_process):
        """An agent->client request (e.g. session/request_permission) whose id
        collides with a pending request id is routed to the notification queue,
        NOT mis-correlated as that request's response.

        Regression: cursor-agent numbers its permission requests 0,1,2,... in the
        same integer space as our outgoing requests, so a permission request can
        share the id of our pending session/prompt. It must be distinguished by
        the presence of a "method" field.
        """
        transport = ACPTransport()
        transport._process = mock_process

        loop = asyncio.get_running_loop()
        pending = loop.create_future()
        transport._pending[3] = pending  # our pending session/prompt (id=3)

        incoming = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "session/request_permission",
            "params": {"toolCall": {"toolCallId": "x"}},
        }
        mock_process.stdout.readline = AsyncMock(
            side_effect=[(json.dumps(incoming) + "\n").encode(), b""]
        )

        await transport._read_loop()

        assert not pending.done()  # the colliding request did not resolve it
        msg = await transport.recv_notification(timeout=1.0)
        assert msg == incoming

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


# ---------------------------------------------------------------------------
# Fake transport for driving CursorBackend.run against the real ACP flow:
# initialize -> session/new (or session/load) -> session/prompt, with
# session/update notifications streamed while the prompt request is pending.
# ---------------------------------------------------------------------------


def _update(session_update: str, **fields) -> dict:
    """Build a session/update notification with the given sessionUpdate kind.

    `fields` may include a `kind` (the tool_call's own kind, e.g. "execute"),
    which is why the discriminator parameter is named session_update.
    """
    return {
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": {"update": {"sessionUpdate": session_update, **fields}},
    }


def _perm_request(req_id, tool_call_id: str, title: str) -> dict:
    """Build a session/request_permission with the real toolCall/options shape."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "session/request_permission",
        "params": {
            "sessionId": "s1",
            "toolCall": {"toolCallId": tool_call_id, "title": title, "kind": "execute"},
            "options": [
                {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
                {"optionId": "allow-always", "name": "Allow always", "kind": "allow_always"},
                {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
            ],
        },
    }


class _FakeTransport:
    """Deterministic fake ACPTransport.

    Replays ``notifications`` from recv_notification in order; when they are
    exhausted it resolves the pending session/prompt request with ``stop_reason``
    (or raises ``prompt_exc``). Records sent requests, notifications, and
    permission replies for assertions.
    """

    def __init__(
        self,
        notifications,
        *,
        session_id: str = "test-sess",
        stop_reason: str = "end_turn",
        prompt_exc: Exception | None = None,
        alive: bool = True,
        simulate_silence: bool = False,
    ):
        self.notifs = list(notifications)
        self.session_id = session_id
        self.stop_reason = stop_reason
        self.prompt_exc = prompt_exc
        self.alive = alive
        self.simulate_silence = simulate_silence
        self.sent_requests: list[tuple] = []
        self.sent_notifications: list[tuple] = []
        self.permission_replies: list[tuple] = []
        self._prompt_future = None

    async def start(self):
        pass

    async def close(self):
        self.alive = False

    @property
    def is_alive(self):
        return self.alive

    async def send_request(self, method, params=None):
        self.sent_requests.append((method, params))
        if method == "session/new":
            return {"sessionId": self.session_id}
        if method == "session/prompt":
            self._prompt_future = asyncio.get_event_loop().create_future()
            if self.simulate_silence:
                # Resolve on a short delay so the grace wait_for in run() returns
                # quickly, while recv_notification still drives the silence path.
                async def _later(fut=self._prompt_future):
                    await asyncio.sleep(0.02)
                    if not fut.done():
                        fut.set_result({"stopReason": self.stop_reason})

                asyncio.ensure_future(_later())
            return await self._prompt_future
        return {}

    async def send_notification(self, method, params=None):
        self.sent_notifications.append((method, params))

    async def send_response(self, req_id, result):
        self.permission_replies.append((req_id, result))

    async def recv_notification(self, timeout=None):
        if self.notifs:
            return self.notifs.pop(0)
        if self.simulate_silence:
            return None  # silence; prompt resolves via its own delayed task
        # Yield so the pending session/prompt task runs far enough to create
        # its future, then resolve it (turn complete).
        for _ in range(5):
            if self._prompt_future is not None:
                break
            await asyncio.sleep(0)
        if self._prompt_future is not None and not self._prompt_future.done():
            if self.prompt_exc is not None:
                self._prompt_future.set_exception(self.prompt_exc)
            else:
                self._prompt_future.set_result({"stopReason": self.stop_reason})
            await asyncio.sleep(0)  # let the prompt task resume to completion
        return None


async def _run_with_fake(request: SessionRequest, fake: _FakeTransport) -> AgentResult:
    """Run CursorBackend.run with the given fake transport patched in."""
    with (
        patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
        patch.object(ACPTransport, "start", new_callable=AsyncMock),
        patch("orchestrator.backends.cursor.ACPTransport", return_value=fake),
    ):
        return await CursorBackend().run(request)


class TestCursorBackendEventLoop:
    """Integration tests for the ACP event loop in CursorBackend.run."""

    @pytest.mark.asyncio
    async def test_handshake_and_session_creation(self, tmp_path):
        """The run issues initialize, notifications/initialized, session/new, session/prompt."""
        fake = _FakeTransport([])
        result = await _run_with_fake(_make_request(tmp_path), fake)

        req_methods = [m for m, _ in fake.sent_requests]
        assert req_methods == ["initialize", "session/new", "session/prompt"]
        assert ("notifications/initialized", {}) in fake.sent_notifications
        assert result.completed is True
        assert result.session_id == "test-sess"

    @pytest.mark.asyncio
    async def test_simple_session_completion(self, tmp_path):
        """stopReason end_turn yields AgentResult(completed=True)."""
        fake = _FakeTransport(
            [_update("agent_message_chunk", content={"type": "text", "text": "PONG"})],
            stop_reason="end_turn",
        )
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is True
        assert result.suspended is False
        assert result.error is None

    @pytest.mark.asyncio
    async def test_non_end_turn_stop_reason_is_error(self, tmp_path):
        """A non-end_turn stopReason surfaces as an error, not completion."""
        fake = _FakeTransport([], stop_reason="refusal")
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is False
        assert result.error is not None
        assert "refusal" in result.error

    @pytest.mark.asyncio
    async def test_prompt_exception_is_error(self, tmp_path):
        """An exception from the session/prompt request becomes the result error."""
        fake = _FakeTransport([], prompt_exc=RuntimeError("ACP JSON-RPC error"))
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is False
        assert "ACP JSON-RPC error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_sandbox_allow_safe_command(self, tmp_path):
        """A permission request for an in-worktree command is allowed."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        request = SessionRequest(
            prompt="t", cwd=worktree, host_repo_path=tmp_path, env={}, max_turns=5,
        )
        fake = _FakeTransport([
            _update("tool_call", toolCallId="t1", title="`ls -la`", kind="execute",
                    rawInput={"command": "ls -la"}),
            _perm_request(100, "t1", "`ls -la`"),
        ])
        result = await _run_with_fake(request, fake)
        assert result.completed is True
        assert fake.permission_replies == [
            (100, {"outcome": {"outcome": "selected", "optionId": "allow-once"}})
        ]

    @pytest.mark.asyncio
    async def test_sandbox_deny_violation(self, tmp_path):
        """A permission request escaping the worktree is rejected.

        The permission payload carries no command — it is correlated by
        toolCallId from the preceding tool_call update.
        """
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        host = tmp_path
        request = SessionRequest(
            prompt="t", cwd=worktree, host_repo_path=host, env={}, max_turns=5,
        )
        fake = _FakeTransport([
            _update("tool_call", toolCallId="t2", title="`git -C ...`", kind="execute",
                    rawInput={"command": f"git -C {host} status"}),
            _perm_request(200, "t2", "`git -C ...`"),
        ])
        result = await _run_with_fake(request, fake)
        assert result.completed is True
        assert fake.permission_replies == [
            (200, {"outcome": {"outcome": "selected", "optionId": "reject-once"}})
        ]

    @pytest.mark.asyncio
    async def test_question_forwarding_suspends(self, tmp_path):
        """cursor/ask_question suspends the run and calls on_question."""
        captured: list[dict] = []
        fake = _FakeTransport([
            {
                "jsonrpc": "2.0",
                "method": "cursor/ask_question",
                "params": {
                    "question": "Which database?",
                    "options": ["PostgreSQL", "SQLite"],
                    "header": "Database",
                    "multiSelect": False,
                },
            },
        ])
        request = _make_request(tmp_path, on_question=lambda q: captured.append(q))
        result = await _run_with_fake(request, fake)

        assert result.suspended is True
        assert result.completed is False
        assert result.question["question"] == "Which database?"
        assert result.question["options"] == ["PostgreSQL", "SQLite"]
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_review_decision_capture(self, tmp_path):
        """A ReviewDecision tool_call update is captured into the result."""
        captured: list[ReviewToolDecision] = []
        fake = _FakeTransport([
            _update("tool_call", toolCallId="r1", title="ReviewDecision", kind="other",
                    rawInput={"decision": "APPROVE", "summary": "Looks good"}),
        ])
        request = _make_request(
            tmp_path, expose_review_tool=True,
            on_review_decision=lambda d: captured.append(d),
        )
        result = await _run_with_fake(request, fake)
        assert result.review_decision is not None
        assert result.review_decision.decision == "APPROVE"
        assert result.review_decision.summary == "Looks good"
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_review_decision_mcp_namespaced(self, tmp_path):
        """ReviewDecision is captured when the tool title is MCP-namespaced."""
        fake = _FakeTransport([
            _update("tool_call", toolCallId="r2",
                    title="mcp__orchestrator__ReviewDecision", kind="other",
                    rawInput={
                        "decision": "feedback",
                        "summary": "Needs work",
                        "issues": [{"location": "foo.py", "concern": "missing tests"}],
                    }),
        ])
        result = await _run_with_fake(_make_request(tmp_path, expose_review_tool=True), fake)
        assert result.review_decision is not None
        assert result.review_decision.decision == "FEEDBACK"
        assert result.review_decision.issues == [{"location": "foo.py", "concern": "missing tests"}]

    @pytest.mark.asyncio
    async def test_review_decision_only_first_captured(self, tmp_path):
        """Only the first ReviewDecision is captured."""
        captured: list[ReviewToolDecision] = []
        fake = _FakeTransport([
            _update("tool_call", toolCallId="r1", title="ReviewDecision", kind="other",
                    rawInput={"decision": "FEEDBACK", "summary": "First"}),
            _update("tool_call", toolCallId="r2", title="ReviewDecision", kind="other",
                    rawInput={"decision": "APPROVE", "summary": "Second"}),
        ])
        request = _make_request(
            tmp_path, expose_review_tool=True,
            on_review_decision=lambda d: captured.append(d),
        )
        result = await _run_with_fake(request, fake)
        assert result.review_decision.decision == "FEEDBACK"
        assert result.review_decision.summary == "First"
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_log_events_emitted(self, tmp_path):
        """session/update notifications normalize to TextEvent/ToolCallEvent/ToolResultEvent."""
        log_events: list[LogEvent] = []
        fake = _FakeTransport([
            _update("agent_message_chunk", content={"type": "text", "text": "Thinking..."}),
            _update("tool_call", toolCallId="t1", title="Bash", kind="execute",
                    rawInput={"command": "ls"}),
            _update("tool_call_update", toolCallId="t1", status="completed",
                    content="file1.txt\nfile2.txt"),
        ])
        result = await _run_with_fake(_make_request(tmp_path, on_log=lambda e: log_events.append(e)), fake)

        assert result.completed is True
        assert len(log_events) == 3
        assert isinstance(log_events[0], TextEvent)
        assert log_events[0].text == "Thinking..."
        assert isinstance(log_events[1], ToolCallEvent)
        assert log_events[1].name == "Bash"
        assert log_events[1].tool_id == "t1"
        assert isinstance(log_events[2], ToolResultEvent)
        assert log_events[2].tool_use_id == "t1"
        assert log_events[2].content == "file1.txt\nfile2.txt"
        assert log_events[2].is_error is False

    @pytest.mark.asyncio
    async def test_session_resume_uses_session_load(self, tmp_path):
        """resume_session_id routes through session/load, not session/new."""
        request = _make_request(tmp_path, resume_session_id="prev-sess")
        fake = _FakeTransport([], session_id="prev-sess")
        result = await _run_with_fake(request, fake)

        methods = [m for m, _ in fake.sent_requests]
        assert "session/load" in methods
        assert "session/new" not in methods
        assert result.session_id == "prev-sess"

    @pytest.mark.asyncio
    async def test_unknown_method_ignored(self, tmp_path):
        """Unknown ACP notification methods are skipped without error."""
        fake = _FakeTransport([
            {"jsonrpc": "2.0", "method": "some/unknown_method", "params": {"data": "x"}},
        ])
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is True


class TestCursorBackendParityEdgeCases:
    """Edge cases identified during Claude-vs-Cursor parity analysis."""

    @pytest.mark.asyncio
    async def test_mcp_config_cleaned_up_on_error(self, tmp_path):
        """MCP config files are removed even when the prompt errors."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        request = SessionRequest(
            prompt="review", cwd=worktree, host_repo_path=tmp_path, env={},
            max_turns=10, expose_review_tool=True,
        )
        fake = _FakeTransport([], prompt_exc=RuntimeError("Composer crashed"))
        result = await _run_with_fake(request, fake)

        assert result.error == "Composer crashed"
        assert not (worktree / ".cursor" / "mcp.json").exists()
        assert not (worktree / ".cursor" / "_review_mcp_server.py").exists()

    @pytest.mark.asyncio
    async def test_mcp_config_not_written_without_expose_review_tool(self, tmp_path):
        """No .cursor/ config is created when expose_review_tool is False."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        request = SessionRequest(
            prompt="implement", cwd=worktree, host_repo_path=tmp_path, env={},
            max_turns=10, expose_review_tool=False,
        )
        result = await _run_with_fake(request, _FakeTransport([]))
        assert result.completed is True
        assert not (worktree / ".cursor").exists()

    @pytest.mark.asyncio
    async def test_permission_request_without_id_does_not_crash(self, tmp_path):
        """A permission request missing 'id' is handled without replying or crashing."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        request = SessionRequest(
            prompt="t", cwd=worktree, host_repo_path=tmp_path, env={}, max_turns=5,
        )
        perm = _perm_request(None, "t1", "`ls`")
        del perm["id"]
        fake = _FakeTransport([perm])
        result = await _run_with_fake(request, fake)
        assert result.completed is True
        assert fake.permission_replies == []

    @pytest.mark.asyncio
    async def test_silence_produces_timeout_error(self, tmp_path):
        """recv_notification returning None while the prompt is pending is a timeout."""
        fake = _FakeTransport([], simulate_silence=True)
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is False
        assert "Timed out" in (result.error or "")

    @pytest.mark.asyncio
    async def test_not_alive_before_prompt_produces_error(self, tmp_path):
        """If the process is gone before the prompt is sent, the result is an error."""
        fake = _FakeTransport([], alive=False)
        result = await _run_with_fake(_make_request(tmp_path), fake)
        assert result.completed is False
        assert "exited before the prompt was sent" in (result.error or "")
