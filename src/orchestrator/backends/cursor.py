# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_cursor - CursorBackend: ACP-based Cursor/Composer backend
"""Cursor/Composer backend via ACP (Agent Client Protocol).

Implements :class:`~orchestrator.backend.AgentBackend` by spawning
``cursor-agent acp`` as a subprocess and speaking JSON-RPC 2.0 over its
stdin/stdout. This module is the ONLY place in the orchestrator that interacts
with the ``cursor-agent`` binary; everything above the seam talks through
:class:`~orchestrator.backend.SessionRequest` and
:class:`~orchestrator.models.AgentResult`.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from orchestrator.backend import (
    AgentBackend,
    LogEvent,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolDecision,
    ToolResultEvent,
    ToolUse,
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
# ACP JSON-RPC transport
# ---------------------------------------------------------------------------


class CursorAgentNotFoundError(RuntimeError):
    """Raised when the ``cursor-agent`` binary is not found on $PATH."""

    def __init__(self) -> None:
        super().__init__(
            "cursor-agent binary not found on $PATH. "
            "Install the Cursor CLI (v1.7+) and ensure `cursor-agent` is available. "
            "See https://docs.cursor.com/cli for installation instructions."
        )


class ACPTransport:
    """Low-level JSON-RPC 2.0 transport over a ``cursor-agent acp`` subprocess.

    Sends requests with auto-incrementing ``id`` via stdin, reads
    newline-delimited JSON-RPC messages from stdout, correlates responses
    by ``id``, and buffers incoming notifications into an asyncio queue.
    """

    def __init__(self) -> None:
        self._process: Optional[asyncio.subprocess.Process] = None
        self._next_id: int = 1
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._notifications: asyncio.Queue[dict] = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None
        self._closed = False

    async def start(self) -> None:
        """Spawn ``cursor-agent acp`` and begin reading stdout."""
        binary = shutil.which("cursor-agent")
        if binary is None:
            raise CursorAgentNotFoundError()

        self._process = await asyncio.create_subprocess_exec(
            binary,
            "acp",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        atexit.register(self._sync_cleanup)

    async def _read_loop(self) -> None:
        """Read newline-delimited JSON from stdout and dispatch."""
        assert self._process is not None
        assert self._process.stdout is not None
        while True:
            line = await self._process.stdout.readline()
            if not line:
                # EOF — subprocess exited
                break
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            try:
                msg = json.loads(line_str)
            except json.JSONDecodeError:
                logger.warning("ACP: non-JSON line from cursor-agent: %s", line_str[:200])
                continue

            msg_id = msg.get("id")
            # A response has an id that matches a pending request
            if msg_id is not None and msg_id in self._pending:
                future = self._pending.pop(msg_id)
                if not future.done():
                    future.set_result(msg)
            else:
                # Notification or unsolicited message
                await self._notifications.put(msg)

    async def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and wait for the correlated response."""
        assert self._process is not None
        assert self._process.stdin is not None

        req_id = self._next_id
        self._next_id += 1

        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict] = loop.create_future()
        self._pending[req_id] = future

        data = json.dumps(request) + "\n"
        self._process.stdin.write(data.encode("utf-8"))
        await self._process.stdin.drain()

        result = await future
        if "error" in result:
            error = result["error"]
            raise RuntimeError(
                f"ACP JSON-RPC error ({error.get('code', '?')}): {error.get('message', 'unknown')}"
            )
        return result.get("result", {})

    async def send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a one-way JSON-RPC notification (no ``id``, no response)."""
        assert self._process is not None
        assert self._process.stdin is not None

        notification: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notification["params"] = params

        data = json.dumps(notification) + "\n"
        self._process.stdin.write(data.encode("utf-8"))
        await self._process.stdin.drain()

    async def recv_notification(self, timeout: float | None = None) -> dict | None:
        """Return the next buffered notification, or None on timeout."""
        try:
            return await asyncio.wait_for(self._notifications.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def _sync_cleanup(self) -> None:
        """Best-effort synchronous cleanup for atexit."""
        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
            except ProcessLookupError:
                pass

    async def close(self) -> None:
        """Gracefully shut down the subprocess and reader task."""
        self._closed = True
        if self._process and self._process.returncode is None:
            if self._process.stdin:
                try:
                    self._process.stdin.close()
                except Exception:
                    pass
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Cancel any pending futures
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    @property
    def is_alive(self) -> bool:
        """True if the subprocess is still running."""
        return self._process is not None and self._process.returncode is None


# ---------------------------------------------------------------------------
# CursorBackend
# ---------------------------------------------------------------------------

# Pattern for matching ReviewDecision tool calls in the ACP event stream.
# May appear as plain "ReviewDecision" or MCP-namespaced.
_REVIEW_DECISION_NAMES = frozenset({
    "ReviewDecision",
    "mcp__orchestrator__ReviewDecision",
})


class CursorBackend:
    """Runs an agent phase via the Cursor ACP protocol (cursor-agent acp).

    Translates a :class:`~orchestrator.backend.SessionRequest` into ACP
    JSON-RPC calls: ``system/init``, ``session/new`` or ``session/load``,
    then processes ``session/update`` notifications for sandbox enforcement,
    question forwarding, review-decision capture, and log-event normalization.
    """

    async def run(self, request: SessionRequest) -> AgentResult:
        # Validate binary availability up front
        if shutil.which("cursor-agent") is None:
            raise CursorAgentNotFoundError()

        wrote_mcp_config = False
        transport = ACPTransport()

        captured_question: Optional[dict] = None
        captured_review_decision: Optional[ReviewToolDecision] = None
        session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False

        try:
            # Step 1: Write MCP config if review tool is needed
            if request.expose_review_tool:
                _write_cursor_mcp_config(request.cwd)
                wrote_mcp_config = True

            # Step 2: Start ACP transport
            await transport.start()

            # Step 3: system/init handshake
            init_result = await transport.send_request("system/init", {
                "protocolVersion": "1.0",
                "clientInfo": {"name": "vibe-engineer-orchestrator", "version": "1.0.0"},
            })
            session_id = init_result.get("session_id")

            # Step 4: Create or resume session
            if request.resume_session_id:
                await transport.send_request("session/load", {
                    "sessionId": request.resume_session_id,
                    "prompt": request.prompt,
                })
                session_id = request.resume_session_id
            else:
                new_result = await transport.send_request("session/new", {
                    "model": "composer",
                    "permissions": "auto-allow",
                    "cwd": str(request.cwd),
                    "prompt": request.prompt,
                })
                if new_result.get("sessionId"):
                    session_id = new_result["sessionId"]

            # Step 5: Event loop — process notifications until session ends
            while transport.is_alive:
                msg = await transport.recv_notification(timeout=300.0)
                if msg is None:
                    # Timeout or EOF without a result — treat as error
                    if not transport.is_alive:
                        error = "cursor-agent process exited unexpectedly"
                    else:
                        error = "Timed out waiting for ACP notification"
                    break

                method = msg.get("method", "")
                params = msg.get("params", {})

                # --- Session result (completion) ---
                if method == "session/result":
                    completed = not params.get("isError", False)
                    if params.get("isError"):
                        error = params.get("errorMessage", "Agent returned error")
                    if params.get("sessionId"):
                        session_id = params["sessionId"]

                    # Emit ResultEvent
                    if request.on_log:
                        request.on_log(ResultEvent(
                            subtype="error" if params.get("isError") else "success",
                            duration_ms=params.get("durationMs", 0),
                            total_cost_usd=params.get("totalCostUsd", 0.0),
                            num_turns=params.get("numTurns", 0),
                            is_error=params.get("isError", False),
                            session_id=params.get("sessionId"),
                            result_text=params.get("resultText"),
                        ))
                    break

                # --- Permission request (sandbox enforcement) ---
                if method == "session/request_permission":
                    tool_name = params.get("toolName", "")
                    tool_input = params.get("toolInput", {})
                    command = params.get("command", tool_input.get("command", ""))
                    cwd = params.get("cwd")

                    tool_use = ToolUse(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        command=command,
                        cwd=cwd,
                    )

                    is_violation, reason = is_sandbox_violation(
                        command or "", request.host_repo_path, request.cwd
                    )

                    # Reply to the permission request
                    reply_id = msg.get("id")
                    if reply_id is not None:
                        if is_violation:
                            response = {
                                "jsonrpc": "2.0",
                                "id": reply_id,
                                "result": {
                                    "decision": "deny",
                                    "reason": reason,
                                },
                            }
                        else:
                            response = {
                                "jsonrpc": "2.0",
                                "id": reply_id,
                                "result": {"decision": "allow"},
                            }
                        assert transport._process is not None
                        assert transport._process.stdin is not None
                        data = json.dumps(response) + "\n"
                        transport._process.stdin.write(data.encode("utf-8"))
                        await transport._process.stdin.drain()
                    continue

                # --- Question forwarding ---
                if method == "cursor/ask_question":
                    question_text = params.get("question", "")
                    options = params.get("options", [])
                    header = params.get("header", "")
                    multi_select = params.get("multiSelect", False)

                    captured_question = {
                        "question": question_text,
                        "options": options,
                        "header": header,
                        "multiSelect": multi_select,
                        "all_questions": params.get("allQuestions", [
                            {"question": question_text, "options": options,
                             "header": header, "multiSelect": multi_select}
                        ]),
                    }
                    if request.on_question:
                        request.on_question(captured_question)
                    break  # Session suspended

                # --- session/update — log events and ReviewDecision capture ---
                if method == "session/update":
                    content_blocks = params.get("content", [])
                    for block in content_blocks:
                        block_type = block.get("type", "")

                        if block_type == "text":
                            if request.on_log:
                                request.on_log(TextEvent(text=block.get("text", "")))

                        elif block_type == "tool_use":
                            name = block.get("name", "")
                            tool_input = block.get("input", {})
                            tool_id = block.get("id", "")
                            description = tool_input.get("description") if isinstance(tool_input, dict) else None

                            if request.on_log:
                                request.on_log(ToolCallEvent(
                                    tool_id=tool_id,
                                    name=name,
                                    input=tool_input if isinstance(tool_input, dict) else {},
                                    description=description,
                                ))

                            # Check for ReviewDecision tool call
                            if (
                                captured_review_decision is None
                                and name in _REVIEW_DECISION_NAMES
                                and isinstance(tool_input, dict)
                            ):
                                captured_review_decision = ReviewToolDecision(
                                    decision=tool_input.get("decision", "").upper(),
                                    summary=tool_input.get("summary", ""),
                                    criteria_assessment=tool_input.get("criteria_assessment"),
                                    issues=tool_input.get("issues"),
                                    reason=tool_input.get("reason"),
                                )
                                if request.on_review_decision:
                                    request.on_review_decision(captured_review_decision)

                        elif block_type == "tool_result":
                            if request.on_log:
                                content_text = block.get("content", "")
                                if not isinstance(content_text, str):
                                    content_text = str(content_text)
                                request.on_log(ToolResultEvent(
                                    tool_use_id=block.get("tool_use_id", ""),
                                    content=content_text,
                                    is_error=block.get("is_error", False),
                                ))
                    continue

                # Unknown method — log and continue (defensive, per risk note)
                logger.debug("ACP: ignoring unknown method %r", method)

        except CursorAgentNotFoundError:
            raise
        except Exception as e:
            error = str(e)
        finally:
            await transport.close()
            if wrote_mcp_config:
                _remove_cursor_mcp_config(request.cwd)

        # Build result
        if captured_question:
            return AgentResult(
                completed=False,
                suspended=True,
                session_id=session_id,
                question=captured_question,
            )

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


# Assert CursorBackend satisfies the AgentBackend protocol at import time.
_: AgentBackend = CursorBackend()
