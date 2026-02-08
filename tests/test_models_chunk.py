"""Tests for chunk domain models and parsing functions."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/cli_decompose - Extract parse_status_filters to domain layer

import pytest

from models import ChunkStatus
from models.chunk import parse_status_filters


class TestParseStatusFilters:
    """Tests for parse_status_filters domain function."""

    def test_empty_input_returns_none(self):
        """No input returns None (no filtering)."""
        result, error = parse_status_filters((), False, False, False)
        assert result is None
        assert error is None

    def test_valid_status_string_single(self):
        """Single valid status string is parsed."""
        result, error = parse_status_filters(("FUTURE",), False, False, False)
        assert result == {ChunkStatus.FUTURE}
        assert error is None

    def test_valid_status_string_case_insensitive(self):
        """Status strings are case-insensitive."""
        result, error = parse_status_filters(("future",), False, False, False)
        assert result == {ChunkStatus.FUTURE}
        assert error is None

        result, error = parse_status_filters(("Future",), False, False, False)
        assert result == {ChunkStatus.FUTURE}
        assert error is None

    def test_valid_status_comma_separated(self):
        """Comma-separated status strings are parsed."""
        result, error = parse_status_filters(("FUTURE,ACTIVE",), False, False, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.ACTIVE}
        assert error is None

    def test_valid_status_multiple_options(self):
        """Multiple --status options are combined."""
        result, error = parse_status_filters(("FUTURE", "ACTIVE"), False, False, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.ACTIVE}
        assert error is None

    def test_future_flag(self):
        """--future flag adds FUTURE status."""
        result, error = parse_status_filters((), True, False, False)
        assert result == {ChunkStatus.FUTURE}
        assert error is None

    def test_active_flag(self):
        """--active flag adds ACTIVE status."""
        result, error = parse_status_filters((), False, True, False)
        assert result == {ChunkStatus.ACTIVE}
        assert error is None

    def test_implementing_flag(self):
        """--implementing flag adds IMPLEMENTING status."""
        result, error = parse_status_filters((), False, False, True)
        assert result == {ChunkStatus.IMPLEMENTING}
        assert error is None

    def test_multiple_flags_combined(self):
        """Multiple convenience flags are combined."""
        result, error = parse_status_filters((), True, True, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.ACTIVE}
        assert error is None

    def test_flags_and_status_option_combined(self):
        """Flags and --status option are combined."""
        result, error = parse_status_filters(("HISTORICAL",), True, False, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.HISTORICAL}
        assert error is None

    def test_invalid_status_string_returns_error(self):
        """Invalid status string returns error with valid options."""
        result, error = parse_status_filters(("INVALID",), False, False, False)
        assert result is None
        assert error is not None
        assert "Invalid status" in error
        assert "INVALID" in error
        # Should list valid statuses
        assert "FUTURE" in error
        assert "ACTIVE" in error

    def test_invalid_status_in_comma_list_returns_error(self):
        """Invalid status in comma-separated list returns error."""
        result, error = parse_status_filters(("FUTURE,INVALID",), False, False, False)
        assert result is None
        assert error is not None
        assert "INVALID" in error

    def test_whitespace_handling(self):
        """Whitespace around status values is trimmed."""
        result, error = parse_status_filters((" FUTURE , ACTIVE ",), False, False, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.ACTIVE}
        assert error is None

    def test_empty_string_parts_ignored(self):
        """Empty parts in comma-separated strings are ignored."""
        result, error = parse_status_filters(("FUTURE,,ACTIVE",), False, False, False)
        assert result == {ChunkStatus.FUTURE, ChunkStatus.ACTIVE}
        assert error is None

    def test_all_valid_statuses(self):
        """All ChunkStatus values are accepted."""
        for status in ChunkStatus:
            result, error = parse_status_filters((status.value,), False, False, False)
            assert result == {status}
            assert error is None

    def test_duplicate_statuses_deduplicated(self):
        """Duplicate statuses via different inputs are deduplicated."""
        result, error = parse_status_filters(("FUTURE", "FUTURE"), True, False, False)
        assert result == {ChunkStatus.FUTURE}
        assert error is None
