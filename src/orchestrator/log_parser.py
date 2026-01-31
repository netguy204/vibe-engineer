# Chunk: docs/chunks/orch_tail_command - Log parsing and tail command for orchestrator
"""Log parser for orchestrator agent logs.

Parses the raw log format used by create_log_callback() and provides
human-friendly display formatting.
"""

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
        message_type: Type of message (SystemMessage, AssistantMessage, etc.)
        content: Type-specific parsed content
        raw_line: The original log line
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


# Regex patterns for parsing log lines
TIMESTAMP_PATTERN = re.compile(r"^\[([^\]]+)\]\s+(.+)$")
MESSAGE_TYPE_PATTERN = re.compile(r"^(\w+Message)\((.+)\)$", re.DOTALL)

# Patterns for extracting content from message bodies
TEXT_BLOCK_PATTERN = re.compile(r"TextBlock\(text='((?:[^'\\]|\\.)*)'\)")
TOOL_USE_PATTERN = re.compile(
    r"ToolUseBlock\(id='([^']+)',\s*name='([^']+)',\s*input=(\{[^}]*\})"
)
TOOL_RESULT_PATTERN = re.compile(
    r"ToolResultBlock\(tool_use_id='([^']+)',\s*content='((?:[^'\\]|\\.)*)',\s*is_error=(\w+)"
)
RESULT_MESSAGE_PATTERN = re.compile(
    r"subtype='(\w+)'.*?duration_ms=(\d+).*?is_error=(\w+).*?num_turns=(\d+).*?total_cost_usd=([0-9.]+)"
)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse an ISO format timestamp string.

    Args:
        timestamp_str: ISO format timestamp (e.g., '2026-01-31T19:30:56.669473+00:00')

    Returns:
        Parsed datetime object
    """
    # Handle timezone offset format
    return datetime.fromisoformat(timestamp_str)


def _unescape_string(s: str) -> str:
    """Unescape a Python string literal.

    Handles common escape sequences like \\n, \\t, \\', etc.
    """
    return s.encode("utf-8").decode("unicode_escape")


def _extract_description_from_input(input_str: str) -> Optional[str]:
    """Extract description field from tool input if present.

    Args:
        input_str: The tool input dict as a string

    Returns:
        Description string if found, None otherwise
    """
    # Look for 'description': '...' pattern
    match = re.search(r"['\"]description['\"]\s*:\s*['\"]([^'\"]+)['\"]", input_str)
    if match:
        return match.group(1)
    return None


def parse_log_line(line: str) -> Optional[ParsedLogEntry]:
    """Parse a single log line into structured data.

    Args:
        line: A single line from the log file

    Returns:
        ParsedLogEntry if successfully parsed, None otherwise
    """
    line = line.strip()
    if not line:
        return None

    # Extract timestamp and message body
    timestamp_match = TIMESTAMP_PATTERN.match(line)
    if not timestamp_match:
        return None

    timestamp_str = timestamp_match.group(1)
    message_body = timestamp_match.group(2)

    try:
        timestamp = parse_timestamp(timestamp_str)
    except ValueError:
        return None

    # Extract message type
    type_match = MESSAGE_TYPE_PATTERN.match(message_body)
    if not type_match:
        return None

    message_type = type_match.group(1)
    message_content = type_match.group(2)

    # Parse based on message type
    content: Any = None

    if message_type == "SystemMessage":
        # Just store raw content for system messages
        content = {"raw": message_content}

    elif message_type == "AssistantMessage":
        content = _parse_assistant_message(message_content)

    elif message_type == "UserMessage":
        content = _parse_user_message(message_content)

    elif message_type == "ResultMessage":
        content = _parse_result_message(message_content)

    return ParsedLogEntry(
        timestamp=timestamp,
        message_type=message_type,
        content=content,
        raw_line=line,
    )


def _parse_assistant_message(content: str) -> dict:
    """Parse AssistantMessage content.

    Returns dict with 'text_blocks' and 'tool_calls' lists.
    """
    result = {"text_blocks": [], "tool_calls": []}

    # Extract TextBlocks
    for match in TEXT_BLOCK_PATTERN.finditer(content):
        try:
            text = _unescape_string(match.group(1))
            result["text_blocks"].append(TextContent(text=text))
        except Exception:
            # If unescape fails, use raw text
            result["text_blocks"].append(TextContent(text=match.group(1)))

    # Extract ToolUseBlocks
    for match in TOOL_USE_PATTERN.finditer(content):
        tool_id = match.group(1)
        name = match.group(2)
        input_str = match.group(3)
        description = _extract_description_from_input(input_str)

        # Try to parse input as dict
        try:
            # Simple parsing - extract file_path if present
            input_dict: dict = {}
            file_path_match = re.search(r"['\"]file_path['\"]\s*:\s*['\"]([^'\"]+)['\"]", input_str)
            if file_path_match:
                input_dict["file_path"] = file_path_match.group(1)
            command_match = re.search(r"['\"]command['\"]\s*:\s*['\"]([^'\"]+)['\"]", input_str)
            if command_match:
                input_dict["command"] = command_match.group(1)
        except Exception:
            input_dict = {}

        result["tool_calls"].append(
            ToolCall(
                tool_id=tool_id,
                name=name,
                input=input_dict,
                description=description,
            )
        )

    return result


def _parse_user_message(content: str) -> dict:
    """Parse UserMessage content.

    Returns dict with 'tool_results' list.
    """
    result = {"tool_results": []}

    for match in TOOL_RESULT_PATTERN.finditer(content):
        tool_use_id = match.group(1)
        content_str = match.group(2)
        is_error = match.group(3).lower() == "true"

        try:
            content_str = _unescape_string(content_str)
        except Exception:
            pass

        result["tool_results"].append(
            ToolResult(
                tool_use_id=tool_use_id,
                content=content_str,
                is_error=is_error,
            )
        )

    return result


def _parse_result_message(content: str) -> Optional[ResultInfo]:
    """Parse ResultMessage content.

    Returns ResultInfo with summary information.
    """
    match = RESULT_MESSAGE_PATTERN.search(content)
    if not match:
        return None

    # Extract result text if present
    result_text = None
    result_match = re.search(r"result=['\"](.+?)['\"],?\s*structured_output", content, re.DOTALL)
    if result_match:
        try:
            result_text = _unescape_string(result_match.group(1))
        except Exception:
            result_text = result_match.group(1)

    return ResultInfo(
        subtype=match.group(1),
        duration_ms=int(match.group(2)),
        is_error=match.group(3).lower() == "true",
        num_turns=int(match.group(4)),
        total_cost_usd=float(match.group(5)),
        result_text=result_text,
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
        # Build display line
        if tool_call.description:
            line = f"{timestamp} ▶ {tool_call.name}: {tool_call.description}"
        else:
            # Extract useful info from input
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
        # Determine symbol based on error status
        symbol = "✗" if result.is_error else "✓"

        # Create abbreviated summary
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

    # Count lines
    lines = content.split("\n")
    line_count = len(lines)

    # Check for common patterns
    if "passed" in content.lower() and "skipped" in content.lower():
        # Test results
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

    # Short content - truncate if needed
    if len(content) > 50:
        return content[:47] + "..."

    # Single line result
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

        # Wrap text
        wrapped = _word_wrap(text, max_width - len(indent) - 3)

        # Format first line with timestamp and emoji
        if wrapped:
            first_line = f"{timestamp} 💬 {wrapped[0]}"
            lines.append(first_line)

            # Format continuation lines with indent
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

    # Format duration
    duration_sec = result.duration_ms / 1000
    if duration_sec < 60:
        duration_str = f"{duration_sec:.0f}s"
    else:
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes}m {seconds}s"

    # Format cost
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
        # Skip system messages in display
        return []

    elif entry.message_type == "AssistantMessage":
        lines = []
        # Tool calls first
        lines.extend(format_tool_call(entry))
        # Then text content
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
