# Chunk: docs/chunks/backend_logparse - JSON-line log parser (replaces regex-based parser)
# Chunk: docs/chunks/orch_tail_command - Log parsing and tail command for orchestrator
"""Log parser for orchestrator agent logs.

Deserializes JSON-line log files written by :func:`create_log_callback` and
provides human-friendly display formatting. The parser is backend-agnostic:
it operates on the normalized :class:`LogEvent` shapes, so any backend that
emits those events produces identical summaries.
"""

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ParsedLogEntry:
    """A parsed log entry from an orchestrator log file.

    Attributes:
        timestamp: When the message was logged
        message_type: Type of message (AssistantMessage, UserMessage, ResultMessage, SystemMessage)
        content: Type-specific parsed content
        raw_line: The original log line (raw JSON string)
    """

    timestamp: datetime
    message_type: str
    content: Any
    raw_line: str


@dataclass
class ToolCall:
    """A parsed tool call from an AssistantMessage."""

    tool_id: str
    name: str
    input: dict
    description: Optional[str] = None


@dataclass
class ToolResult:
    """A parsed tool result from a UserMessage."""

    tool_use_id: str
    content: str
    is_error: bool


@dataclass
class TextContent:
    """Parsed text content from an AssistantMessage."""

    text: str


@dataclass
class ResultInfo:
    """Parsed ResultMessage information."""

    subtype: str  # 'success' or 'error'
    duration_ms: int
    total_cost_usd: float
    num_turns: int
    is_error: bool
    result_text: Optional[str] = None


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse an ISO format timestamp string.

    Args:
        timestamp_str: ISO format timestamp (e.g., '2026-01-31T19:30:56.669473+00:00')

    Returns:
        Parsed datetime object
    """
    return datetime.fromisoformat(timestamp_str)


def parse_log_line(line: str) -> Optional[ParsedLogEntry]:
    """Parse a single JSON log line into structured data.

    Args:
        line: A single JSON line from the log file

    Returns:
        ParsedLogEntry if successfully parsed, None otherwise
    """
    line = line.strip()
    if not line:
        return None

    try:
        record = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(record, dict):
        return None

    timestamp_str = record.get("timestamp")
    event_type = record.get("type")
    if not timestamp_str or not event_type:
        return None

    try:
        timestamp = parse_timestamp(timestamp_str)
    except ValueError:
        return None

    if event_type == "text":
        message_type = "AssistantMessage"
        content = {
            "text_blocks": [TextContent(text=record.get("text", ""))],
            "tool_calls": [],
        }

    elif event_type == "tool_call":
        message_type = "AssistantMessage"
        tool_input = record.get("input", {})
        description = record.get("description")
        content = {
            "text_blocks": [],
            "tool_calls": [
                ToolCall(
                    tool_id=record.get("tool_id", ""),
                    name=record.get("name", ""),
                    input=tool_input if isinstance(tool_input, dict) else {},
                    description=description,
                )
            ],
        }

    elif event_type == "tool_result":
        message_type = "UserMessage"
        content = {
            "tool_results": [
                ToolResult(
                    tool_use_id=record.get("tool_use_id", ""),
                    content=record.get("content", ""),
                    is_error=record.get("is_error", False),
                )
            ],
        }

    elif event_type == "result":
        message_type = "ResultMessage"
        content = ResultInfo(
            subtype=record.get("subtype", "success"),
            duration_ms=int(record.get("duration_ms", 0)),
            total_cost_usd=float(record.get("total_cost_usd", 0.0)),
            num_turns=int(record.get("num_turns", 0)),
            is_error=record.get("is_error", False),
            result_text=record.get("result_text"),
        )

    else:
        return None

    return ParsedLogEntry(
        timestamp=timestamp,
        message_type=message_type,
        content=content,
        raw_line=line,
    )


def parse_log_file(log_path: Path) -> list[ParsedLogEntry]:
    """Parse all entries from a log file.

    Args:
        log_path: Path to the log file

    Returns:
        List of parsed log entries
    """
    if not log_path.exists():
        return []

    entries = []
    with open(log_path) as f:
        for line in f:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)

    return entries


# ============================================================================
# Display Formatting
# ============================================================================


def format_timestamp(dt: datetime) -> str:
    """Format a datetime as HH:MM:SS.

    Args:
        dt: Datetime to format

    Returns:
        Formatted time string
    """
    return dt.strftime("%H:%M:%S")


def format_tool_call(entry: ParsedLogEntry) -> list[str]:
    """Format tool calls from an AssistantMessage for display.

    Args:
        entry: Parsed log entry containing tool calls

    Returns:
        List of formatted lines (one per tool call)
    """
    lines = []
    if entry.message_type != "AssistantMessage":
        return lines

    content = entry.content
    if not content or "tool_calls" not in content:
        return lines

    timestamp = format_timestamp(entry.timestamp)

    for tool_call in content["tool_calls"]:
        if tool_call.description:
            line = f"{timestamp} ▶ {tool_call.name}: {tool_call.description}"
        else:
            if tool_call.name == "Read" and "file_path" in tool_call.input:
                path = Path(tool_call.input["file_path"]).name
                line = f"{timestamp} ▶ {tool_call.name}: {path}"
            elif tool_call.name == "Write" and "file_path" in tool_call.input:
                path = Path(tool_call.input["file_path"]).name
                line = f"{timestamp} ▶ {tool_call.name}: {path}"
            else:
                line = f"{timestamp} ▶ {tool_call.name}"

        lines.append(line)

    return lines


def format_tool_result(entry: ParsedLogEntry) -> list[str]:
    """Format tool results from a UserMessage for display.

    Args:
        entry: Parsed log entry containing tool results

    Returns:
        List of formatted lines (one per result)
    """
    lines = []
    if entry.message_type != "UserMessage":
        return lines

    content = entry.content
    if not content or "tool_results" not in content:
        return lines

    timestamp = format_timestamp(entry.timestamp)

    for result in content["tool_results"]:
        symbol = "✗" if result.is_error else "✓"
        summary = _abbreviate_result(result.content)
        line = f"{timestamp} {symbol} {summary}"
        lines.append(line)

    return lines


def _abbreviate_result(content: str) -> str:
    """Create an abbreviated summary of tool result content.

    Args:
        content: The tool result content

    Returns:
        Abbreviated summary string
    """
    if not content:
        return "(empty)"

    lines = content.split("\n")
    line_count = len(lines)

    if "passed" in content.lower() and "skipped" in content.lower():
        match = re.search(r"(\d+)\s*passed.*?(\d+)\s*skipped", content, re.IGNORECASE)
        if match:
            return f"{match.group(1)} passed, {match.group(2)} skipped"

    if "Exit code" in content:
        match = re.search(r"Exit code\s*(\d+)", content)
        if match:
            code = int(match.group(1))
            if code == 0:
                return "Success"
            return f"Exit code {code}"

    if line_count > 5:
        return f"({line_count} lines)"

    if len(content) > 50:
        return content[:47] + "..."

    if line_count == 1:
        return content.strip()

    return f"({line_count} lines)"


def format_assistant_text(
    entry: ParsedLogEntry, max_width: int = 80, indent: str = "           "
) -> list[str]:
    """Format assistant TextBlocks with word-wrap.

    Args:
        entry: Parsed log entry containing text blocks
        max_width: Maximum line width
        indent: Indentation for continuation lines

    Returns:
        List of formatted lines
    """
    lines = []
    if entry.message_type != "AssistantMessage":
        return lines

    content = entry.content
    if not content or "text_blocks" not in content:
        return lines

    timestamp = format_timestamp(entry.timestamp)

    for text_block in content["text_blocks"]:
        text = text_block.text.strip()
        if not text:
            continue

        wrapped = _word_wrap(text, max_width - len(indent) - 3)

        if wrapped:
            first_line = f"{timestamp} 💬 {wrapped[0]}"
            lines.append(first_line)

            for cont_line in wrapped[1:]:
                lines.append(f"{indent}{cont_line}")

    return lines


def _word_wrap(text: str, max_width: int) -> list[str]:
    """Word-wrap text to specified width.

    Args:
        text: Text to wrap
        max_width: Maximum line width

    Returns:
        List of wrapped lines
    """
    if max_width <= 0:
        max_width = 80

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_len = len(word)
        if current_length + word_len + (1 if current_line else 0) <= max_width:
            current_line.append(word)
            current_length += word_len + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_len

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def format_phase_header(phase: str, start_time: datetime) -> str:
    """Format a phase transition header.

    Args:
        phase: Phase name (e.g., 'IMPLEMENT')
        start_time: When the phase started

    Returns:
        Formatted header string
    """
    time_str = format_timestamp(start_time)
    return f"=== {phase} phase === (started {time_str})"


def format_result_banner(entry: ParsedLogEntry) -> str:
    """Format ResultMessage as a summary banner.

    Args:
        entry: Parsed log entry with ResultInfo content

    Returns:
        Formatted banner string
    """
    if entry.message_type != "ResultMessage" or not entry.content:
        return ""

    result = entry.content
    if not isinstance(result, ResultInfo):
        return ""

    timestamp = format_timestamp(entry.timestamp)
    status = "ERROR" if result.is_error else "SUCCESS"

    duration_sec = result.duration_ms / 1000
    if duration_sec < 60:
        duration_str = f"{duration_sec:.0f}s"
    else:
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes}m {seconds}s"

    cost_str = f"${result.total_cost_usd:.2f}"

    return f"{timestamp} ══ {status} ══ {duration_str} | {cost_str} | {result.num_turns} turns"


def format_entry(entry: ParsedLogEntry, terminal_width: Optional[int] = None) -> list[str]:
    """Format a single log entry for display.

    Args:
        entry: The parsed log entry
        terminal_width: Terminal width for text wrapping

    Returns:
        List of formatted lines
    """
    if terminal_width is None:
        terminal_width = shutil.get_terminal_size().columns

    if entry.message_type == "SystemMessage":
        return []

    elif entry.message_type == "AssistantMessage":
        lines = []
        lines.extend(format_tool_call(entry))
        lines.extend(format_assistant_text(entry, max_width=terminal_width))
        return lines

    elif entry.message_type == "UserMessage":
        return format_tool_result(entry)

    elif entry.message_type == "ResultMessage":
        banner = format_result_banner(entry)
        return [banner] if banner else []

    return []


def format_log_entries(
    entries: list[ParsedLogEntry],
    terminal_width: Optional[int] = None,
) -> list[str]:
    """Format a list of log entries for display.

    Args:
        entries: List of parsed log entries
        terminal_width: Terminal width for text wrapping

    Returns:
        List of formatted lines
    """
    if terminal_width is None:
        terminal_width = shutil.get_terminal_size().columns

    lines = []
    for entry in entries:
        lines.extend(format_entry(entry, terminal_width))

    return lines


# ============================================================================
# HTML Formatting for Dashboard Display
# ============================================================================


def _escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Plain text to escape

    Returns:
        HTML-safe text
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def format_entry_for_html(entry: ParsedLogEntry, terminal_width: int = 100) -> list[str]:
    """Format a log entry as HTML-safe strings for dashboard display.

    Uses the same formatting logic as format_entry() but escapes HTML
    special characters and preserves the visual symbols (unicode characters
    don't need escaping).

    Args:
        entry: The parsed log entry
        terminal_width: Width for text wrapping (default 100 for dashboard)

    Returns:
        List of HTML-escaped formatted lines
    """
    plain_lines = format_entry(entry, terminal_width)
    return [_escape_html(line) for line in plain_lines]


def format_phase_header_for_html(phase: str, start_time: datetime) -> str:
    """Format a phase transition header for HTML display.

    Args:
        phase: Phase name (e.g., 'IMPLEMENT')
        start_time: When the phase started

    Returns:
        HTML-escaped header string
    """
    return _escape_html(format_phase_header(phase, start_time))


def format_result_banner_for_html(entry: ParsedLogEntry) -> str:
    """Format ResultMessage as a summary banner for HTML display.

    Args:
        entry: Parsed log entry with ResultInfo content

    Returns:
        HTML-escaped banner string
    """
    banner = format_result_banner(entry)
    return _escape_html(banner) if banner else ""
