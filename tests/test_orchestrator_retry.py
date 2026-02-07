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
