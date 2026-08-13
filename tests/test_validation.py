"""Tests for validation utilities."""

import pytest

from validation import MAX_PATH_COMPONENT_LENGTH, validate_identifier


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


# Chunk: docs/chunks/crossref_artifact_id_cap - Default cap is the filesystem limit
class TestDefaultLengthCap:
    """The default length cap is the filesystem path-component limit (255).

    Identifiers become directory names, so the real constraint is path
    legality — 255 bytes per component on APFS/ext4/NTFS, which equals 255
    characters for the ASCII identifier charset — not an arbitrary number.
    """

    def test_default_cap_is_path_component_limit(self):
        """The exported constant matches the filesystem path-component limit."""
        assert MAX_PATH_COMPONENT_LENGTH == 255

    def test_descriptive_name_beyond_31_chars_is_valid_by_default(self):
        """Ordinary descriptive names over 31 chars pass with the default cap."""
        errors = validate_identifier(
            "database_and_sagemaker_savings_plans", "test_field"
        )

        assert errors == []

    def test_length_at_path_component_limit_is_valid_by_default(self):
        """255 characters (the filesystem limit) passes with the default cap."""
        errors = validate_identifier("a" * 255, "test_field")

        assert errors == []

    def test_length_over_path_component_limit_is_rejected_by_default(self):
        """256 characters exceeds the filesystem limit and is rejected."""
        errors = validate_identifier("a" * 256, "test_field")

        assert len(errors) == 1
        assert errors[0] == "test_field must be at most 255 characters (got 256)"
