"""Shared reference types used across multiple artifact frontmatter schemas."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/models_subpackage - References module

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator

from models.shared import _require_valid_dir_name, _require_valid_repo_ref


# Chunk: docs/chunks/artifact_ordering_index - Enum defining workflow artifact types
# Chunk: docs/chunks/consolidate_ext_refs - Moved ArtifactType enum from artifact_ordering.py to models.py
class ArtifactType(StrEnum):
    """Types of workflow artifacts that can be ordered."""

    CHUNK = "chunk"
    NARRATIVE = "narrative"
    INVESTIGATION = "investigation"
    SUBSYSTEM = "subsystem"


# Chunk: docs/chunks/remove_legacy_prefix - Simplified patterns accepting only {short_name} format
# Regex for validating artifact ID format: {short_name}
# Lowercase letters, digits, underscores, hyphens (must start with letter)
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")

# Same as ARTIFACT_ID_PATTERN - kept for backward compatibility in existing code
CHUNK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


# Chunk: docs/chunks/artifact_pattern_consolidation - Unified artifact ID validation helper
def _validate_artifact_id(v: str, field_name: str = "artifact_id") -> str:
    """Validate that a value matches the artifact ID pattern.

    Args:
        v: The value to validate.
        field_name: The name of the field for error messages.

    Returns:
        The validated value.

    Raises:
        ValueError: If the value is empty or doesn't match the pattern.
    """
    if not v:
        raise ValueError(f"{field_name} cannot be empty")
    if not ARTIFACT_ID_PATTERN.match(v):
        raise ValueError(
            f"{field_name} must be lowercase, start with a letter, and contain only "
            "letters, digits, underscores, and hyphens"
        )
    return v


# Chunk: docs/chunks/artifact_pattern_consolidation - Generic artifact relationship model
class ArtifactRelationship(BaseModel):
    """Generic relationship between workflow artifacts.

    A unified model for expressing relationships between artifacts. This replaces
    type-specific models (ChunkRelationship, SubsystemRelationship) with a single
    model parameterized by artifact type.

    Relationship types:
    - "implements": The artifact directly implements part of the related artifact
    - "uses": The artifact uses/depends on the related artifact

    Examples:
        # Chunk implements a subsystem
        ArtifactRelationship(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="template_system",
            relationship="implements"
        )

        # Subsystem references a chunk
        ArtifactRelationship(
            artifact_type=ArtifactType.CHUNK,
            artifact_id="template_rendering",
            relationship="implements"
        )
    """

    artifact_type: ArtifactType
    artifact_id: str  # format: {short_name}
    relationship: Literal["implements", "uses"]

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, v: str) -> str:
        """Validate artifact_id matches valid artifact ID pattern."""
        return _validate_artifact_id(v, "artifact_id")

    def to_chunk_relationship(self) -> "ChunkRelationship":
        """Convert to ChunkRelationship (for backward compatibility).

        Only valid when artifact_type is CHUNK.

        Raises:
            ValueError: If artifact_type is not CHUNK.
        """
        if self.artifact_type != ArtifactType.CHUNK:
            raise ValueError(
                f"Cannot convert {self.artifact_type} relationship to ChunkRelationship"
            )
        return ChunkRelationship(
            chunk_id=self.artifact_id,
            relationship=self.relationship,
        )

    def to_subsystem_relationship(self) -> "SubsystemRelationship":
        """Convert to SubsystemRelationship (for backward compatibility).

        Only valid when artifact_type is SUBSYSTEM.

        Raises:
            ValueError: If artifact_type is not SUBSYSTEM.
        """
        if self.artifact_type != ArtifactType.SUBSYSTEM:
            raise ValueError(
                f"Cannot convert {self.artifact_type} relationship to SubsystemRelationship"
            )
        return SubsystemRelationship(
            subsystem_id=self.artifact_id,
            relationship=self.relationship,
        )

    @classmethod
    def from_chunk_relationship(cls, rel: "ChunkRelationship") -> "ArtifactRelationship":
        """Create from ChunkRelationship (for backward compatibility)."""
        return cls(
            artifact_type=ArtifactType.CHUNK,
            artifact_id=rel.chunk_id,
            relationship=rel.relationship,
        )

    @classmethod
    def from_subsystem_relationship(
        cls, rel: "SubsystemRelationship"
    ) -> "ArtifactRelationship":
        """Create from SubsystemRelationship (for backward compatibility)."""
        return cls(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id=rel.subsystem_id,
            relationship=rel.relationship,
        )


# Chunk: docs/chunks/subsystem_schemas_and_model - Model for chunk-to-subsystem relationships
# Chunk: docs/chunks/remove_legacy_prefix - Validation without legacy format branches
class ChunkRelationship(BaseModel):
    """Relationship between a subsystem and a chunk.

    Captures how chunks relate to subsystem documentation:
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem

    Note: Consider using ArtifactRelationship for new code. This class is retained
    for backward compatibility with existing subsystem YAML files.
    """

    chunk_id: str  # format: {short_name}
    relationship: Literal["implements", "uses"]

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
        """Validate chunk_id matches valid artifact ID pattern."""
        return _validate_artifact_id(v, "chunk_id")


# Chunk: docs/chunks/bidirectional_refs - Pydantic model for chunk-to-subsystem relationship
# Chunk: docs/chunks/remove_legacy_prefix - Validation without legacy format branches
class SubsystemRelationship(BaseModel):
    """Relationship between a chunk and a subsystem.

    Captures how a chunk relates to subsystem documentation (inverse of ChunkRelationship):
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem

    Note: Consider using ArtifactRelationship for new code. This class is retained
    for backward compatibility with existing chunk YAML files.
    """

    subsystem_id: str  # format: {short_name}
    relationship: Literal["implements", "uses"]

    @field_validator("subsystem_id")
    @classmethod
    def validate_subsystem_id(cls, v: str) -> str:
        """Validate subsystem_id matches valid artifact ID pattern."""
        return _validate_artifact_id(v, "subsystem_id")


class ComplianceLevel(StrEnum):
    """Compliance level for code references in subsystem documentation.

    Indicates how well referenced code follows the subsystem's patterns.
    """

    COMPLIANT = "COMPLIANT"  # Fully follows the subsystem's patterns
    PARTIAL = "PARTIAL"  # Partially follows but has some deviations
    NON_COMPLIANT = "NON_COMPLIANT"  # Does not follow the patterns


# Chunk: docs/chunks/chunk_validate - Pydantic model for symbolic code references with validation
# Chunk: docs/chunks/coderef_format_prompting - Improved org/repo format error messages
class SymbolicReference(BaseModel):
    """A symbolic reference to code that implements a requirement.

    Format: {file_path}, {file_path}#{symbol_path}, or {org/repo::file_path}#{symbol_path}

    Examples:
        - src/chunks.py (entire module)
        - src/chunks.py#Chunks (class)
        - src/chunks.py#Chunks::create_chunk (method)
        - src/ve.py#validate_short_name (standalone function)
        - acme/project::src/foo.py#Bar (class in another project)

    For subsystem documentation, the optional compliance field indicates how well
    the referenced code follows the subsystem's patterns:
        - COMPLIANT: Fully follows the subsystem's patterns (canonical implementation)
        - PARTIAL: Partially follows but has some deviations
        - NON_COMPLIANT: Does not follow the patterns (deviation to be addressed)
    """

    ref: str  # format: {file_path}, {file_path}#{symbol_path}, or {org/repo::...}
    implements: str  # description of what this reference implements
    compliance: ComplianceLevel | None = None  # optional, used in subsystem docs

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, v: str) -> str:
        """Validate ref field format.

        Supports both local references and project-qualified references:
        - Local: file_path or file_path#symbol_path
        - Qualified: org/repo::file_path or org/repo::file_path#symbol_path
        """
        if not v:
            raise ValueError("ref cannot be empty")

        if v.startswith("#"):
            raise ValueError("ref must start with a file path, not #")

        if v.count("#") > 1:
            raise ValueError("ref cannot contain multiple # characters")

        # Check for project qualifier (:: must come before # if present)
        hash_pos = v.find("#")
        if hash_pos == -1:
            ref_before_symbol = v
        else:
            ref_before_symbol = v[:hash_pos]

        # Check for :: in the portion before #
        double_colon_pos = ref_before_symbol.find("::")
        if double_colon_pos != -1:
            project = ref_before_symbol[:double_colon_pos]
            file_path_part = ref_before_symbol[double_colon_pos + 2:]

            # Validate that there's no second :: before #
            if "::" in file_path_part:
                raise ValueError("ref cannot have multiple :: delimiters before #")

            # Validate project qualifier is not empty
            if not project:
                raise ValueError("project qualifier cannot be empty before ::")

            # Validate project is in org/repo format using existing validator
            # Wrap with contextual error message that includes the invalid value
            try:
                _require_valid_repo_ref(project, "project qualifier")
            except ValueError:
                raise ValueError(
                    f"project qualifier must be in 'org/repo' format "
                    f"(e.g., 'acme/project::path'), got '{project}'"
                )

            # Check that file path portion is not empty
            if not file_path_part:
                raise ValueError("file path cannot be empty after ::")
        else:
            # No project qualifier, ref_before_symbol is the file path
            file_path_part = ref_before_symbol

        if "#" in v:
            symbol_path = v.split("#", 1)[1]
            if not symbol_path:
                raise ValueError("symbol path cannot be empty after #")

            # Check for empty components in symbol path
            parts = symbol_path.split("::")
            for part in parts:
                if not part:
                    raise ValueError("symbol path cannot have empty component between ::")

        return v

    @field_validator("implements")
    @classmethod
    def validate_implements(cls, v: str) -> str:
        """Validate implements field is non-empty."""
        if not v or not v.strip():
            raise ValueError("implements cannot be empty")
        return v


class CodeRange(BaseModel):
    """A range of lines in a file that implements a specific requirement."""

    lines: str  # "N-M" or "N" format
    implements: str


class CodeReference(BaseModel):
    """A file with code ranges that implement requirements."""

    file: str
    ranges: list[CodeRange]


# Chunk: docs/chunks/consolidate_ext_refs - Generic external artifact reference model with artifact_type and artifact_id fields
class ExternalArtifactRef(BaseModel):
    """Reference to a workflow artifact in another repository.

    Used for external.yaml files that reference artifacts (chunks, narratives,
    investigations, subsystems) in an external repository. This is a type-agnostic
    replacement for ExternalChunkRef that supports all workflow artifact types.
    """

    artifact_type: ArtifactType
    artifact_id: str  # Short name of the referenced artifact
    repo: str  # GitHub-style org/repo format
    track: str | None = None  # Branch to follow (optional)
    pinned: str | None = None  # 40-char SHA (optional)
    created_after: list[str] = []  # Local causal ordering

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repo is in org/repo format."""
        return _require_valid_repo_ref(v, "repo")

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, v: str) -> str:
        """Validate artifact_id is a valid directory name."""
        return _require_valid_dir_name(v, "artifact_id")

    # Note: The `pinned` field is optional and ignored. It remains in the model
    # for backward compatibility with existing external.yaml files that may still
    # have it. External references now always resolve to HEAD (see DEC-002).


class ProposedChunk(BaseModel):
    """A proposed chunk entry used across narratives, subsystems, and investigations.

    Represents a chunk that has been proposed but may or may not have been created yet.
    When chunk_directory is None or empty, the chunk has not yet been created.

    The depends_on field stores indices of other proposed chunks in the same array
    that this chunk depends on. These are 0-based indices referencing sibling prompts.
    When the chunk is created, index-based dependencies are resolved to chunk directory
    names by looking up proposed_chunks[index].chunk_directory.
    """

    prompt: str  # The chunk prompt text
    chunk_directory: str | None = None  # Populated when chunk is created
    depends_on: list[int] = []  # Indices of sibling proposed chunks this depends on

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        return v

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[int]) -> list[int]:
        """Validate depends_on indices are non-negative."""
        for idx in v:
            if idx < 0:
                raise ValueError(f"depends_on indices must be non-negative, got {idx}")
        return v
