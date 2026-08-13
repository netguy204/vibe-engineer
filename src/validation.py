"""Shared validation utilities."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

import re

# Chunk: docs/chunks/crossref_artifact_id_cap - Cap identifiers at the real constraint
# Identifiers become directory names, so the binding constraint is path
# legality: every filesystem we target (APFS, ext4, NTFS) limits a path
# component to 255 bytes. The identifier charset is pure ASCII, so bytes ==
# characters and 255 characters is exactly the filesystem limit. If the
# charset is ever widened beyond ASCII, this equivalence breaks and the cap
# must be revisited in byte terms.
MAX_PATH_COMPONENT_LENGTH = 255


def validate_identifier(
    value: str,
    field_name: str,
    *,
    allow_dot: bool = False,
    max_length: int | None = MAX_PATH_COMPONENT_LENGTH,
) -> list[str]:
    """Validate an identifier for safe filesystem use.

    Args:
        value: The string to validate.
        field_name: Name of the field (for error messages).
        allow_dot: If True, dots are allowed in the identifier.
        max_length: Maximum allowed length (None for no limit). Defaults to
            the filesystem path-component limit; pass a smaller value only
            when a genuine external constraint applies (e.g. GitHub's org
            and repo name limits).

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if max_length is not None and len(value) > max_length:
        errors.append(
            f"{field_name} must be at most {max_length} characters "
            f"(got {len(value)})"
        )

    pattern = r"^[a-zA-Z0-9_.\-]+$" if allow_dot else r"^[a-zA-Z0-9_-]+$"
    if not re.match(pattern, value):
        invalid_chars = re.sub(r"[a-zA-Z0-9_.\-]" if allow_dot else r"[a-zA-Z0-9_-]", "", value)
        errors.append(f"{field_name} contains invalid characters: {invalid_chars!r}")

    return errors
