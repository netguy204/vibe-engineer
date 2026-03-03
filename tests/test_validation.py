"""Tests for validation utilities."""

import pytest

from validation import validate_identifier


class TestValidateIdentifierLength:
    """Tests for length validation in validate_identifier()."""

    def test_length_exceeds_max_error_message(self):
        """Verify error message format when length exceeds maximum."""
        # Use a 32-character string with max_length=31
        errors = validate_identifier("a" * 32, "test_field", max_length=31)

        assert len(errors) == 1
        assert errors[0] == "test_field must be at most 31 characters (got 32)"

    def test_length_exactly_at_max_is_valid(self):
        """Exactly max_length characters should be valid."""
        # Use a 31-character string with max_length=31
        errors = validate_identifier("a" * 31, "test_field", max_length=31)

        assert len(errors) == 0

    def test_length_below_max_is_valid(self):
        """Below max_length characters should be valid."""
        # Use a 30-character string with max_length=31
        errors = validate_identifier("a" * 30, "test_field", max_length=31)

        assert len(errors) == 0

    def test_no_max_length_allows_long_strings(self):
        """When max_length is None, any length is allowed."""
        errors = validate_identifier("a" * 100, "test_field", max_length=None)

        assert len(errors) == 0
