# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Extracted from scheduler.py for single-responsibility
"""Retryable API error detection.

This module provides pattern matching for detecting 5xx API errors that are
likely transient and worth retrying. Extracted from scheduler.py to keep
the scheduler focused on dispatch logic.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

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


# Chunk: docs/chunks/orch_session_auto_resume - Session limit error detection
# Regex patterns for detecting session limit errors with reset times
# Match patterns like:
# - "you've hit your limit - resets 10pm"
# - "rate limit exceeded, resets at 10pm"
# - "session limit reached - resets 10:30pm (America/New_York)"
_SESSION_LIMIT_PATTERNS = [
    r"you'?ve hit your limit",
    r"rate limit (?:exceeded|reached|hit)",
    r"session limit (?:exceeded|reached|hit)",
]

# Time patterns to look for after "resets"
# Matches: 10pm, 10:30pm, 10:30am, 2024-02-07T22:00:00Z
_RESET_TIME_PATTERN = re.compile(
    r"resets?\s+(?:at\s+)?("
    r"(\d{1,2})(:\d{2})?\s*(am|pm)"  # Simple time: 10pm, 10:30pm
    r"|(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"  # ISO format
    r")"
    r"(?:\s*\(([^)]+)\))?",  # Optional timezone in parens: (America/New_York)
    re.IGNORECASE,
)


def is_session_limit_error(error: str) -> bool:
    """Check if an error string indicates a session limit with a parseable reset time.

    Looks for patterns indicating session/rate limits that include a reset time.
    Only returns True if the error contains both:
    1. A session/rate limit indicator (e.g., "you've hit your limit")
    2. A parseable reset time (e.g., "resets 10pm")

    This is distinct from `is_retryable_api_error` which handles 5xx errors.
    Session limit errors get scheduled for retry at the reset time instead
    of using exponential backoff.

    Args:
        error: The error string from the agent result

    Returns:
        True if the error is a session limit with parseable reset time
    """
    if not error:
        return False

    error_lower = error.lower()

    # Check for session limit patterns
    has_limit_pattern = False
    for pattern in _SESSION_LIMIT_PATTERNS:
        if re.search(pattern, error_lower):
            has_limit_pattern = True
            break

    if not has_limit_pattern:
        return False

    # Check for reset time pattern
    match = _RESET_TIME_PATTERN.search(error)
    return match is not None


def parse_reset_time(error: str) -> Optional[datetime]:
    """Extract and parse reset time from an error string.

    Extracts reset time patterns and converts to a UTC datetime. Handles:
    - Simple times: "10pm", "10:30am" (assumes UTC)
    - Times with timezone: "10pm (America/New_York)"
    - ISO format: "2024-02-07T22:00:00Z"

    If the parsed time is in the past, assumes the next occurrence (tomorrow).

    Args:
        error: The error string containing a reset time

    Returns:
        UTC datetime of the reset time, or None if parsing fails
    """
    if not error:
        return None

    match = _RESET_TIME_PATTERN.search(error)
    if not match:
        return None

    full_match = match.group(1)
    iso_match = match.group(5)
    tz_name = match.group(6)  # Optional timezone like "America/New_York"

    try:
        if iso_match:
            # ISO format: 2024-02-07T22:00:00Z
            return datetime.fromisoformat(iso_match.replace("Z", "+00:00"))

        # Simple time format: 10pm, 10:30pm
        hour_str = match.group(2)
        minute_str = match.group(3)  # Could be None or ":30"
        am_pm = match.group(4).lower()

        hour = int(hour_str)
        minute = int(minute_str[1:]) if minute_str else 0

        # Convert 12-hour to 24-hour
        if am_pm == "pm" and hour != 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0

        # Determine timezone
        if tz_name:
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = timezone.utc
        else:
            tz = timezone.utc

        # Create datetime for today with the parsed time
        now = datetime.now(tz)
        reset_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time is in the past, assume tomorrow
        if reset_time <= now:
            reset_time += timedelta(days=1)

        # Convert to UTC
        return reset_time.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None
