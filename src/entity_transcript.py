"""Parse Claude Code JSONL session transcripts into clean, structured data.

Provides extraction utilities for memory and episodic search pipelines.

# Chunk: docs/chunks/entity_transcript_extractor
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    """A single conversational turn (user prompt or assistant response)."""
    role: str           # "user" or "assistant"
    text: str           # cleaned text content
    timestamp: str      # ISO 8601
    uuid: str
    tool_uses: list[str] = field(default_factory=list)  # tool names used (assistant only)


@dataclass
class SessionTranscript:
    """Extracted transcript from a Claude Code session."""
    session_id: str
    turns: list[Turn]


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

# XML system tags to strip entirely (with their content)
_SYSTEM_TAGS = (
    "system-reminder",
    "command-message",
    "command-name",
    "command-args",
    "task-notification",
)
_TAG_PATTERN = re.compile(
    r"<(" + "|".join(re.escape(t) for t in _SYSTEM_TAGS) + r")>.*?</\1>",
    re.DOTALL,
)

# Claude Code temporary file paths
_FILE_PATH_PATTERN = re.compile(r"/private/tmp/claude-\d+/\S*")

# UUIDs (case-insensitive)
_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Strip noise from extracted transcript text.

    Removes XML system tags, Claude Code temp file paths, UUIDs, and collapses
    excessive whitespace.
    """
    # 1. Remove XML system tags and their content
    text = _TAG_PATTERN.sub("", text)

    # 2. Remove Claude Code injected temp file paths
    text = _FILE_PATH_PATTERN.sub("", text)

    # 3. Remove UUIDs
    text = _UUID_PATTERN.sub("", text)

    # 4. Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Collapse runs of spaces/tabs (but not newlines) to a single space
    text = re.sub(r"[ \t]+", " ", text)

    # 6. Strip leading/trailing whitespace from each line (clean up blank lines)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    # 7. Strip overall leading/trailing whitespace
    return text.strip()


# ---------------------------------------------------------------------------
# is_substantive_turn
# ---------------------------------------------------------------------------

def is_substantive_turn(turn: Turn) -> bool:
    """Return True if the turn has meaningful content (>= 20 chars after cleaning)."""
    cleaned = clean_text(turn.text).strip()
    return len(cleaned) >= 20


# ---------------------------------------------------------------------------
# parse_session_jsonl helpers
# ---------------------------------------------------------------------------

def _extract_text_from_message(message: dict) -> str:
    """Extract human-readable text from a Claude Code message object."""
    if not message:
        return ""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    parts.append(block.get("text", ""))
                # tool_use and tool_result are intentionally skipped
        return "\n".join(parts)
    return ""


def _get_tool_names(message: dict) -> list[str]:
    """Extract tool names used in a message."""
    if not message:
        return []
    content = message.get("content", [])
    if not isinstance(content, list):
        return []
    return [
        block.get("name", "unknown")
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]


# ---------------------------------------------------------------------------
# parse_session_jsonl
# ---------------------------------------------------------------------------

def parse_session_jsonl(jsonl_path: Path) -> SessionTranscript:
    """Parse a Claude Code session JSONL file into a SessionTranscript.

    - Merges assistant continuations (same requestId) into a single Turn.
    - Skips isMeta user messages and file-history-snapshot entries.
    - Applies clean_text to all extracted text.
    """
    session_id = jsonl_path.stem
    turns: list[Turn] = []

    # Accumulate state for the current assistant response group
    current_assistant_text: list[str] = []
    current_assistant_tools: list[str] = []
    current_assistant_ts: str | None = None
    current_assistant_uuid: str | None = None
    current_request_id: str | None = None

    def flush_assistant() -> None:
        nonlocal current_assistant_text, current_assistant_tools
        nonlocal current_assistant_ts, current_assistant_uuid, current_request_id
        if current_assistant_text or current_assistant_tools:
            text = clean_text("\n".join(current_assistant_text))
            turns.append(Turn(
                role="assistant",
                text=text,
                timestamp=current_assistant_ts or "",
                uuid=current_assistant_uuid or "",
                tool_uses=list(current_assistant_tools),
            ))
        current_assistant_text = []
        current_assistant_tools = []
        current_assistant_ts = None
        current_assistant_uuid = None
        current_request_id = None

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")

            if entry_type == "file-history-snapshot":
                continue

            if entry.get("isMeta"):
                continue

            if entry_type == "user":
                flush_assistant()
                message = entry.get("message", {})
                text = clean_text(_extract_text_from_message(message))
                if text.strip():
                    turns.append(Turn(
                        role="user",
                        text=text,
                        timestamp=entry.get("timestamp", ""),
                        uuid=entry.get("uuid", ""),
                    ))

            elif entry_type == "assistant":
                request_id = entry.get("requestId", "")
                if request_id != current_request_id:
                    flush_assistant()
                    current_request_id = request_id
                    current_assistant_ts = entry.get("timestamp", "")
                    current_assistant_uuid = entry.get("uuid", "")

                message = entry.get("message", {})
                text = _extract_text_from_message(message)
                tools = _get_tool_names(message)
                if text.strip():
                    current_assistant_text.append(text)
                if tools:
                    current_assistant_tools.extend(tools)

    flush_assistant()
    return SessionTranscript(session_id=session_id, turns=turns)


# ---------------------------------------------------------------------------
# resolve_session_jsonl_path
# ---------------------------------------------------------------------------

def resolve_session_jsonl_path(project_path: str, session_id: str) -> Path | None:
    """Find the JSONL file for a session.

    Checks two locations in order:
    1. Archived transcripts: <project_path>/.entities/<any>/sessions/<session_id>.jsonl
    2. Claude Code default:  ~/.claude/projects/<encoded>/<session_id>.jsonl

    The encoded path convention: "-" + absolute path with "/" replaced by "-".

    Returns the Path if found, None otherwise. Does NOT use sessions-index.json.
    """
    # 1. Check entity archive (preferred)
    project = Path(project_path)
    for match in project.glob(f".entities/*/sessions/{session_id}.jsonl"):
        return match

    # 2. Fall back to Claude Code's location
    encoded = "-" + project_path.strip("/").replace("/", "-")
    fallback = Path.home() / ".claude" / "projects" / encoded / f"{session_id}.jsonl"
    if fallback.exists():
        return fallback

    return None
