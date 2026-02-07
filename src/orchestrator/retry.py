# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Extracted from scheduler.py for single-responsibility
"""Retryable API error detection.

This module provides pattern matching for detecting 5xx API errors that are
likely transient and worth retrying. Extracted from scheduler.py to keep
the scheduler focused on dispatch logic.
"""

import re

# Chunk: docs/chunks/orch_api_retry - Pattern matching for retryable API errors
# Regex patterns for detecting 5xx API errors in error strings
_5XX_STATUS_PATTERN = re.compile(r"\b5[0-9]{2}\b")  # 500, 502, 503, etc.
_5XX_TEXT_PATTERNS = [
    "internal server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "overloaded",
    "api_error",  # Anthropic API error type
    "rate_limit",  # Often a temporary condition
    "529",  # Anthropic overloaded status
]


def is_retryable_api_error(error: str) -> bool:
    """Check if an error string indicates a retryable 5xx API error.

    Looks for patterns indicating server-side errors that are likely
    transient and worth retrying:
    - HTTP 5xx status codes (500, 502, 503, 504, 529)
    - Error messages like "Internal Server Error", "overloaded", etc.

    Does NOT retry on client errors (4xx) or other non-transient failures.

    Args:
        error: The error string from the agent result

    Returns:
        True if the error appears to be a retryable 5xx API error
    """
    if not error:
        return False

    error_lower = error.lower()

    # Check for 5xx status codes in the error
    if _5XX_STATUS_PATTERN.search(error):
        return True

    # Check for common 5xx error text patterns
    for pattern in _5XX_TEXT_PATTERNS:
        if pattern in error_lower:
            return True

    return False
