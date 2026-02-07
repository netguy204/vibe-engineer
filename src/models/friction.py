"""Friction log domain models for tracking pain points."""
# Subsystem: docs/subsystems/friction_tracking - Friction log management
# Chunk: docs/chunks/models_subpackage - Friction module

import re
from typing import Literal

from pydantic import BaseModel, field_validator

from models.shared import SHA_PATTERN, _require_valid_repo_ref


class FrictionTheme(BaseModel):
    """A friction theme/category in the frontmatter.

    Themes emerge organically as friction is logged. Agents see existing
    themes when appending and cluster new entries accordingly.
    """

    id: str  # Short identifier like "code-refs"
    name: str  # Human-readable name like "Code Reference Friction"

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate id is non-empty."""
        if not v or not v.strip():
            raise ValueError("id cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v


class FrictionProposedChunk(BaseModel):
    """A proposed chunk that addresses friction entries.

    Similar to ProposedChunk but includes an addresses array linking to
    friction entry IDs for bidirectional traceability.
    """

    prompt: str
    chunk_directory: str | None = None  # Populated when chunk is created
    addresses: list[str] = []  # List of F-number IDs like ["F001", "F003"]

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        return v


# Chunk: docs/chunks/friction_chunk_linking - Regex pattern for validating friction entry ID format
# Regex for validating friction entry ID format: F followed by digits
FRICTION_ENTRY_ID_PATTERN = re.compile(r"^F\d+$")


# Chunk: docs/chunks/selective_artifact_friction - External friction source reference schema
class ExternalFrictionSource(BaseModel):
    """Reference to friction entries in an external repository.

    Used in project FRICTION.md frontmatter to track friction entries that
    originated from external artifact repositories in task contexts.
    """

    repo: str  # External repo ref in org/repo format (e.g., "acme/ext")
    track: str = "main"  # Branch to track
    pinned: str  # Commit SHA when reference was created
    entry_ids: list[str] = []  # List of F-numbers in that repo this project cares about

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repo is in org/repo format."""
        return _require_valid_repo_ref(v, "repo")

    @field_validator("pinned")
    @classmethod
    def validate_pinned(cls, v: str) -> str:
        """Validate pinned is a 40-character hex SHA."""
        if not SHA_PATTERN.match(v):
            raise ValueError("pinned must be a 40-character lowercase hex SHA")
        return v

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, v: list[str]) -> list[str]:
        """Validate entry_ids are valid friction entry IDs."""
        for entry_id in v:
            if not FRICTION_ENTRY_ID_PATTERN.match(entry_id):
                raise ValueError(
                    f"entry_id '{entry_id}' must match pattern F followed by digits (e.g., F001, F123)"
                )
        return v


# Chunk: docs/chunks/selective_artifact_friction - Friction log frontmatter schema
class FrictionFrontmatter(BaseModel):
    """Frontmatter schema for FRICTION.md files.

    Validates the YAML frontmatter in friction log documentation.
    """

    themes: list[FrictionTheme] = []
    proposed_chunks: list[FrictionProposedChunk] = []
    external_friction_sources: list[ExternalFrictionSource] = []


# Chunk: docs/chunks/friction_chunk_linking - Pydantic model for friction entry reference with entry_id and scope fields
class FrictionEntryReference(BaseModel):
    """Reference to a friction entry that a chunk addresses.

    Used in chunk frontmatter to link chunks to the friction entries they resolve.
    Provides "why did we do this work?" traceability from implementation back to
    accumulated pain points.
    """

    entry_id: str  # e.g., "F001"
    scope: Literal["full", "partial"] = "full"

    @field_validator("entry_id")
    @classmethod
    def validate_entry_id(cls, v: str) -> str:
        """Validate entry_id matches the friction entry ID pattern (F followed by digits)."""
        if not v:
            raise ValueError("entry_id cannot be empty")
        if not FRICTION_ENTRY_ID_PATTERN.match(v):
            raise ValueError(
                "entry_id must match pattern F followed by digits (e.g., F001, F123)"
            )
        return v
