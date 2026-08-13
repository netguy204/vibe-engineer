"""Shared reference types used across multiple artifact frontmatter schemas."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/models_subpackage - References module

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from models.shared import (
    _require_valid_dir_name,
    _require_valid_repo_ref,
    classify_qualifier_shape,
)

# Chunk: docs/chunks/federation_peer_refs - Member names in external.yaml obey the manifest grammar
# `models.workspace` depends on nothing in `models`, so importing it here keeps
# the package's internal imports acyclic while ensuring a `tree:` target in an
# external.yaml is held to exactly the grammar `.ve-workspace.yaml` enforces.
from models.workspace import validate_member_name


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

    Format: {file_path}, {file_path}#{symbol_path}, or a qualified form
    {qualifier}::{file_path}#{symbol_path} where the qualifier is either a
    workspace member name (no '/') or a GitHub-style org/repo (exactly one
    '/'). The qualifier shape rule is shared with the comment backreference
    grammar (`models.shared.classify_qualifier_shape`).

    # Chunk: docs/chunks/federation_member_refs - Member-qualified frontmatter refs

    Examples:
        - src/chunks.py (entire module)
        - src/chunks.py#Chunks (class)
        - src/chunks.py#Chunks::create_chunk (method)
        - src/ve.py#validate_short_name (standalone function)
        - engine::src/foo.py#Bar (class in a sibling tree of this workspace)
        - acme/project::src/foo.py#Bar (class in another repository)

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

        Supports local and qualified references:
        - Local: file_path or file_path#symbol_path
        - Member-qualified: member::file_path[#symbol_path] (same workspace)
        - Repo-qualified: org/repo::file_path[#symbol_path] (another repository)
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

            # Chunk: docs/chunks/federation_member_refs - Member qualifiers are valid frontmatter refs
            # The shape rule is shared with the comment grammar: a member name
            # (no '/') or an org/repo reference (exactly one '/').
            kind, reason = classify_qualifier_shape(project)
            if kind == "invalid":
                raise ValueError(
                    f"project qualifier must be a workspace member name "
                    f"(e.g., 'engine::path') or in 'org/repo' format "
                    f"(e.g., 'acme/project::path'), got '{project}': {reason}"
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
# Chunk: docs/chunks/federation_peer_refs - Peer (tree) targets and interest notes
class ExternalArtifactRef(BaseModel):
    """Reference to a workflow artifact that lives outside this artifact directory.

    Used for external.yaml files that reference artifacts (chunks, narratives,
    investigations, subsystems) owned elsewhere. Two flavors of target exist, and
    exactly one must be given:

    - `repo: <org>/<repo>` — a *cross-repository* reference. Resolution goes
      through the repo cache and a `track`, because the target is a different
      history that moves independently.
    - `tree: <member>` — a *peer* reference to another VE tree in the same
      workspace (see `.ve-workspace.yaml`). Resolution is a manifest lookup plus
      a filesystem read: the target is in the same working copy, hence the same
      commit, so `track`/`pinned` are meaningless and rejected.

    Both flavors may carry `why`: one line recording what this tree depends on in
    the target. That turns a pointer into a legible *interest edge*, which is
    what makes the reverse query ("who consumes this artifact?") worth asking.
    """

    artifact_type: ArtifactType
    artifact_id: str  # Short name of the referenced artifact
    repo: str | None = None  # GitHub-style org/repo format (cross-repo flavor)
    tree: str | None = None  # Workspace member name (peer flavor)
    why: str | None = None  # One line: what this tree depends on in the target
    track: str | None = None  # Branch to follow (cross-repo only)
    pinned: str | None = None  # 40-char SHA (optional)
    created_after: list[str] = []  # Local causal ordering
    # Chunk: docs/chunks/external_never_resolved - Has anybody ever read this target?
    last_resolved: str | None = None  # UTC instant of the last successful resolve

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str | None) -> str | None:
        """Validate repo is in org/repo format when present."""
        if v is None:
            return None
        return _require_valid_repo_ref(v, "repo")

    # Chunk: docs/chunks/federation_peer_refs - Member name validation for tree targets
    @field_validator("tree")
    @classmethod
    def validate_tree(cls, v: str | None) -> str | None:
        """Validate tree names a workspace member."""
        if v is None:
            return None
        return validate_member_name(v, "tree")

    # Chunk: docs/chunks/federation_peer_refs - Interest note is a single non-empty line
    @field_validator("why")
    @classmethod
    def validate_why(cls, v: str | None) -> str | None:
        """Validate why is one non-empty line.

        A blank note records nothing, and a multi-line note cannot be tabulated
        by the reverse-interest report that consumes it, so both are rejected
        rather than silently reshaped.
        """
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError(
                "why cannot be empty: it records what this tree depends on in the "
                "target artifact. Omit the field entirely if there is nothing to say"
            )
        if "\n" in stripped or "\r" in stripped:
            raise ValueError(
                "why must be a single line so consumer reports can tabulate it; "
                "put longer rationale in the pointing tree's own artifact"
            )
        return stripped

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, v: str) -> str:
        """Validate artifact_id is a valid directory name."""
        return _require_valid_dir_name(v, "artifact_id")

    # Chunk: docs/chunks/external_never_resolved - The stamp must be a real instant
    @field_validator("last_resolved", mode="before")
    @classmethod
    def validate_last_resolved(cls, v: object) -> str | None:
        """Validate last_resolved is an ISO-8601 instant.

        The field's whole value is that its absence is meaningful, so a garbled
        value must not be able to masquerade as a resolution that happened.

        Runs in ``before`` mode because YAML resolves an unquoted timestamp to a
        ``datetime`` rather than a string. `stamp_resolved` quotes what it
        writes, but a hand-edited or `yaml.dump`-written pointer need not, and
        rejecting those would be pedantry about quoting rather than about time.
        """
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if not isinstance(v, str):
            raise ValueError(
                f"last_resolved must be an ISO-8601 instant string, got "
                f"{type(v).__name__}"
            )
        stripped = v.strip()
        try:
            datetime.fromisoformat(stripped)
        except ValueError as exc:
            raise ValueError(
                f"last_resolved must be an ISO-8601 instant (e.g. "
                f"2026-08-07T11:14:08+00:00), got {v!r}. It is written by "
                f"`ve external resolve`; do not hand-edit it"
            ) from exc
        return stripped

    # Chunk: docs/chunks/federation_peer_refs - tree xor repo, and tracklessness of peer refs
    @model_validator(mode="after")
    def validate_target(self) -> "ExternalArtifactRef":
        """Enforce exactly one target, and that peer targets are trackless."""
        if self.repo is not None and self.tree is not None:
            raise ValueError(
                f"exactly one of 'repo' and 'tree' may be set, got both "
                f"(repo: {self.repo}, tree: {self.tree}). 'repo' addresses another "
                f"repository; 'tree' addresses another VE tree in this workspace"
            )
        if self.repo is None and self.tree is None:
            raise ValueError(
                "exactly one of 'repo' (another repository, as org/repo) and "
                "'tree' (a workspace member name) must be set; a pointer with no "
                "target cannot resolve"
            )

        if self.tree is not None:
            for field in ("track", "pinned"):
                if getattr(self, field) is not None:
                    raise ValueError(
                        f"'{field}' is invalid with 'tree': a peer reference resolves "
                        f"inside the same working copy, so it is already at the same "
                        f"commit as the tree pointing at it. Remove '{field}'"
                    )
            # Chunk: docs/chunks/external_never_resolved - Peers have nothing to stamp
            if self.last_resolved is not None:
                raise ValueError(
                    "'last_resolved' is invalid with 'tree': a peer reference "
                    "resolves through the workspace manifest against the same "
                    "commit, so it is either structurally resolvable right now or "
                    "reported by `ve workspace validate` as missing-target. There "
                    "is no 'has anyone ever looked' question to answer. "
                    "Remove 'last_resolved'"
                )
        return self

    # Chunk: docs/chunks/federation_peer_refs - Flavor predicate for callers
    @property
    def is_peer(self) -> bool:
        """True when this pointer targets a workspace member rather than a repo."""
        return self.tree is not None

    # Chunk: docs/chunks/federation_peer_refs - Uniform target rendering for display
    @property
    def target_display(self) -> str:
        """The pointer's target, formatted for human output."""
        if self.tree is not None:
            return f"tree:{self.tree}"
        return self.repo or "(no target)"

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
