# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - AgentBackend seam and normalized contract types
"""Backend-agnostic contract for executing agent phases.

The orchestrator runs each chunk phase through an :class:`AgentBackend` rather
than calling any specific agent SDK directly. This module defines the seam:
the normalized request/decision types and the protocol every backend
implements. Concrete backends (e.g. ``orchestrator.backends.claude.ClaudeBackend``)
translate a :class:`SessionRequest` onto their native mechanism and return the
shared :class:`~orchestrator.models.AgentResult`.

This module imports no agent SDK and must stay that way: it is the contract both
the Claude and future (Cursor/Composer) backends depend on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, Union

from orchestrator.models import AgentResult, ReviewToolDecision


# ---------------------------------------------------------------------------
# Normalized log event types
# ---------------------------------------------------------------------------
# Chunk: docs/chunks/backend_logparse - Backend-agnostic log events
#
# Every backend translates its native message stream into these event types
# before calling ``on_log``. Downstream consumers (log_parser, log_streaming)
# never touch vendor-specific shapes.


@dataclass
class TextEvent:
    """Agent emitted a text block."""

    text: str


@dataclass
class ToolCallEvent:
    """Agent invoked a tool."""

    tool_id: str
    name: str
    input: dict
    description: Optional[str] = None


@dataclass
class ToolResultEvent:
    """A tool returned a result."""

    tool_use_id: str
    content: str
    is_error: bool


@dataclass
class ResultEvent:
    """Session completed (success or error)."""

    subtype: str  # "success" | "error"
    duration_ms: int
    total_cost_usd: float
    num_turns: int
    is_error: bool
    session_id: Optional[str] = None
    result_text: Optional[str] = None


LogEvent = Union[TextEvent, ToolCallEvent, ToolResultEvent, ResultEvent]


class ToolDecision(StrEnum):
    """Decision a tool-use policy returns before a tool executes."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass
class ToolUse:
    """A tool invocation an agent is about to make, surfaced to policy.

    ``command`` and ``cwd`` are conveniences populated for shell/Bash tools so
    sandbox policy can inspect them without re-parsing ``tool_input``.
    """

    tool_name: str
    tool_input: dict
    command: Optional[str] = None
    cwd: Optional[str] = None


@dataclass
class SessionRequest:
    """Everything a backend needs to run (or resume) one agent phase.

    The orchestrator owns policy and passes it to the backend two ways:

    - **Sandbox context** (``host_repo_path`` + ``cwd``, the worktree): every
      backend gates tool use through the shared :func:`is_sandbox_violation`,
      expressed in :class:`ToolUse`/:class:`ToolDecision` terms, to keep agents
      inside their worktree. Carried as data (not a callback) so the deny reason
      survives to the agent.
    - **Observation callbacks** the backend invokes against its native event
      stream: ``on_question`` (agent asked the operator something — suspend and
      forward), ``on_review_decision`` (reviewer submitted its ReviewDecision),
      and ``on_log`` (per-message activity logging).

    Resume is folded into ``resume_session_id``; ``expose_review_tool`` asks the
    backend to make the orchestrator ReviewDecision tool available (REVIEW phase).
    """

    prompt: str
    cwd: Path
    host_repo_path: Path
    env: dict[str, str]
    max_turns: int
    allowed_tools: list[str] = field(default_factory=list)
    resume_session_id: Optional[str] = None
    expose_review_tool: bool = False
    on_question: Optional[Callable[[dict], None]] = None
    on_review_decision: Optional[Callable[[ReviewToolDecision], None]] = None
    on_log: Optional[Callable[["LogEvent"], None]] = None


class AgentBackend(Protocol):
    """Executes a single agent phase described by a :class:`SessionRequest`.

    Implementations own all vendor-specific machinery (process/SDK management,
    tool interception, session resume) and must return a populated
    :class:`~orchestrator.models.AgentResult`. Resume is folded into
    :attr:`SessionRequest.resume_session_id`; there is no separate entry point.
    """

    async def run(self, request: SessionRequest) -> AgentResult: ...


# Chunk: docs/chunks/orch_sandbox_enforcement - Sandbox violation detection logic
# Chunk: docs/chunks/orch_sandbox_shape - Shape-aware classification: rules apply
#   to command positions and their arguments, never to heredoc bodies, quoted
#   literals, or comment text
def is_sandbox_violation(
    command: str,
    host_repo_path: Path,
    worktree_path: Path,
) -> tuple[bool, Optional[str]]:
    """Check if a command violates sandbox rules.

    Detects commands that would escape the worktree sandbox and access
    the host repository or other forbidden locations. Pure path/string logic
    with no SDK dependency, so any backend's tool-use policy can reuse it.

    The classifier judges a command by its *shape* -- what it would execute --
    not by every byte of its content. The command is preprocessed (heredoc
    bodies and comments are data, not command; unquoted newlines are segment
    boundaries), tokenized at the shlex level with shell operators split into
    their own tokens, and the cd/git/host-path rules are applied per executed
    segment. Input that shlex cannot tokenize falls back to the legacy
    substring scan: the fallback fails toward denial, never toward allow.

    SELF-CONTAINMENT: the Cursor backend embeds this function's source
    verbatim (``inspect.getsource``) into a standalone hook script whose only
    top-level imports are ``sys``/``os``/``json``/``re``/``Path``/``Optional``.
    Keep every helper nested inside this function and import anything else
    (e.g. ``shlex``) locally.

    Args:
        command: The bash command string to check
        host_repo_path: Absolute path to the host repository (where orchestrator runs)
        worktree_path: Absolute path to the worktree (agent's sandbox)

    Returns:
        Tuple of (is_violation, reason) where reason explains the violation.
    """
    import shlex

    host_str = str(host_repo_path).rstrip("/")
    worktree_str = str(worktree_path).rstrip("/")

    def _legacy(cmd_text: str) -> tuple[bool, Optional[str]]:
        """Pre-shape substring scan, kept verbatim as the conservative
        fallback for input the tokenizer cannot handle."""
        # Pattern 1: Direct cd to host repo (with or without quotes)
        # Matches: cd /path/to/host, cd '/path/to/host', cd "/path/to/host"
        # Must be exact match (with optional trailing slash), not a prefix of worktree path
        cd_patterns = [
            f"cd {host_str}",
            f"cd '{host_str}'",
            f'cd "{host_str}"',
            f"cd {host_str}/",
            f"cd '{host_str}/'",
            f'cd "{host_str}/"',
        ]
        for pattern in cd_patterns:
            if pattern in cmd_text:
                # Make sure this isn't actually a path within the worktree
                # (e.g., cd /host/path/.ve/chunks/test/worktree should be allowed)
                cd_target_match = re.search(r"cd\s+['\"]?([^'\"\s]+)['\"]?", cmd_text)
                if cd_target_match:
                    cd_target = cd_target_match.group(1).rstrip("/")
                    # If the target is within the worktree, it's safe
                    if cd_target.startswith(worktree_str):
                        continue
                return (True, f"Blocked: cd to host repository path ({host_str})")

        # Pattern 2: Git commands with -C flag pointing to host repo
        # Matches: git -C /path/to/host ..., git -C '/path/to/host' ...
        git_c_patterns = [
            f"git -C {host_str}",
            f"git -C '{host_str}'",
            f'git -C "{host_str}"',
        ]
        for pattern in git_c_patterns:
            if pattern in cmd_text:
                # The worktree lives under the host repo, so `git -C <worktree>` --
                # ordinary in-worktree work -- matches these patterns too. Exempt it,
                # the way Patterns 1 and 3 already do. Anchored at a path boundary:
                # a sibling such as <worktree>-evil is outside the sandbox, and a
                # bare startswith would wave it through.
                c_target_match = re.search(r"git\s+-C\s+['\"]?([^'\"\s]+)", cmd_text)
                if c_target_match:
                    c_target = c_target_match.group(1).rstrip("/")
                    if c_target == worktree_str or c_target.startswith(worktree_str + "/"):
                        continue
                return (True, f"Blocked: git -C targeting host repository ({host_str})")

        # Pattern 3: Any git command containing host repo path as argument
        # This catches things like: git --git-dir=/host/path/.git
        # But allow paths within the worktree (which may contain the host path as prefix)
        if "git " in cmd_text and host_str in cmd_text:
            # Check if the reference is to a path within the worktree
            # If the command references the worktree path, it's allowed
            if worktree_str not in cmd_text:
                return (True, f"Blocked: git command references host repository path ({host_str})")

        # Pattern 4: cd to absolute path outside worktree
        # Match cd followed by absolute path
        cd_abs_pattern = re.compile(r"cd\s+['\"]?(/[^'\"\s]+)['\"]?")
        for match in cd_abs_pattern.finditer(cmd_text):
            target_path = match.group(1).rstrip("/")
            # Allow paths within worktree
            if target_path.startswith(worktree_str):
                continue
            # Allow common system paths that agents might need
            safe_prefixes = ["/tmp", "/var/tmp", "/dev"]
            if any(target_path.startswith(p) for p in safe_prefixes):
                continue
            # Block cd to other absolute paths
            return (True, f"Blocked: cd to absolute path outside worktree ({target_path})")

        return (False, None)

    def _strip(text: str) -> tuple[str, bool]:
        """Quote-aware preprocessing: drop heredoc bodies and comments (data,
        not command -- the line introducing a heredoc IS still checked), and
        turn unquoted newlines into ``;`` so each line is its own segment.
        Text inside quotes passes through untouched. Never raises.

        Returns ``(preprocessed_text, force_legacy)``. ``force_legacy`` is set
        when a double-quoted region contains command substitution (backtick or
        ``$(``): bash executes those, but shlex-level tokenization would treat
        them as data, so the caller must use the conservative substring
        fallback instead. Single quotes suppress substitution and stay opaque.
        """
        out: list[str] = []
        pending: list[tuple[str, bool]] = []  # heredocs opened on current line
        in_single = in_double = False
        force_legacy = False
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if in_single:
                out.append(ch)
                if ch == "'":
                    in_single = False
                i += 1
                continue
            if in_double:
                if ch == "\\" and i + 1 < n:
                    out.append(text[i:i + 2])
                    i += 2
                    continue
                if ch == "`" or (ch == "$" and i + 1 < n and text[i + 1] == "("):
                    force_legacy = True
                out.append(ch)
                if ch == '"':
                    in_double = False
                i += 1
                continue
            if ch == "\\":
                if i + 1 < n and text[i + 1] == "\n":
                    i += 2  # line continuation: splice
                    continue
                out.append(text[i:i + 2])
                i += 2
                continue
            if ch == "'":
                in_single = True
                out.append(ch)
                i += 1
                continue
            if ch == '"':
                in_double = True
                out.append(ch)
                i += 1
                continue
            if ch == "#" and (not out or out[-1] in " \t;&|()"):
                while i < n and text[i] != "\n":
                    i += 1  # comment: data until end of line
                continue
            if ch == "<":
                run = 1
                while i + run < n and text[i + run] == "<":
                    run += 1
                if run != 2:  # lone redirect or <<< herestring: not a heredoc
                    out.append("<" * run)
                    i += run
                    continue
                out.append("<<")
                j = i + 2
                strip_tabs = False
                if j < n and text[j] == "-":
                    strip_tabs = True
                    out.append("-")
                    j += 1
                while j < n and text[j] in " \t":
                    out.append(text[j])
                    j += 1
                marker = None
                if j < n and text[j] in "'\"":
                    k = text.find(text[j], j + 1)
                    if k != -1:
                        marker = text[j + 1:k]
                        out.append(text[j:k + 1])
                        j = k + 1
                else:
                    k = j
                    while k < n and (text[k].isalnum() or text[k] in "_.-"):
                        k += 1
                    if k > j:
                        marker = text[j:k]
                        out.append(text[j:k])
                        j = k
                if marker:
                    pending.append((marker, strip_tabs))
                i = j
                continue
            if ch == "\n":
                i += 1
                for marker, strip_tabs in pending:
                    while i < n:  # skip body lines until the terminator line
                        eol = text.find("\n", i)
                        line, i = (text[i:], n) if eol == -1 else (text[i:eol], eol + 1)
                        if (line.lstrip("\t") if strip_tabs else line) == marker:
                            break
                pending = []
                out.append(";")
                continue
            out.append(ch)
            i += 1
        return "".join(out), force_legacy

    def _within_worktree(path: str) -> bool:
        # Anchored at a path boundary: a sibling such as <worktree>-evil is
        # outside the sandbox, and a bare startswith would wave it through.
        p = path.rstrip("/")
        return p == worktree_str or p.startswith(worktree_str + "/")

    def _check_segments(tokens: list[str]) -> tuple[bool, Optional[str]]:
        separator_chars = set(";&|()`")
        punctuation_chars = set(";&|()`<>")
        env_assign = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
        wrappers = {"env", "command", "exec", "nohup", "nice", "time", "sudo", "xargs"}

        segments: list[list[str]] = []
        current: list[str] = []
        for tok in tokens:
            if tok and all(c in punctuation_chars for c in tok):
                # Separator only when the run is purely command-separating
                # (&&, ;, |, |&, parens, backtick). Any run containing a
                # redirection char (<, >, >>, >&, 2>&1's >&) is dropped but
                # keeps the segment open, so a redirection target stays
                # visible to the git host-path rule below.
                if all(c in separator_chars for c in tok):
                    if current:
                        segments.append(current)
                        current = []
                continue
            current.append(tok)
        if current:
            segments.append(current)

        for seg in segments:
            # Command word: skip env assignments, unwrap command wrappers
            # (env git -C <host> must not hide git behind env).
            idx = 0
            while True:
                while idx < len(seg) and env_assign.match(seg[idx]):
                    idx += 1
                if idx < len(seg) and seg[idx] in wrappers:
                    idx += 1
                    while idx < len(seg) and seg[idx].startswith("-"):
                        idx += 1
                    continue
                break
            if idx >= len(seg):
                continue
            cmd = seg[idx]
            args = seg[idx + 1:]

            if cmd == "cd":
                target = args[0].rstrip("/") if args else ""
                if target.startswith("/") and not _within_worktree(target):
                    if target == host_str or target.startswith(host_str + "/"):
                        return (True, f"Blocked: cd to host repository path ({host_str})")
                    safe_prefixes = ("/tmp", "/var/tmp", "/dev")
                    if not any(
                        target == p or target.startswith(p + "/")
                        for p in safe_prefixes
                    ):
                        return (
                            True,
                            f"Blocked: cd to absolute path outside worktree ({target})",
                        )
                continue

            if cmd == "git" or cmd.endswith("/git"):
                j = 0
                while j < len(args):
                    if args[j] == "-C" and j + 1 < len(args):
                        c_target = args[j + 1].rstrip("/")
                        j += 2
                    elif args[j].startswith("-C") and len(args[j]) > 2:
                        c_target = args[j][2:].rstrip("/")
                        j += 1
                    else:
                        j += 1
                        continue
                    if _within_worktree(c_target):
                        continue
                    # Unanchored on the host side on purpose: a -C target that
                    # merely extends the host path (or the worktree path, e.g.
                    # <worktree>-evil) is still a host-side escape.
                    if c_target == host_str or c_target.startswith(host_str):
                        return (
                            True,
                            f"Blocked: git -C targeting host repository ({host_str})",
                        )
                # Host path anywhere in the git segment -- including env
                # assignments (GIT_DIR=<host>/.git git ...) and redirection
                # targets -- unless the token is a worktree path (which
                # contains the host path as a prefix by construction).
                for tok in seg:
                    if host_str in tok and worktree_str not in tok:
                        return (
                            True,
                            f"Blocked: git command references host repository path ({host_str})",
                        )
                continue

        return (False, None)

    try:
        stripped, force_legacy = _strip(command)
        if force_legacy:
            # Command substitution inside double quotes: bash executes it,
            # shlex-level tokenization would read it as data. Conservative
            # substring scan instead -- toward denial, never toward allow.
            return _legacy(command)
        lex = shlex.shlex(stripped, posix=True, punctuation_chars="();<>|&`")
        lex.whitespace_split = True
        # shlex's own comment handling truncates mid-token '#' (git
        # --format=%h#%s); comments are already stripped by _strip.
        lex.commenters = ""
        tokens = list(lex)
    except ValueError:
        # Untokenizable (e.g. unbalanced quotes): fall back to the substring
        # scan over the ORIGINAL command -- toward denial, never toward allow.
        return _legacy(command)

    return _check_segments(tokens)
