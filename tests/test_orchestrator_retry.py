# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Tests for extracted retry module
"""Tests for the orchestrator retry module.

These tests verify the is_retryable_api_error function correctly identifies
transient 5xx API errors that should be retried.
"""

import pytest

from orchestrator.retry import (
    is_retryable_api_error,
    _5XX_STATUS_PATTERN,
    _5XX_TEXT_PATTERNS,
)


class TestIsRetryableApiError:
    """Tests for the is_retryable_api_error helper function."""

    def test_500_errors(self):
        """Detects 500 Internal Server Error."""
        assert is_retryable_api_error("Error: 500 Internal Server Error")
        assert is_retryable_api_error("status code 500")
        assert is_retryable_api_error("HTTP/1.1 500")

    def test_502_errors(self):
        """Detects 502 Bad Gateway."""
        assert is_retryable_api_error("502 Bad Gateway")
        assert is_retryable_api_error("error: 502")

    def test_503_errors(self):
        """Detects 503 Service Unavailable."""
        assert is_retryable_api_error("503 Service Unavailable")
        assert is_retryable_api_error("service unavailable")

    def test_504_errors(self):
        """Detects 504 Gateway Timeout."""
        assert is_retryable_api_error("504 Gateway Timeout")
        assert is_retryable_api_error("gateway timeout")

    def test_529_errors(self):
        """Detects 529 Overloaded (Anthropic-specific)."""
        assert is_retryable_api_error("529 Overloaded")
        assert is_retryable_api_error("error code 529")

    def test_overloaded_text(self):
        """Detects 'overloaded' text patterns."""
        assert is_retryable_api_error("API is overloaded, please retry")
        assert is_retryable_api_error("Server overloaded")

    def test_api_error_text(self):
        """Detects 'api_error' text patterns."""
        assert is_retryable_api_error("api_error: server error")
        assert is_retryable_api_error("type: api_error")

    def test_rate_limit_text(self):
        """Detects 'rate_limit' text patterns."""
        assert is_retryable_api_error("rate_limit exceeded")
        assert is_retryable_api_error("rate_limit_error")

    def test_not_retryable_4xx(self):
        """Does not match 4xx client errors."""
        assert not is_retryable_api_error("400 Bad Request")
        assert not is_retryable_api_error("401 Unauthorized")
        assert not is_retryable_api_error("403 Forbidden")
        assert not is_retryable_api_error("404 Not Found")
        assert not is_retryable_api_error("429 Too Many Requests")  # 429 is not a 5xx

    def test_not_retryable_other_errors(self):
        """Does not match unrelated errors."""
        assert not is_retryable_api_error("FileNotFoundError: /path/to/file")
        assert not is_retryable_api_error("SyntaxError in code")
        assert not is_retryable_api_error("Permission denied")
        assert not is_retryable_api_error("Invalid argument")

    def test_empty_and_none(self):
        """Handles empty string and None gracefully."""
        assert not is_retryable_api_error("")
        assert not is_retryable_api_error(None)

    def test_case_insensitive(self):
        """Text pattern matching is case-insensitive."""
        assert is_retryable_api_error("INTERNAL SERVER ERROR")
        assert is_retryable_api_error("Bad Gateway")
        assert is_retryable_api_error("SERVICE UNAVAILABLE")
        assert is_retryable_api_error("Overloaded")


class TestPatternConstants:
    """Tests for the pattern constants."""

    def test_5xx_status_pattern_matches_5xx_codes(self):
        """The regex pattern matches 5xx status codes."""
        assert _5XX_STATUS_PATTERN.search("500")
        assert _5XX_STATUS_PATTERN.search("502")
        assert _5XX_STATUS_PATTERN.search("503")
        assert _5XX_STATUS_PATTERN.search("504")
        assert _5XX_STATUS_PATTERN.search("529")
        assert _5XX_STATUS_PATTERN.search("599")

    def test_5xx_status_pattern_not_matches_non_5xx(self):
        """The regex pattern does not match non-5xx codes."""
        assert not _5XX_STATUS_PATTERN.search("400")
        assert not _5XX_STATUS_PATTERN.search("200")
        assert not _5XX_STATUS_PATTERN.search("429")

    def test_5xx_text_patterns_coverage(self):
        """All expected text patterns are included."""
        assert "internal server error" in _5XX_TEXT_PATTERNS
        assert "bad gateway" in _5XX_TEXT_PATTERNS
        assert "service unavailable" in _5XX_TEXT_PATTERNS
        assert "gateway timeout" in _5XX_TEXT_PATTERNS
        assert "overloaded" in _5XX_TEXT_PATTERNS
        assert "api_error" in _5XX_TEXT_PATTERNS
        assert "rate_limit" in _5XX_TEXT_PATTERNS
        assert "529" in _5XX_TEXT_PATTERNS


# Chunk: docs/chunks/orch_session_auto_resume - Session limit error detection and retry
class TestIsSessionLimitError:
    """Tests for the is_session_limit_error detection function."""

    def test_detects_limit_with_simple_time(self):
        """Detects session limit errors with simple reset time."""
        from orchestrator.retry import is_session_limit_error

        assert is_session_limit_error("You've hit your limit - resets 10pm")

    def test_detects_limit_with_timezone(self):
        """Detects session limit errors with timezone in parentheses."""
        from orchestrator.retry import is_session_limit_error

        assert is_session_limit_error(
            "You've hit your limit - resets 10pm (America/New_York)"
        )
        assert is_session_limit_error(
            "You've hit your limit - resets 10:30pm (America/Los_Angeles)"
        )

    def test_detects_limit_with_iso_timestamp(self):
        """Detects session limit errors with full ISO timestamp."""
        from orchestrator.retry import is_session_limit_error

        assert is_session_limit_error(
            "You've hit your limit - resets 2024-02-07T22:00:00Z"
        )

    def test_detects_rate_limit_reset(self):
        """Detects rate limit reset patterns."""
        from orchestrator.retry import is_session_limit_error

        assert is_session_limit_error("Rate limit exceeded, resets at 10pm")
        assert is_session_limit_error("Session limit reached - resets 11:30pm")

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        from orchestrator.retry import is_session_limit_error

        assert is_session_limit_error("YOU'VE HIT YOUR LIMIT - resets 10pm")
        assert is_session_limit_error("you've hit your limit - RESETS 10PM")

    def test_no_reset_time_returns_false(self):
        """Session limit without reset time returns False."""
        from orchestrator.retry import is_session_limit_error

        # These should NOT match - no reset time provided
        assert not is_session_limit_error("You've hit your limit")
        assert not is_session_limit_error("Rate limit exceeded")
        assert not is_session_limit_error("Session limit reached - please try again later")

    def test_unrelated_errors_return_false(self):
        """Unrelated errors return False."""
        from orchestrator.retry import is_session_limit_error

        assert not is_session_limit_error("500 Internal Server Error")
        assert not is_session_limit_error("FileNotFoundError: /path/to/file")
        assert not is_session_limit_error("Connection timeout")
        assert not is_session_limit_error("Permission denied")

    def test_empty_and_none(self):
        """Handles empty string and None gracefully."""
        from orchestrator.retry import is_session_limit_error

        assert not is_session_limit_error("")
        assert not is_session_limit_error(None)


# Chunk: docs/chunks/orch_session_auto_resume - Reset time parsing
class TestParseResetTime:
    """Tests for the parse_reset_time function."""

    def test_parse_simple_pm_time(self):
        """Parse simple time like '10pm' (default to UTC)."""
        from datetime import datetime, timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time("You've hit your limit - resets 10pm")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 22
        assert result.minute == 0

    def test_parse_am_time(self):
        """Parse AM time like '10am'."""
        from datetime import timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time("You've hit your limit - resets 10am")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10
        assert result.minute == 0

    def test_parse_time_with_minutes(self):
        """Parse time with minutes like '10:30pm'."""
        from datetime import timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time("You've hit your limit - resets 10:30pm")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 22
        assert result.minute == 30

    def test_parse_timezone_america_new_york(self):
        """Parse time with America/New_York timezone and convert to UTC."""
        from datetime import timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time(
            "You've hit your limit - resets 10pm (America/New_York)"
        )
        assert result is not None
        assert result.tzinfo == timezone.utc
        # 10pm Eastern is 3am or 2am UTC depending on DST

    def test_parse_timezone_america_los_angeles(self):
        """Parse time with America/Los_Angeles timezone and convert to UTC."""
        from datetime import timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time(
            "You've hit your limit - resets 10:30pm (America/Los_Angeles)"
        )
        assert result is not None
        assert result.tzinfo == timezone.utc
        # Result should be converted from Pacific to UTC

    def test_parse_iso_timestamp(self):
        """Parse full ISO timestamp."""
        from datetime import datetime, timezone
        from orchestrator.retry import parse_reset_time

        result = parse_reset_time(
            "You've hit your limit - resets 2024-02-07T22:00:00Z"
        )
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 7
        assert result.hour == 22
        assert result.minute == 0

    def test_unparseable_returns_none(self):
        """Unparseable strings return None (not raise exceptions)."""
        from orchestrator.retry import parse_reset_time

        assert parse_reset_time("You've hit your limit") is None
        assert parse_reset_time("Random error message") is None
        assert parse_reset_time("") is None
        assert parse_reset_time(None) is None

    def test_future_time_assumption(self):
        """If parsed time is in the past, assume next occurrence (tomorrow)."""
        from datetime import datetime, timezone
        from orchestrator.retry import parse_reset_time

        # This test verifies the "next occurrence" behavior
        result = parse_reset_time("You've hit your limit - resets 11:59pm")
        assert result is not None
        # Should be in the future
        assert result >= datetime.now(timezone.utc)
