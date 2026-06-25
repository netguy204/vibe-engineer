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

# JSON schema for the ReviewDecision tool, matching the Claude MCP tool contract.
REVIEW_DECISION_TOOL_SCHEMA: dict[str, Any] = {
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


def _write_cursor_mcp_config(worktree: Path) -> Path:
    """Write ``.cursor/mcp.json`` declaring the ReviewDecision MCP server.

    Creates the ``.cursor/`` directory if needed and writes both the config
    file and the server script. Returns the path to the config file.
    """
    cursor_dir = worktree / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    # Write the MCP server script
    server_script = cursor_dir / "_review_mcp_server.py"
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
    config_path = cursor_dir / "mcp.json"
    config_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
    return config_path


def _remove_cursor_mcp_config(worktree: Path) -> None:
    """Remove the ``.cursor/mcp.json`` and server script written by the backend.

    Silently succeeds if the files don't exist. Removes the ``.cursor/``
    directory only if it is empty after cleanup.
    """
    cursor_dir = worktree / ".cursor"
    for name in ("mcp.json", "_review_mcp_server.py"):
        path = cursor_dir / name
        if path.exists():
            path.unlink()

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


def _write_sandbox_hook(worktree: Path, host_repo_path: Path) -> None:
    """Write a ``.cursor/hooks.json`` beforeShellExecution hook that enforces
    the worktree sandbox.

    In print mode there is no in-process permission round-trip, so sandbox
    policy is applied by a hook script cursor-agent runs before each shell
    command. The script delegates to the shared
    :func:`~orchestrator.backend.is_sandbox_violation`; a deny overrides
    ``--force``.
    """
    cursor_dir = worktree / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    # Embed is_sandbox_violation's exact source so the hook is self-contained.
    # Importing orchestrator.backend would pull the heavy package __init__ and
    # crash the hook — which cursor-agent then fails OPEN on (allowing the
    # command). Embedding the source keeps the policy identical with no drift.
    fn_src = inspect.getsource(is_sandbox_violation)
    hook_script = cursor_dir / "_sandbox_hook.py"
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

    hooks_path = cursor_dir / "hooks.json"
    hooks_config = {
        "version": 1,
        "hooks": {
            "beforeShellExecution": [
                {"command": f"python3 {hook_script}", "type": "command"}
            ]
        },
    }
    hooks_path.write_text(json.dumps(hooks_config, indent=2) + "\n")


def _remove_sandbox_hook(worktree: Path) -> None:
    """Remove the sandbox hook files; remove ``.cursor/`` if it becomes empty."""
    cursor_dir = worktree / ".cursor"
    for name in ("hooks.json", "_sandbox_hook.py"):
        path = cursor_dir / name
        if path.exists():
            path.unlink()
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

        try:
            # Always enforce the sandbox via a beforeShellExecution hook.
            _write_sandbox_hook(request.cwd, request.host_repo_path)
            if request.expose_review_tool:
                _write_cursor_mcp_config(request.cwd)
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
            )

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
                    if event.get("session_id"):
                        session_id = event["session_id"]
                    if event.get("is_error", False):
                        error = event.get("result") or "Agent returned error"
                    else:
                        completed = True

            await proc.wait()
            if not completed and error is None and proc.returncode not in (0, None):
                stderr_text = ""
                if proc.stderr is not None:
                    stderr_text = (await proc.stderr.read()).decode(
                        "utf-8", errors="replace"
                    )
                error = (
                    f"cursor-agent exited with code {proc.returncode}: "
                    f"{stderr_text.strip()[:500]}"
                ).strip()
        except CursorAgentNotFoundError:
            raise
        except Exception as e:  # pragma: no cover - defensive
            error = str(e)
        finally:
            _remove_sandbox_hook(request.cwd)
            if wrote_mcp:
                _remove_cursor_mcp_config(request.cwd)

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

    def _handle_event(
        self,
        event: dict,
        request: SessionRequest,
        captured_review_decision: Optional[ReviewToolDecision],
    ) -> Optional[ReviewToolDecision]:
        """Normalize one stream-json event into LogEvents; capture ReviewDecision."""
        etype = event.get("type")

        if etype == "assistant":
            content = event.get("message", {}).get("content", []) or []
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
                args = body.get("args") if isinstance(body.get("args"), dict) else {}
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
        if not isinstance(args, dict):
            return captured
        payload = args
        if "decision" not in payload:
            for nest_key in ("args", "arguments"):
                inner = payload.get(nest_key)
                if isinstance(inner, dict) and "decision" in inner:
                    payload = inner
                    break
        decision = payload.get("decision")
        looks_like_review = (
            any(name in str(key) for name in _REVIEW_DECISION_NAMES)
            or "ReviewDecision" in json.dumps(args)
        )
        if decision and looks_like_review:
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
