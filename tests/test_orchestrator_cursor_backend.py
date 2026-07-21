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

import asyncio
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
        # Returns a per-file snapshot of pre-existing bytes (all None on a clean
        # worktree) so cleanup can restore a project's own committed versions.
        originals = _write_cursor_mcp_config(tmp_path)
        assert originals == {"mcp.json": None, "_review_mcp_server.py": None}
        config_path = tmp_path / ".cursor" / "mcp.json"
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

    @pytest.mark.asyncio
    async def test_unrelated_tool_with_decision_key_not_captured(self, tmp_path):
        """A non-review tool carrying a top-level ``decision`` is NOT captured.

        Guards against the loose ``"ReviewDecision" in json.dumps(args)`` match:
        the tool name/key must identify a review, not an incidental key.
        """
        captured: list[ReviewToolDecision] = []
        worktree = tmp_path / "wt"
        worktree.mkdir()
        request = SessionRequest(
            prompt="review", cwd=worktree, host_repo_path=tmp_path, env={},
            max_turns=10, expose_review_tool=True,
            on_review_decision=captured.append,
        )
        lines = [
            _init(),
            # A plain shell tool that happens to carry a top-level "decision".
            _tool_started("shellToolCall",
                          {"command": "echo hi", "decision": "APPROVE"}),
            _result(True),
        ]
        result, _ = await _run(request, lines)
        assert result.review_decision is None
        assert captured == []


# ---------------------------------------------------------------------------
# Robustness: null message, no-result, timeout/kill, logging, .cursor clobber
# ---------------------------------------------------------------------------


class _CapturingStdout:
    """Stdout fake that records the process cwd on first iteration.

    Used to prove sandbox/MCP scaffolding is on disk *while* the agent runs,
    via an assertion hook invoked on the first ``__anext__``.
    """

    def __init__(self, lines: list[str], on_first):
        self._lines = [(line + "\n").encode() for line in lines]
        self._on_first = on_first
        self._first = True

    def __aiter__(self):
        self._it = iter(self._lines)
        return self

    async def __anext__(self) -> bytes:
        if self._first:
            self._first = False
            self._on_first()
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _HangingStdout:
    """Stdout fake whose iterator never yields and never ends (simulates hang)."""

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        # Sleep far longer than the (monkeypatched) phase timeout.
        await asyncio.sleep(3600)
        raise StopAsyncIteration  # pragma: no cover


class _StdoutProc:
    """Fake proc wrapping an arbitrary stdout iterator (already-finished proc)."""

    def __init__(self, stdout, returncode: int = 0, stderr: bytes = b""):
        self.stdout = stdout
        self.stderr = _FakeStderr(stderr)
        self.returncode = returncode

    async def wait(self):
        return self.returncode


class _KillableProc:
    """Fake proc that starts running (returncode None) and records kill().

    ``wait()`` blocks until ``kill()``, exactly like a real process. A fake
    that returns from ``wait()`` unconditionally hides the bug where the
    timeout path waits on the process *before* killing it: that wait never
    returns for a genuinely hung agent.
    """

    def __init__(self, stdout, stderr: bytes = b""):
        self.stdout = stdout
        self.stderr = _FakeStderr(stderr)
        self.returncode = None
        self.killed = False
        self._exited = asyncio.Event()

    def kill(self):
        self.killed = True
        self.returncode = -9
        self._exited.set()

    async def wait(self):
        await self._exited.wait()
        return self.returncode


class TestCursorBackendRobustness:
    @pytest.mark.asyncio
    async def test_null_message_does_not_crash(self, tmp_path):
        """An assistant event with ``message: null`` must not crash the phase."""
        lines = [
            _init(),
            json.dumps({"type": "assistant", "message": None}),
            _result(True, "done"),
        ]
        result, _ = await _run(_make_request(tmp_path), lines)
        assert result.completed is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_no_result_event_clean_exit_is_error(self, tmp_path):
        """Exit 0 with no result event is ambiguous: surface it as an error."""
        result, _ = await _run(
            _make_request(tmp_path), [_init(), _assistant("working")],
            returncode=0,
        )
        assert result.completed is False
        assert result.error is not None
        assert "no result event" in result.error
        assert "exit 0" in result.error

    @pytest.mark.asyncio
    async def test_nonzero_exit_logs_error(self, tmp_path, caplog):
        """A non-zero exit is logged at ERROR so failures are visible."""
        import logging
        with caplog.at_level(logging.ERROR, logger="orchestrator.backends.cursor"):
            result, _ = await _run(
                _make_request(tmp_path), [_init()], returncode=1, stderr=b"boom"
            )
        assert result.error is not None
        assert any(
            r.levelno == logging.ERROR and "non-zero" in r.getMessage()
            for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_timeout_kills_process_and_errors(self, tmp_path, monkeypatch):
        """A hung stdout trips the wall-clock backstop, errors, and kills proc."""
        monkeypatch.setattr(
            "orchestrator.backends.cursor._PHASE_TIMEOUT_SECONDS", 0.05
        )
        proc = _KillableProc(_HangingStdout())
        exec_mock = AsyncMock(return_value=proc)
        with (
            patch("orchestrator.backends.cursor.shutil.which",
                  return_value="/usr/bin/cursor-agent"),
            patch("orchestrator.backends.cursor.asyncio.create_subprocess_exec",
                  exec_mock),
        ):
            # Bounded: if run() waits on the process before killing it, this
            # never returns, so a regression fails loudly instead of hanging.
            result = await asyncio.wait_for(
                CursorBackend().run(_make_request(tmp_path)), timeout=5
            )
        assert result.completed is False
        assert result.error is not None
        assert "exceeded" in result.error
        assert proc.killed is True

    @pytest.mark.asyncio
    async def test_preexisting_cursor_hooks_restored(self, tmp_path):
        """A project's own .cursor/hooks.json is restored, not clobbered."""
        worktree = tmp_path / "wt"
        (worktree / ".cursor").mkdir(parents=True)
        sentinel = worktree / ".cursor" / "hooks.json"
        sentinel.write_text('{"project": "keep me"}')
        await _run(_make_request(worktree), [_init(), _result()])
        # The pre-existing file survives unchanged; .cursor/ is not removed.
        assert sentinel.exists()
        assert json.loads(sentinel.read_text()) == {"project": "keep me"}

    @pytest.mark.asyncio
    async def test_sandbox_hook_present_during_run(self, tmp_path):
        """The hook is on disk *while* the agent runs, not just written/removed.

        Fails if _write_sandbox_hook is dropped from run(): the assertion fires
        on the first stdout iteration, i.e. mid-run.
        """
        worktree = tmp_path / "wt"
        worktree.mkdir()
        hooks_path = worktree / ".cursor" / "hooks.json"
        seen: dict[str, bool] = {}

        def _check():
            seen["present"] = hooks_path.exists()

        stdout = _CapturingStdout([_init(), _result()], _check)
        proc = _StdoutProc(stdout, returncode=0)
        exec_mock = AsyncMock(return_value=proc)
        with (
            patch("orchestrator.backends.cursor.shutil.which",
                  return_value="/usr/bin/cursor-agent"),
            patch("orchestrator.backends.cursor.asyncio.create_subprocess_exec",
                  exec_mock),
        ):
            await CursorBackend().run(_make_request(worktree))
        assert seen.get("present") is True  # written before the agent ran
        assert not (worktree / ".cursor").exists()  # cleaned up after


class TestSandboxHookShellSafety:
    def test_hook_command_is_shell_safe_with_space_in_path(self, tmp_path):
        """A worktree path with a space yields a shell-safe hook command.

        Without shlex.quote, ``python3 /a b/.cursor/_sandbox_hook.py`` splits on
        the space and cursor-agent fails to spawn the hook (failing open). The
        quoted command must still deny a worktree-escaping command when run via
        a real shell.
        """
        host = Path("/home/user/project")
        worktree = tmp_path / "work tree with space"
        worktree.mkdir()
        _write_sandbox_hook(worktree, host)
        hooks = json.loads((worktree / ".cursor" / "hooks.json").read_text())
        cmd = hooks["hooks"]["beforeShellExecution"][0]["command"]
        # The script path appears quoted (or escaped) so the space is preserved.
        assert "_sandbox_hook.py" in cmd
        r = subprocess.run(
            cmd, shell=True,
            input=json.dumps({"command": "git -C /home/user/project status"}),
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["permission"] == "deny"
