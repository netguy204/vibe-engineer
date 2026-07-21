# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_cursor - CursorBackend: cursor-agent print-mode backend
"""Cursor/Composer backend via cursor-agent print mode.

Implements :class:`~orchestrator.backend.AgentBackend` by spawning
``cursor-agent -p --output-format stream-json`` (non-interactive print mode,
which runs the prompt to autonomous completion) and parsing its newline-
delimited JSON event stream. This module is the ONLY place in the orchestrator
that interacts with the ``cursor-agent`` binary; everything above the seam talks
through :class:`~orchestrator.backend.SessionRequest` and
:class:`~orchestrator.models.AgentResult`.

Interactive ACP mode was rejected during live validation: it holds turns open
waiting for the operator, which an autonomous orchestrator cannot satisfy.
Sandbox enforcement therefore moves to a ``.cursor/hooks.json`` hook.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import shutil
import shlex
from pathlib import Path
from typing import Any, Optional

from orchestrator.backend import (
    AgentBackend,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
    is_sandbox_violation,
)
from orchestrator.models import AgentResult, ReviewToolDecision

logger = logging.getLogger(__name__)

# Wall-clock backstop for a single cursor-agent phase. A hung agent (e.g. one
# whose stdout never closes) yields an error rather than blocking the
# orchestrator forever.
_PHASE_TIMEOUT_SECONDS = 1800


def _snapshot(path: Path) -> Optional[bytes]:
    """Return *path*'s current bytes, or None if it does not exist.

    Used before the backend overwrites a ``.cursor/`` file so a project's own
    committed version can be restored on cleanup instead of being clobbered.
    """
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _restore_or_remove(path: Path, original: Optional[bytes]) -> None:
    """Restore *path* to *original* bytes, or delete it if it did not pre-exist.

    A None *original* means the backend created the file, so it is unlinked.
    Otherwise the pre-existing bytes are written back verbatim.
    """
    if original is None:
        if path.exists():
            path.unlink()
    else:
        path.write_bytes(original)


# ---------------------------------------------------------------------------
# MCP server script for ReviewDecision
# ---------------------------------------------------------------------------

# Inline Python script that acts as a stdio MCP server exposing ReviewDecision.
# The backend captures the decision from the ACP event stream, not from this
# server's response — the server just needs to acknowledge the tool call so
# the agent sees success.
_MCP_SERVER_SCRIPT = r'''#!/usr/bin/env python3
"""Minimal stdio MCP server exposing the ReviewDecision tool.

Reads JSON-RPC from stdin, writes to stdout. Handles:
- initialize (MCP handshake)
- tools/list (returns ReviewDecision definition)
- tools/call for ReviewDecision (returns confirmation)
"""
import json
import sys

TOOL_DEF = {
    "name": "ReviewDecision",
    "description": "Submit the final review decision for the implementation",
    "inputSchema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["APPROVE", "FEEDBACK", "ESCALATE"],
                "description": "The review decision",
            },
            "summary": {
                "type": "string",
                "description": "Brief summary of the review findings",
            },
            "criteria_assessment": {
                "type": "array",
                "description": "Optional structured assessment of success criteria",
                "items": {"type": "object"},
            },
            "issues": {
                "type": "array",
                "description": "List of issues for FEEDBACK decisions",
                "items": {"type": "object"},
            },
            "reason": {
                "type": "string",
                "description": "Reason for ESCALATE decisions",
            },
        },
        "required": ["decision", "summary"],
    },
}


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle(request: dict) -> dict | None:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "orchestrator-review", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # notification, no response

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": [TOOL_DEF]},
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        decision = arguments.get("decision", "UNKNOWN")
        if tool_name == "ReviewDecision":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Review decision '{decision}' recorded successfully.",
                        }
                    ]
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            send(response)


if __name__ == "__main__":
    main()
'''


def _write_cursor_mcp_config(worktree: Path) -> dict[str, Optional[bytes]]:
    """Write ``.cursor/mcp.json`` declaring the ReviewDecision MCP server.

    Creates the ``.cursor/`` directory if needed and writes both the config
    file and the server script. Any pre-existing target files are snapshotted
    first and returned so :func:`_remove_cursor_mcp_config` can restore a
    project's own committed versions instead of deleting them.
    """
    cursor_dir = worktree / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    server_script = cursor_dir / "_review_mcp_server.py"
    config_path = cursor_dir / "mcp.json"
    originals: dict[str, Optional[bytes]] = {
        "_review_mcp_server.py": _snapshot(server_script),
        "mcp.json": _snapshot(config_path),
    }

    # Write the MCP server script
    server_script.write_text(_MCP_SERVER_SCRIPT)

    # Write mcp.json pointing to the server script
    mcp_config = {
        "mcpServers": {
            "orchestrator": {
                "command": "python3",
                "args": [str(server_script)],
            }
        }
    }
    config_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
    return originals


def _remove_cursor_mcp_config(
    worktree: Path, originals: Optional[dict[str, Optional[bytes]]] = None
) -> None:
    """Restore or remove the ``.cursor/mcp.json`` and server script.

    Files that pre-existed the run (snapshotted in *originals*) are restored to
    their original bytes; files the backend created are unlinked. Removes the
    ``.cursor/`` directory only if it is empty after cleanup. Silently succeeds
    if the files don't exist.
    """
    cursor_dir = worktree / ".cursor"
    originals = originals or {}
    for name in ("mcp.json", "_review_mcp_server.py"):
        _restore_or_remove(cursor_dir / name, originals.get(name))

    # Remove .cursor/ if empty
    if cursor_dir.exists() and not any(cursor_dir.iterdir()):
        cursor_dir.rmdir()


# ---------------------------------------------------------------------------
# cursor-agent binary discovery
# ---------------------------------------------------------------------------


class CursorAgentNotFoundError(RuntimeError):
    """Raised when the ``cursor-agent`` binary is not found on $PATH."""

    def __init__(self) -> None:
        super().__init__(
            "cursor-agent binary not found on $PATH. "
            "Install the Cursor CLI (v1.7+) and ensure `cursor-agent` is available. "
            "See https://docs.cursor.com/cli for installation instructions."
        )


# ---------------------------------------------------------------------------
# Sandbox enforcement hook (print mode)
# ---------------------------------------------------------------------------


def _write_sandbox_hook(
    worktree: Path, host_repo_path: Path
) -> dict[str, Optional[bytes]]:
    """Write a ``.cursor/hooks.json`` beforeShellExecution hook that enforces
    the worktree sandbox.

    In print mode there is no in-process permission round-trip, so sandbox
    policy is applied by a hook script cursor-agent runs before each shell
    command. The script delegates to the shared
    :func:`~orchestrator.backend.is_sandbox_violation`; a deny overrides
    ``--force``.

    Any pre-existing target files are snapshotted first and returned so
    :func:`_remove_sandbox_hook` can restore a project's own committed versions
    instead of clobbering them.
    """
    cursor_dir = worktree / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    hook_script = cursor_dir / "_sandbox_hook.py"
    hooks_path = cursor_dir / "hooks.json"
    originals: dict[str, Optional[bytes]] = {
        "_sandbox_hook.py": _snapshot(hook_script),
        "hooks.json": _snapshot(hooks_path),
    }

    # Embed is_sandbox_violation's exact source so the hook is self-contained.
    # Importing orchestrator.backend would pull the heavy package __init__ and
    # crash the hook — which cursor-agent then fails OPEN on (allowing the
    # command). Embedding the source keeps the policy identical with no drift.
    fn_src = inspect.getsource(is_sandbox_violation)
    hook_script.write_text(
        "#!/usr/bin/env python3\n"
        "from __future__ import annotations\n"
        "import json, re, sys\n"
        "from pathlib import Path\n"
        "from typing import Optional\n"
        "\n"
        + fn_src
        + "\n"
        "try:\n"
        "    data = json.load(sys.stdin)\n"
        "except Exception:\n"
        "    print(json.dumps({'permission': 'allow'}))\n"
        "    sys.exit(0)\n"
        "command = data.get('command', '') or ''\n"
        f"violation, reason = is_sandbox_violation(command, Path({str(host_repo_path)!r}), Path({str(worktree)!r}))\n"
        "if violation:\n"
        "    print(json.dumps({'permission': 'deny',\n"
        "                      'agentMessage': reason or 'Blocked by worktree sandbox policy',\n"
        "                      'userMessage': reason or 'sandbox: blocked'}))\n"
        "else:\n"
        "    print(json.dumps({'permission': 'allow'}))\n"
    )

    hooks_config = {
        "version": 1,
        "hooks": {
            "beforeShellExecution": [
                # shlex.quote so a worktree path with a space stays shell-safe;
                # an unquoted path makes cursor-agent fail to spawn the hook and
                # fall open, silently disabling the sandbox.
                {
                    "command": f"python3 {shlex.quote(str(hook_script))}",
                    "type": "command",
                }
            ]
        },
    }
    hooks_path.write_text(json.dumps(hooks_config, indent=2) + "\n")
    return originals


def _remove_sandbox_hook(
    worktree: Path, originals: Optional[dict[str, Optional[bytes]]] = None
) -> None:
    """Restore or remove the sandbox hook files.

    Files that pre-existed the run (snapshotted in *originals*) are restored;
    files the backend created are unlinked. Removes ``.cursor/`` if it becomes
    empty.
    """
    cursor_dir = worktree / ".cursor"
    originals = originals or {}
    for name in ("hooks.json", "_sandbox_hook.py"):
        _restore_or_remove(cursor_dir / name, originals.get(name))
    if cursor_dir.exists() and not any(cursor_dir.iterdir()):
        cursor_dir.rmdir()


# ---------------------------------------------------------------------------
# CursorBackend (print mode)
# ---------------------------------------------------------------------------

# Tool names that carry a ReviewDecision (plain or MCP-namespaced).
_REVIEW_DECISION_NAMES = frozenset({
    "ReviewDecision",
    "mcp__orchestrator__ReviewDecision",
})


class CursorBackend:
    """Runs an agent phase via ``cursor-agent`` print mode (non-interactive).

    Spawns ``cursor-agent -p --force --output-format stream-json`` and parses
    the newline-delimited JSON event stream. Print mode runs autonomously to
    completion (unlike interactive ACP, which holds turns waiting for the
    operator), which is what the orchestrator needs.

    Sandbox enforcement is applied out-of-process via a ``.cursor/hooks.json``
    beforeShellExecution hook (see :func:`_write_sandbox_hook`). The
    ReviewDecision MCP tool is exposed via ``.cursor/mcp.json`` during REVIEW.

    Print mode cannot ask the operator interactive questions, so
    ``on_question`` / suspension does not apply to this backend; the agent runs
    to a decision autonomously.
    """

    async def run(self, request: SessionRequest) -> AgentResult:
        if shutil.which("cursor-agent") is None:
            raise CursorAgentNotFoundError()

        wrote_mcp = False
        captured_review_decision: Optional[ReviewToolDecision] = None
        session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False
        saw_result_event = False
        proc = None
        hook_originals: dict[str, Optional[bytes]] = {}
        mcp_originals: dict[str, Optional[bytes]] = {}

        try:
            # Always enforce the sandbox via a beforeShellExecution hook.
            hook_originals = _write_sandbox_hook(request.cwd, request.host_repo_path)
            if request.expose_review_tool:
                mcp_originals = _write_cursor_mcp_config(request.cwd)
                wrote_mcp = True

            cmd = ["cursor-agent", "-p", "--force",
                   "--output-format", "stream-json"]
            if wrote_mcp:
                cmd.append("--approve-mcps")
            if request.resume_session_id:
                cmd += ["--resume", request.resume_session_id]
            cmd.append(request.prompt)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(request.cwd),
                env=request.env or None,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # stream-json emits one JSON object per line; a single line (e.g. a
                # large content block) easily exceeds asyncio's 64KB default and
                # would raise "Separator is found, but chunk is longer than limit".
                limit=16 * 1024 * 1024,
            )

            # Drain stderr concurrently: it is a PIPE, so >64KB of stderr would
            # block the child while we iterate stdout, deadlocking the phase.
            assert proc.stderr is not None
            stderr_task = asyncio.create_task(proc.stderr.read())

            try:
                (
                    session_id,
                    error,
                    completed,
                    saw_result_event,
                    captured_review_decision,
                ) = await asyncio.wait_for(
                    self._consume_stream(request, proc),
                    timeout=_PHASE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                error = (
                    f"cursor-agent phase exceeded {_PHASE_TIMEOUT_SECONDS}s"
                )
                logger.error(
                    "cursor-agent phase exceeded %ss; killing process",
                    _PHASE_TIMEOUT_SECONDS,
                )
                stderr_task.cancel()
                # The process is killed in the finally block below.

            if error is None or not saw_result_event:
                await proc.wait()
                stderr_text = ""
                try:
                    stderr_text = (await stderr_task).decode(
                        "utf-8", errors="replace"
                    )
                except asyncio.CancelledError:
                    pass
                rc = proc.returncode
                if not completed and error is None and rc not in (0, None):
                    error = (
                        f"cursor-agent exited with code {rc}: "
                        f"{stderr_text.strip()[:500]}"
                    ).strip()
                    logger.error(
                        "cursor-agent exited non-zero (code %s): %s",
                        rc,
                        stderr_text.strip()[:500],
                    )
                # Exit cleanly but no result event: the phase outcome is
                # ambiguous, so surface it as an error rather than reporting an
                # empty success.
                elif not saw_result_event and error is None:
                    error = (
                        f"cursor-agent produced no result event "
                        f"(exit {rc})"
                    )
                    logger.warning(
                        "cursor-agent produced no result event (exit %s)", rc
                    )
            else:
                await proc.wait()
                try:
                    await stderr_task
                except asyncio.CancelledError:
                    pass
        except CursorAgentNotFoundError:
            raise
        except Exception as e:
            error = str(e)
            logger.error("cursor-agent backend failed: %s", e, exc_info=True)
        finally:
            # Always kill a still-running process so a hung or timed-out agent
            # cannot leak.
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:  # pragma: no cover - defensive
                    pass
            _remove_sandbox_hook(request.cwd, hook_originals)
            if wrote_mcp:
                _remove_cursor_mcp_config(request.cwd, mcp_originals)

        if error:
            return AgentResult(
                completed=False,
                suspended=False,
                session_id=session_id,
                error=error,
                review_decision=captured_review_decision,
            )
        return AgentResult(
            completed=completed,
            suspended=False,
            session_id=session_id,
            review_decision=captured_review_decision,
        )

    async def _consume_stream(
        self, request: SessionRequest, proc: Any
    ) -> tuple[Optional[str], Optional[str], bool, bool, Optional[ReviewToolDecision]]:
        """Iterate the stream-json stdout, returning the accumulated outcome.

        Returns ``(session_id, error, completed, saw_result_event,
        captured_review_decision)``. Wrapped by :meth:`run` in a wall-clock
        timeout so a never-ending stdout cannot hang the orchestrator.
        """
        captured_review_decision: Optional[ReviewToolDecision] = None
        session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False
        saw_result_event = False

        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("stream-json: non-JSON line: %s", line[:200])
                continue

            captured_review_decision = self._handle_event(
                event, request, captured_review_decision
            )

            etype = event.get("type")
            if etype == "system" and event.get("subtype") == "init":
                session_id = event.get("session_id") or session_id
            elif etype == "result":
                saw_result_event = True
                if event.get("session_id"):
                    session_id = event["session_id"]
                if event.get("is_error", False):
                    error = event.get("result") or "Agent returned error"
                else:
                    completed = True

        return session_id, error, completed, saw_result_event, captured_review_decision

    def _handle_event(
        self,
        event: dict,
        request: SessionRequest,
        captured_review_decision: Optional[ReviewToolDecision],
    ) -> Optional[ReviewToolDecision]:
        """Normalize one stream-json event into LogEvents; capture ReviewDecision."""
        etype = event.get("type")

        if etype == "assistant":
            # ``message`` may be JSON null, so guard before .get("content").
            content = (event.get("message") or {}).get("content", []) or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    if request.on_log:
                        request.on_log(TextEvent(text=block.get("text", "")))
            return captured_review_decision

        if etype == "tool_call":
            subtype = event.get("subtype")
            call_id = event.get("call_id", "")
            tool_call = event.get("tool_call", {}) or {}
            # Shape: {"<name>ToolCall": {"args": {...}, "result": {...}}}
            for key, body in tool_call.items():
                if not isinstance(body, dict):
                    continue
                raw_args = body.get("args")
                args = raw_args if isinstance(raw_args, dict) else {}
                if subtype == "started":
                    if request.on_log:
                        request.on_log(ToolCallEvent(
                            tool_id=call_id,
                            name=key,
                            input=args,
                            description=args.get("command") or args.get("path"),
                        ))
                    captured_review_decision = self._maybe_capture_review(
                        key, args, request, captured_review_decision
                    )
                elif subtype == "completed":
                    result = body.get("result")
                    is_err = isinstance(result, dict) and (
                        "rejected" in result or "error" in result
                    )
                    if is_err:
                        # Surface sandbox denies / tool rejections in the daemon
                        # log, not just the per-phase stream.
                        logger.warning(
                            "cursor-agent tool %s rejected/errored: %s",
                            key,
                            json.dumps(result)[:500],
                        )
                    if request.on_log:
                        content_text = json.dumps(result)[:2000] if result is not None else ""
                        request.on_log(ToolResultEvent(
                            tool_use_id=call_id,
                            content=content_text,
                            is_error=is_err,
                        ))
                    captured_review_decision = self._maybe_capture_review(
                        key, args, request, captured_review_decision
                    )
            return captured_review_decision

        if etype == "result":
            if request.on_log:
                request.on_log(ResultEvent(
                    subtype=event.get("subtype", "success"),
                    duration_ms=event.get("duration_ms", 0),
                    total_cost_usd=event.get("total_cost_usd", 0.0),
                    num_turns=event.get("num_turns", 0),
                    is_error=event.get("is_error", False),
                    session_id=event.get("session_id"),
                    result_text=event.get("result"),
                ))
        return captured_review_decision

    def _maybe_capture_review(
        self,
        key: str,
        args: dict,
        request: SessionRequest,
        captured: Optional[ReviewToolDecision],
    ) -> Optional[ReviewToolDecision]:
        """Capture the first ReviewDecision tool call from the event stream.

        An MCP tool call is logged as ``mcpToolCall`` whose args wrap the real
        call: ``{"name": "orchestrator-ReviewDecision", "args": {"decision": ...}}``.
        Unwrap the nested ``args`` (or ``arguments``) to find the decision.
        """
        if captured is not None or not request.expose_review_tool:
            return captured
        # Identify a ReviewDecision call by the tool name/key, not by a loose
        # substring scan of the whole payload: an unrelated tool that happens to
        # carry a top-level ``decision`` key must not be mistaken for a review.
        raw_name = args.get("name")
        tool_name = raw_name if isinstance(raw_name, str) else ""
        looks_like_review = any(
            name in str(key) or name in tool_name
            for name in _REVIEW_DECISION_NAMES
        )
        if not looks_like_review:
            return captured

        payload = args
        if "decision" not in payload:
            for nest_key in ("args", "arguments"):
                inner = payload.get(nest_key)
                if isinstance(inner, dict) and "decision" in inner:
                    payload = inner
                    break
        decision = payload.get("decision")
        if decision:
            captured = ReviewToolDecision(
                decision=str(decision).upper(),
                summary=payload.get("summary", ""),
                criteria_assessment=payload.get("criteria_assessment"),
                issues=payload.get("issues"),
                reason=payload.get("reason"),
            )
            if request.on_review_decision:
                request.on_review_decision(captured)
        return captured


# Assert CursorBackend satisfies the AgentBackend protocol at import time.
_: AgentBackend = CursorBackend()
