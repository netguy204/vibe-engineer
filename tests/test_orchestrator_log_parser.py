# Chunk: docs/chunks/orch_tail_command - Log parsing and tail command for orchestrator
"""Tests for the orchestrator log parser module.

Tests parsing of the raw log format and display formatting functions.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.log_parser import (
    ParsedLogEntry,
    ToolCall,
    ToolResult,
    TextContent,
    ResultInfo,
    parse_timestamp,
    parse_log_line,
    parse_log_file,
    format_timestamp,
    format_tool_call,
    format_tool_result,
    format_assistant_text,
    format_phase_header,
    format_result_banner,
    format_entry,
    format_entry_for_html,
    format_phase_header_for_html,
    format_result_banner_for_html,
)


class TestParseTimestamp:
    """Tests for timestamp parsing."""

    def test_parse_iso_timestamp(self):
        """Parses ISO format timestamp with timezone."""
        result = parse_timestamp("2026-01-31T19:30:56.669473+00:00")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 31
        assert result.hour == 19
        assert result.minute == 30
        assert result.second == 56

    def test_parse_timestamp_without_microseconds(self):
        """Parses timestamp without microseconds."""
        result = parse_timestamp("2026-01-31T19:30:56+00:00")
        assert result.hour == 19


class TestParseLogLine:
    """Tests for parsing individual log lines."""

    def test_parse_system_message(self):
        """Parses SystemMessage line."""
        line = "[2026-01-31T19:30:56.669473+00:00] SystemMessage(subtype='init', data={'type': 'system'})"
        result = parse_log_line(line)

        assert result is not None
        assert result.message_type == "SystemMessage"
        assert result.timestamp.hour == 19

    def test_parse_assistant_message_text_block(self):
        """Parses AssistantMessage with TextBlock."""
        line = "[2026-01-31T19:31:07.670490+00:00] AssistantMessage(content=[TextBlock(text='Now I understand the task.')])"
        result = parse_log_line(line)

        assert result is not None
        assert result.message_type == "AssistantMessage"
        assert "text_blocks" in result.content
        assert len(result.content["text_blocks"]) == 1
        assert result.content["text_blocks"][0].text == "Now I understand the task."

    def test_parse_assistant_message_tool_use_block(self):
        """Parses AssistantMessage with ToolUseBlock."""
        line = "[2026-01-31T19:31:00.138584+00:00] AssistantMessage(content=[ToolUseBlock(id='toolu_01UtHBmypBvy2ttkTqMZAqJx', name='Bash', input={'command': 'ls', 'description': 'List files'})])"
        result = parse_log_line(line)

        assert result is not None
        assert result.message_type == "AssistantMessage"
        assert "tool_calls" in result.content
        assert len(result.content["tool_calls"]) == 1
        tool_call = result.content["tool_calls"][0]
        assert tool_call.name == "Bash"
        assert tool_call.description == "List files"

    def test_parse_user_message_tool_result(self):
        """Parses UserMessage with ToolResultBlock."""
        line = "[2026-01-31T19:31:01.226200+00:00] UserMessage(content=[ToolResultBlock(tool_use_id='toolu_01UtHBmypBvy2ttkTqMZAqJx', content='file1.txt\\nfile2.txt', is_error=False)])"
        result = parse_log_line(line)

        assert result is not None
        assert result.message_type == "UserMessage"
        assert "tool_results" in result.content
        assert len(result.content["tool_results"]) == 1
        tool_result = result.content["tool_results"][0]
        assert tool_result.is_error is False

    def test_parse_user_message_tool_result_error(self):
        """Parses UserMessage with error result."""
        line = "[2026-01-31T19:31:01.226200+00:00] UserMessage(content=[ToolResultBlock(tool_use_id='toolu_01UtHBmypBvy2ttkTqMZAqJx', content='Command failed', is_error=True)])"
        result = parse_log_line(line)

        assert result is not None
        tool_result = result.content["tool_results"][0]
        assert tool_result.is_error is True

    def test_parse_result_message_success(self):
        """Parses successful ResultMessage."""
        line = "[2026-01-31T19:37:02.518279+00:00] ResultMessage(subtype='success', duration_ms=365854, duration_api_ms=318398, is_error=False, num_turns=40, session_id='49455da2', total_cost_usd=1.42, usage={}, result='Done')"
        result = parse_log_line(line)

        assert result is not None
        assert result.message_type == "ResultMessage"
        assert isinstance(result.content, ResultInfo)
        assert result.content.subtype == "success"
        assert result.content.duration_ms == 365854
        assert result.content.is_error is False
        assert result.content.num_turns == 40
        assert result.content.total_cost_usd == 1.42

    def test_parse_result_message_error(self):
        """Parses error ResultMessage."""
        line = "[2026-01-31T19:37:02.518279+00:00] ResultMessage(subtype='error', duration_ms=1000, duration_api_ms=500, is_error=True, num_turns=5, session_id='abc', total_cost_usd=0.10, usage={}, result='Error occurred')"
        result = parse_log_line(line)

        assert result is not None
        assert result.content.is_error is True

    def test_parse_malformed_line_returns_none(self):
        """Returns None for malformed lines."""
        assert parse_log_line("") is None
        assert parse_log_line("not a log line") is None
        assert parse_log_line("[bad timestamp] SomeMessage()") is None

    def test_parse_empty_line_returns_none(self):
        """Returns None for empty lines."""
        assert parse_log_line("") is None
        assert parse_log_line("   ") is None


class TestParseLogFile:
    """Tests for parsing entire log files."""

    def test_parse_log_file_basic(self, tmp_path):
        """Parses a simple log file."""
        log_file = tmp_path / "test.txt"
        log_file.write_text(
            "[2026-01-31T19:31:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
            "[2026-01-31T19:31:01.000000+00:00] AssistantMessage(content=[TextBlock(text='Hello')])\n"
        )

        entries = parse_log_file(log_file)
        assert len(entries) == 2
        assert entries[0].message_type == "SystemMessage"
        assert entries[1].message_type == "AssistantMessage"

    def test_parse_nonexistent_file(self, tmp_path):
        """Returns empty list for nonexistent file."""
        entries = parse_log_file(tmp_path / "nonexistent.txt")
        assert entries == []


class TestFormatTimestamp:
    """Tests for timestamp formatting."""

    def test_format_timestamp(self):
        """Formats datetime as HH:MM:SS."""
        dt = datetime(2026, 1, 31, 14, 30, 45)
        result = format_timestamp(dt)
        assert result == "14:30:45"


class TestFormatToolCall:
    """Tests for formatting tool calls."""

    def test_format_tool_call_with_description(self):
        """Formats tool call with description."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [],
                "tool_calls": [
                    ToolCall(
                        tool_id="tool1",
                        name="Bash",
                        input={},
                        description="Run tests",
                    )
                ],
            },
            raw_line="",
        )

        lines = format_tool_call(entry)
        assert len(lines) == 1
        assert "14:30:00 ▶ Bash: Run tests" == lines[0]

    def test_format_tool_call_without_description(self):
        """Formats tool call without description."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [],
                "tool_calls": [
                    ToolCall(tool_id="tool1", name="Glob", input={}, description=None)
                ],
            },
            raw_line="",
        )

        lines = format_tool_call(entry)
        assert len(lines) == 1
        assert "14:30:00 ▶ Glob" == lines[0]

    def test_format_tool_call_read_with_file_path(self):
        """Formats Read tool with file path."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [],
                "tool_calls": [
                    ToolCall(
                        tool_id="tool1",
                        name="Read",
                        input={"file_path": "/path/to/file.py"},
                        description=None,
                    )
                ],
            },
            raw_line="",
        )

        lines = format_tool_call(entry)
        assert len(lines) == 1
        assert "14:30:00 ▶ Read: file.py" == lines[0]

    def test_format_tool_call_wrong_message_type(self):
        """Returns empty for non-AssistantMessage."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="UserMessage",
            content={},
            raw_line="",
        )

        lines = format_tool_call(entry)
        assert lines == []


class TestFormatToolResult:
    """Tests for formatting tool results."""

    def test_format_tool_result_success(self):
        """Formats successful tool result."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="UserMessage",
            content={
                "tool_results": [
                    ToolResult(tool_use_id="tool1", content="Done", is_error=False)
                ]
            },
            raw_line="",
        )

        lines = format_tool_result(entry)
        assert len(lines) == 1
        assert "✓" in lines[0]
        assert "14:30:00" in lines[0]

    def test_format_tool_result_error(self):
        """Formats error tool result with error symbol."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="UserMessage",
            content={
                "tool_results": [
                    ToolResult(tool_use_id="tool1", content="Failed", is_error=True)
                ]
            },
            raw_line="",
        )

        lines = format_tool_result(entry)
        assert len(lines) == 1
        assert "✗" in lines[0]

    def test_format_tool_result_with_line_count(self):
        """Abbreviates multi-line content."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="UserMessage",
            content={
                "tool_results": [
                    ToolResult(
                        tool_use_id="tool1",
                        content="line1\nline2\nline3\nline4\nline5\nline6\nline7",
                        is_error=False,
                    )
                ]
            },
            raw_line="",
        )

        lines = format_tool_result(entry)
        assert len(lines) == 1
        assert "7 lines" in lines[0]

    def test_format_tool_result_test_output(self):
        """Recognizes and formats test output."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="UserMessage",
            content={
                "tool_results": [
                    ToolResult(
                        tool_use_id="tool1",
                        content="1960 passed, 4 skipped in 77s",
                        is_error=False,
                    )
                ]
            },
            raw_line="",
        )

        lines = format_tool_result(entry)
        assert len(lines) == 1
        assert "1960 passed" in lines[0]
        assert "4 skipped" in lines[0]


class TestFormatAssistantText:
    """Tests for formatting assistant text blocks."""

    def test_format_assistant_text_simple(self):
        """Formats simple text block."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text="Hello world")],
                "tool_calls": [],
            },
            raw_line="",
        )

        lines = format_assistant_text(entry, max_width=80)
        assert len(lines) == 1
        assert "💬" in lines[0]
        assert "Hello world" in lines[0]

    def test_format_assistant_text_word_wrap(self):
        """Word-wraps long text."""
        long_text = "This is a very long text that should be wrapped across multiple lines because it exceeds the maximum width"
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text=long_text)],
                "tool_calls": [],
            },
            raw_line="",
        )

        lines = format_assistant_text(entry, max_width=40)
        assert len(lines) > 1
        # First line has timestamp and emoji
        assert "💬" in lines[0]


class TestFormatPhaseHeader:
    """Tests for formatting phase headers."""

    def test_format_phase_header(self):
        """Formats phase header with start time."""
        dt = datetime(2026, 1, 31, 14, 30, 56)
        result = format_phase_header("IMPLEMENT", dt)

        assert "IMPLEMENT" in result
        assert "14:30:56" in result
        assert "===" in result


class TestFormatResultBanner:
    """Tests for formatting result banners."""

    def test_format_result_banner_success(self):
        """Formats successful result banner."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 37, 2),
            message_type="ResultMessage",
            content=ResultInfo(
                subtype="success",
                duration_ms=365854,
                total_cost_usd=1.42,
                num_turns=40,
                is_error=False,
            ),
            raw_line="",
        )

        result = format_result_banner(entry)
        assert "SUCCESS" in result
        assert "14:37:02" in result
        assert "$1.42" in result
        assert "40 turns" in result
        # Duration should be formatted as minutes/seconds
        assert "6m" in result or "365" in result

    def test_format_result_banner_error(self):
        """Formats error result banner."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 37, 2),
            message_type="ResultMessage",
            content=ResultInfo(
                subtype="error",
                duration_ms=1000,
                total_cost_usd=0.10,
                num_turns=5,
                is_error=True,
            ),
            raw_line="",
        )

        result = format_result_banner(entry)
        assert "ERROR" in result

    def test_format_result_banner_short_duration(self):
        """Formats short duration in seconds."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 37, 2),
            message_type="ResultMessage",
            content=ResultInfo(
                subtype="success",
                duration_ms=30000,
                total_cost_usd=0.50,
                num_turns=10,
                is_error=False,
            ),
            raw_line="",
        )

        result = format_result_banner(entry)
        assert "30s" in result


class TestFormatEntry:
    """Tests for the unified format_entry function."""

    def test_format_entry_skips_system_message(self):
        """Skips SystemMessage in output."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="SystemMessage",
            content={"raw": "init data"},
            raw_line="",
        )

        lines = format_entry(entry)
        assert lines == []

    def test_format_entry_assistant_message(self):
        """Formats AssistantMessage with tool calls and text."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text="Hello")],
                "tool_calls": [
                    ToolCall(tool_id="t1", name="Bash", input={}, description="Test")
                ],
            },
            raw_line="",
        )

        lines = format_entry(entry)
        assert len(lines) >= 2  # Tool call + text


class TestFormatEntryForHtml:
    """Tests for HTML-safe formatting functions."""

    def test_format_entry_for_html_escapes_html(self):
        """Escapes HTML special characters in formatted output."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text="Test <script>alert('xss')</script>")],
                "tool_calls": [],
            },
            raw_line="",
        )

        lines = format_entry_for_html(entry)
        # The output should be HTML-escaped
        for line in lines:
            assert "<script>" not in line
            assert "&lt;script&gt;" in line or "script" not in line

    def test_format_entry_for_html_preserves_symbols(self):
        """Preserves unicode symbols like ▶, ✓, ✗, 💬."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text="Hello")],
                "tool_calls": [],
            },
            raw_line="",
        )

        lines = format_entry_for_html(entry)
        # At least one line should contain the speech emoji
        joined = " ".join(lines)
        assert "💬" in joined

    def test_format_entry_for_html_tool_call_symbols(self):
        """Preserves ▶ symbol for tool calls."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [],
                "tool_calls": [
                    ToolCall(tool_id="t1", name="Bash", input={}, description="Test")
                ],
            },
            raw_line="",
        )

        lines = format_entry_for_html(entry)
        assert len(lines) >= 1
        assert "▶" in lines[0]

    def test_format_entry_for_html_escapes_ampersand(self):
        """Escapes ampersands in text."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [TextContent(text="foo & bar")],
                "tool_calls": [],
            },
            raw_line="",
        )

        lines = format_entry_for_html(entry)
        joined = " ".join(lines)
        assert "&amp;" in joined

    def test_format_phase_header_for_html(self):
        """Formats phase header for HTML display."""
        dt = datetime(2026, 1, 31, 14, 30, 56)
        result = format_phase_header_for_html("IMPLEMENT", dt)

        assert "IMPLEMENT" in result
        assert "14:30:56" in result
        assert "===" in result

    def test_format_phase_header_for_html_escapes_html(self):
        """Escapes HTML in phase header."""
        dt = datetime(2026, 1, 31, 14, 30, 56)
        # Phase names shouldn't contain HTML, but test escaping anyway
        result = format_phase_header_for_html("<script>", dt)

        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_format_result_banner_for_html_success(self):
        """Formats result banner for HTML display."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 37, 2),
            message_type="ResultMessage",
            content=ResultInfo(
                subtype="success",
                duration_ms=365854,
                total_cost_usd=1.42,
                num_turns=40,
                is_error=False,
            ),
            raw_line="",
        )

        result = format_result_banner_for_html(entry)
        assert "SUCCESS" in result
        assert "══" in result  # Unicode double lines preserved

    def test_format_result_banner_for_html_empty_for_non_result(self):
        """Returns empty string for non-ResultMessage."""
        entry = ParsedLogEntry(
            timestamp=datetime(2026, 1, 31, 14, 30, 0),
            message_type="AssistantMessage",
            content={
                "text_blocks": [],
                "tool_calls": [],
            },
            raw_line="",
        )

        result = format_result_banner_for_html(entry)
        assert result == ""
