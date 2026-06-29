# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_cursor - Tests for the cursor-agent print-mode backend
"""Tests for the Cursor/Composer print-mode backend.

Covers:
- CursorAgentNotFoundError when the binary is missing
- MCP config helpers (ReviewDecision server) write/remove lifecycle
- Sandbox hook helpers: write/remove, and that the generated hook denies a
  worktree-escaping command
- CursorBackend.run: stream-json parsing (completion, errors, log events,
  review-decision capture, resume), driven by a fake subprocess
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

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
    CursorAgentNotFoundError,
    CursorBackend,
    _remove_cursor_mcp_config,
    _remove_sandbox_hook,
    _write_cursor_mcp_config,
    _write_sandbox_hook,
)
from orchestrator.models import AgentResult, ReviewToolDecision


# ---------------------------------------------------------------------------
# Binary discovery
# ---------------------------------------------------------------------------


class TestCursorAgentMissing:
    def test_error_message_is_actionable(self):
        msg = str(CursorAgentNotFoundError())
        assert "cursor-agent" in msg
        assert "Cursor CLI" in msg

    @pytest.mark.asyncio
    async def test_run_raises_when_binary_missing(self, tmp_path):
        request = SessionRequest(
            prompt="hi", cwd=tmp_path, host_repo_path=tmp_path, env={}, max_turns=5
        )
        with patch("orchestrator.backends.cursor.shutil.which", return_value=None):
            with pytest.raises(CursorAgentNotFoundError):
                await CursorBackend().run(request)

    def test_satisfies_protocol(self):
        backend: AgentBackend = CursorBackend()
        assert hasattr(backend, "run")


# ---------------------------------------------------------------------------
# MCP config helpers (ReviewDecision server)
# ---------------------------------------------------------------------------


class TestMCPConfigHelpers:
    def test_write_creates_config_and_script(self, tmp_path):
        config_path = _write_cursor_mcp_config(tmp_path)
        assert config_path.exists() and config_path.name == "mcp.json"
        config = json.loads(config_path.read_text())
        assert config["mcpServers"]["orchestrator"]["command"] == "python3"
        server_script = tmp_path / ".cursor" / "_review_mcp_server.py"
        assert server_script.exists()
        compile(server_script.read_text(), str(server_script), "exec")  # valid Python

    def test_remove_cleans_up(self, tmp_path):
        _write_cursor_mcp_config(tmp_path)
        _remove_cursor_mcp_config(tmp_path)
        assert not (tmp_path / ".cursor" / "mcp.json").exists()
        assert not (tmp_path / ".cursor").exists()

    def test_remove_idempotent(self, tmp_path):
        _remove_cursor_mcp_config(tmp_path)  # no-op, must not raise


# ---------------------------------------------------------------------------
# Sandbox hook helpers
# ---------------------------------------------------------------------------


class TestSandboxHook:
    def test_write_creates_hook_and_config(self, tmp_path):
        _write_sandbox_hook(tmp_path, tmp_path.parent)
        hooks = tmp_path / ".cursor" / "hooks.json"
        script = tmp_path / ".cursor" / "_sandbox_hook.py"
        assert hooks.exists() and script.exists()
        config = json.loads(hooks.read_text())
        assert "beforeShellExecution" in config["hooks"]
        compile(script.read_text(), str(script), "exec")  # self-contained, valid

    def test_hook_denies_worktree_escape(self, tmp_path):
        host = Path("/home/user/project")
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _write_sandbox_hook(worktree, host)
        script = worktree / ".cursor" / "_sandbox_hook.py"
        r = subprocess.run(
            ["python3", str(script)],
            input=json.dumps({"command": "git -C /home/user/project status"}),
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["permission"] == "deny"

    def test_hook_allows_safe_command(self, tmp_path):
        host = Path("/home/user/project")
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _write_sandbox_hook(worktree, host)
        script = worktree / ".cursor" / "_sandbox_hook.py"
        r = subprocess.run(
            ["python3", str(script)],
            input=json.dumps({"command": "ls -la && git status"}),
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["permission"] == "allow"

    def test_remove_cleans_up(self, tmp_path):
        _write_sandbox_hook(tmp_path, tmp_path.parent)
        _remove_sandbox_hook(tmp_path)
        assert not (tmp_path / ".cursor" / "hooks.json").exists()
        assert not (tmp_path / ".cursor" / "_sandbox_hook.py").exists()
        assert not (tmp_path / ".cursor").exists()


# ---------------------------------------------------------------------------
# CursorBackend.run — stream-json parsing via a fake subprocess
# ---------------------------------------------------------------------------


def _make_request(
    tmp_path: Path,
    on_log: Any = None,
    on_review_decision: Any = None,
    expose_review_tool: bool = False,
    resume_session_id: str | None = None,
) -> SessionRequest:
    return SessionRequest(
        prompt="implement the feature",
        cwd=tmp_path,
        host_repo_path=tmp_path.parent,
        env={},
        max_turns=10,
        on_log=on_log,
        on_review_decision=on_review_decision,
        expose_review_tool=expose_review_tool,
        resume_session_id=resume_session_id,
    )


class _FakeStdout:
    def __init__(self, lines: list[str]):
        self._lines = [(line + "\n").encode() for line in lines]

    def __aiter__(self):
        self._it = iter(self._lines)
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _FakeStderr:
    def __init__(self, data: bytes = b""):
        self._data = data

    async def read(self) -> bytes:
        return self._data


class _FakeProc:
    def __init__(self, lines: list[str], returncode: int = 0, stderr: bytes = b""):
        self.stdout = _FakeStdout(lines)
        self.stderr = _FakeStderr(stderr)
        self.returncode = returncode

    async def wait(self):
        return self.returncode


# stream-json event builders
def _init(sid: str = "s1") -> str:
    return json.dumps({"type": "system", "subtype": "init", "session_id": sid,
                       "model": "composer-2.5"})


def _assistant(text: str) -> str:
    return json.dumps({"type": "assistant", "session_id": "s1",
                       "message": {"role": "assistant",
                                   "content": [{"type": "text", "text": text}]}})


def _result(ok: bool = True, text: str = "done") -> str:
    return json.dumps({"type": "result", "subtype": "success" if ok else "error",
                       "is_error": not ok, "result": text, "session_id": "s1",
                       "duration_ms": 100, "num_turns": 1})


def _tool_started(key: str, args: dict, cid: str = "t1") -> str:
    return json.dumps({"type": "tool_call", "subtype": "started", "call_id": cid,
                       "tool_call": {key: {"args": args}}})


def _tool_completed(key: str, result: dict, cid: str = "t1") -> str:
    return json.dumps({"type": "tool_call", "subtype": "completed", "call_id": cid,
                       "tool_call": {key: {"args": {}, "result": result}}})


async def _run(request: SessionRequest, lines: list[str], returncode: int = 0,
               stderr: bytes = b"") -> tuple[AgentResult, AsyncMock]:
    proc = _FakeProc(lines, returncode, stderr)
    exec_mock = AsyncMock(return_value=proc)
    with (
        patch("orchestrator.backends.cursor.shutil.which", return_value="/usr/bin/cursor-agent"),
        patch("orchestrator.backends.cursor.asyncio.create_subprocess_exec", exec_mock),
    ):
        result = await CursorBackend().run(request)
    return result, exec_mock


class TestCursorBackendPrintMode:
    @pytest.mark.asyncio
    async def test_completion(self, tmp_path):
        result, _ = await _run(_make_request(tmp_path),
                               [_init(), _assistant("PONG"), _result(True, "PONG")])
        assert result.completed is True
        assert result.suspended is False
        assert result.session_id == "s1"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_result_error(self, tmp_path):
        result, _ = await _run(_make_request(tmp_path),
                               [_init(), _result(ok=False, text="model failure")])
        assert result.completed is False
        assert result.error == "model failure"

    @pytest.mark.asyncio
    async def test_nonzero_exit_without_result_is_error(self, tmp_path):
        result, _ = await _run(_make_request(tmp_path), [_init()],
                               returncode=1, stderr=b"boom")
        assert result.completed is False
        assert "exited with code 1" in (result.error or "")
        assert "boom" in (result.error or "")

    @pytest.mark.asyncio
    async def test_command_flags_and_prompt(self, tmp_path):
        _, exec_mock = await _run(_make_request(tmp_path), [_init(), _result()])
        argv = list(exec_mock.call_args.args)
        assert argv[0] == "cursor-agent"
        assert "-p" in argv and "--force" in argv
        assert "stream-json" in argv
        assert argv[-1] == "implement the feature"  # prompt is the last arg
        assert "--approve-mcps" not in argv  # not a review phase

    @pytest.mark.asyncio
    async def test_resume_passes_resume_flag(self, tmp_path):
        _, exec_mock = await _run(
            _make_request(tmp_path, resume_session_id="prev"), [_init(), _result()]
        )
        argv = list(exec_mock.call_args.args)
        assert "--resume" in argv
        assert argv[argv.index("--resume") + 1] == "prev"

    @pytest.mark.asyncio
    async def test_review_phase_writes_mcp_and_approves(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()
        request = SessionRequest(prompt="review", cwd=worktree, host_repo_path=tmp_path,
                                 env={}, max_turns=10, expose_review_tool=True)
        _, exec_mock = await _run(request, [_init(), _result()])
        argv = list(exec_mock.call_args.args)
        assert "--approve-mcps" in argv
        # cleaned up afterwards
        assert not (worktree / ".cursor").exists()

    @pytest.mark.asyncio
    async def test_sandbox_hook_cleaned_up(self, tmp_path):
        worktree = tmp_path / "wt"
        worktree.mkdir()
        request = _make_request(worktree)
        await _run(request, [_init(), _result()])
        # The hook is written during the run and removed afterward.
        assert not (worktree / ".cursor").exists()

    @pytest.mark.asyncio
    async def test_log_events_emitted(self, tmp_path):
        events: list[LogEvent] = []
        lines = [
            _init(),
            _assistant("Thinking..."),
            _tool_started("shellToolCall", {"command": "ls"}),
            _tool_completed("shellToolCall", {"success": {"output": "file1\nfile2"}}),
            _result(True, "done"),
        ]
        result, _ = await _run(_make_request(tmp_path, on_log=events.append), lines)
        assert result.completed is True
        kinds = [type(e).__name__ for e in events]
        assert kinds == ["TextEvent", "ToolCallEvent", "ToolResultEvent", "ResultEvent"]
        assert events[0].text == "Thinking..."
        assert events[1].name == "shellToolCall"
        assert events[1].tool_id == "t1"
        assert events[2].is_error is False
        assert events[3].is_error is False

    @pytest.mark.asyncio
    async def test_tool_result_rejected_is_error(self, tmp_path):
        events: list[LogEvent] = []
        lines = [
            _init(),
            _tool_started("shellToolCall", {"command": "git -C /host status"}),
            _tool_completed("shellToolCall", {"rejected": {"reason": "blocked by a hook"}}),
            _result(True),
        ]
        await _run(_make_request(tmp_path, on_log=events.append), lines)
        tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert tool_results and tool_results[0].is_error is True


class TestCursorBackendReviewCapture:
    @pytest.mark.asyncio
    async def test_review_decision_captured(self, tmp_path):
        captured: list[ReviewToolDecision] = []
        worktree = tmp_path / "wt"
        worktree.mkdir()
        request = SessionRequest(
            prompt="review", cwd=worktree, host_repo_path=tmp_path, env={},
            max_turns=10, expose_review_tool=True,
            on_review_decision=captured.append,
        )
        # Real MCP call shape: mcpToolCall wraps {name, args:{decision,...}}.
        lines = [
            _init(),
            _tool_started("mcpToolCall",
                          {"name": "orchestrator-ReviewDecision",
                           "args": {"decision": "approve", "summary": "LGTM"}}),
            _result(True),
        ]
        result, _ = await _run(request, lines)
        assert result.review_decision is not None
        assert result.review_decision.decision == "APPROVE"
        assert result.review_decision.summary == "LGTM"
        assert len(captured) == 1

    @pytest.mark.asyncio
    async def test_review_decision_ignored_when_not_review_phase(self, tmp_path):
        lines = [
            _init(),
            _tool_started("mcpToolCall",
                          {"name": "orchestrator-ReviewDecision", "args": {"decision": "approve"}}),
            _result(True),
        ]
        result, _ = await _run(_make_request(tmp_path, expose_review_tool=False), lines)
        assert result.review_decision is None
