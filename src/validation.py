"""Shared validation utilities."""
# Chunk: docs/chunks/implement_chunk_start - Shared validation

import re


# Chunk: docs/chunks/implement_chunk_start - Identifier validation
def validate_identifier(
    value: str,
    field_name: str,
    *,
    allow_dot: bool = False,
    max_length: int | None = 31,
) -> list[str]:
    """Validate an identifier for safe filesystem use.

    Args:
        value: The string to validate.
        field_name: Name of the field (for error messages).
        allow_dot: If True, dots are allowed in the identifier.
        max_length: Maximum allowed length (None for no limit).

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if max_length is not None and len(value) >= max_length + 1:
        errors.append(
            f"{field_name} must be less than {max_length + 1} characters "
            f"(got {len(value)})"
        )

    pattern = r"^[a-zA-Z0-9_.\-]+$" if allow_dot else r"^[a-zA-Z0-9_-]+$"
    if not re.match(pattern, value):
        invalid_chars = re.sub(r"[a-zA-Z0-9_.\-]" if allow_dot else r"[a-zA-Z0-9_-]", "", value)
        errors.append(f"{field_name} contains invalid characters: {invalid_chars!r}")

    return errors
