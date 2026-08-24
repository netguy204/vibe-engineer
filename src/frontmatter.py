"""Shared frontmatter I/O utilities.

# Chunk: docs/chunks/frontmatter_io - Shared frontmatter I/O utilities
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

This module provides common parsing and updating logic for YAML frontmatter
in markdown files. It consolidates duplicated implementations from chunks.py,
narratives.py, investigations.py, subsystems.py, friction.py, and
artifact_ordering.py into a unified interface.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError


# Type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)


# Regex pattern to extract YAML frontmatter from markdown files
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Regex pattern to split frontmatter from body (with trailing content)
_FRONTMATTER_WITH_BODY_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL
)

# Chunk: docs/chunks/hooks_lifecycle_fragments - Tolerates an empty `---\n---` block
# and a closing marker at EOF, neither of which _FRONTMATTER_WITH_BODY_PATTERN
# matches (it requires at least one line between the markers and a newline after
# the closing one). Anchoring the closing marker with MULTILINE ^ keeps a `---`
# horizontal rule mid-line from terminating the block.
_OPTIONAL_FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\n(.*?)^---[ \t]*(?:\n(.*))?\Z", re.DOTALL | re.MULTILINE
)


def parse_frontmatter(
    file_path: Path,
    model_class: type[T],
) -> T | None:
    """Parse YAML frontmatter from a markdown file and validate with Pydantic model.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.
        model_class: Pydantic model class to validate against.

    Returns:
        Validated model instance if successful, None if:
        - File doesn't exist
        - File has no frontmatter markers
        - YAML is invalid
        - Pydantic validation fails
    """
    result, _ = parse_frontmatter_with_errors(file_path, model_class)
    return result


def parse_frontmatter_with_errors(
    file_path: Path,
    model_class: type[T],
) -> tuple[T | None, list[str]]:
    """Parse YAML frontmatter with detailed error messages.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.
        model_class: Pydantic model class to validate against.

    Returns:
        Tuple of (model, errors) where:
        - model is the validated Pydantic model if successful, None otherwise
        - errors is a list of error messages (empty if parsing succeeded)
    """
    if not file_path.exists():
        return None, [f"File not found: {file_path}"]

    try:
        content = file_path.read_text()
    except (OSError, IOError) as e:
        return None, [f"Could not read file: {e}"]

    return parse_frontmatter_from_content_with_errors(content, model_class)


def parse_frontmatter_from_content(
    content: str,
    model_class: type[T],
) -> T | None:
    """Parse YAML frontmatter from a content string and validate with Pydantic model.

    Used for cache-based resolution where we have content but not a file path.

    Args:
        content: Full markdown content including frontmatter.
        model_class: Pydantic model class to validate against.

    Returns:
        Validated model instance if successful, None if:
        - Content has no frontmatter markers
        - YAML is invalid
        - Pydantic validation fails
    """
    result, _ = parse_frontmatter_from_content_with_errors(content, model_class)
    return result


def parse_frontmatter_from_content_with_errors(
    content: str,
    model_class: type[T],
) -> tuple[T | None, list[str]]:
    """Parse YAML frontmatter from content string with detailed error messages.

    Args:
        content: Full markdown content including frontmatter.
        model_class: Pydantic model class to validate against.

    Returns:
        Tuple of (model, errors) where:
        - model is the validated Pydantic model if successful, None otherwise
        - errors is a list of error messages (empty if parsing succeeded)
    """
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, ["File missing frontmatter (no --- markers found)"]

    try:
        frontmatter_data = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter_data, dict):
            return None, ["Frontmatter is not a valid YAML mapping"]
        return model_class.model_validate(frontmatter_data), []
    except yaml.YAMLError as e:
        return None, [f"YAML parsing error: {e}"]
    except ValidationError as e:
        # Extract user-friendly error messages from Pydantic validation
        errors = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        return None, errors


def extract_frontmatter_dict(file_path: Path) -> dict[str, Any] | None:
    """Extract raw frontmatter dict without Pydantic validation.

    Useful for generic field extraction where the schema isn't known.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.

    Returns:
        Parsed frontmatter dict, or None if file doesn't exist,
        has no frontmatter, or invalid YAML.
    """
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text()
    except (OSError, IOError):
        return None

    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return None

    try:
        result = yaml.safe_load(match.group(1))
        return result if isinstance(result, dict) else None
    except yaml.YAMLError:
        return None


# Chunk: docs/chunks/hooks_lifecycle_fragments - Optional-frontmatter splitting for hook fragments
def split_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
    """Split optional YAML frontmatter from a markdown body.

    Unlike the parse_frontmatter* family, absent frontmatter is not an error:
    the result is ({}, content). VE hook fragments are commonly bare prose,
    and requiring a --- block would be a trap for operators who have no
    reason to know YAML is involved.

    Malformed YAML, or frontmatter that parses to something other than a
    mapping, is likewise treated as absent: the raw text is preserved as the
    body rather than discarded. Callers embed this output in agent prompts,
    where losing the operator's words is worse than ignoring their syntax.

    Args:
        content: Full markdown content, with or without frontmatter.

    Returns:
        Tuple of (metadata, body). Never raises.
    """
    match = _OPTIONAL_FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content

    body = match.group(2) or ""

    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, content

    if metadata is None:
        # An empty --- --- block: no metadata, but the body still strips.
        return {}, body

    if not isinstance(metadata, dict):
        return {}, content

    return metadata, body


# Chunk: docs/chunks/future_chunk_creation - Reusable utility for modifying YAML frontmatter fields including status
def update_frontmatter_field(
    file_path: Path,
    field: str,
    value: Any,
) -> None:
    """Update a single field in a file's YAML frontmatter.

    Reads the file, updates the specified field in the frontmatter,
    and writes the file back with the body content preserved.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.
        field: The frontmatter field name to update.
        value: The new value for the field.

    Raises:
        FileNotFoundError: If file_path doesn't exist.
        ValueError: If the file has no frontmatter.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text()

    # Parse frontmatter between --- markers
    match = _FRONTMATTER_WITH_BODY_PATTERN.match(content)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {file_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Update the field
    frontmatter[field] = value

    # Reconstruct the file
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"

    file_path.write_text(new_content)
