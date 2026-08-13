"""Shared utilities and cross-cutting helpers for model validation."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Shared utilities module

import re

from pydantic import BaseModel, field_validator

from validation import validate_identifier


# Chunk: docs/chunks/crossref_artifact_id_cap - Length capped by path legality, not 31
def _require_valid_dir_name(value: str, field_name: str) -> str:
    """Validate a directory name, raising ValueError if invalid.

    Length is bounded by the filesystem path-component limit (the
    validate_identifier default), so ordinary descriptive artifact names of
    any realistic length are representable.
    """
    errors = validate_identifier(value, field_name, allow_dot=True)
    if errors:
        raise ValueError("; ".join(errors))
    return value


# Chunk: docs/chunks/chunk_create_task_aware - Validator for GitHub org/repo format
def _require_valid_repo_ref(value: str, field_name: str) -> str:
    """Validate a GitHub-style org/repo reference.

    Format: {org}/{repo} where both parts are valid identifiers.
    """
    if "/" not in value:
        raise ValueError(f"{field_name} must be in 'org/repo' format")

    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError(f"{field_name} must have exactly one slash (org/repo format)")

    org, repo = parts
    if not org:
        raise ValueError(f"{field_name} org part cannot be empty")
    if not repo:
        raise ValueError(f"{field_name} repo part cannot be empty")

    # Validate org part (allow dots, max 39 chars per GitHub)
    org_errors = validate_identifier(org, f"{field_name} org", allow_dot=True, max_length=39)
    if org_errors:
        raise ValueError("; ".join(org_errors))

    # Validate repo part (allow dots, max 100 chars per GitHub)
    repo_errors = validate_identifier(repo, f"{field_name} repo", allow_dot=True, max_length=100)
    if repo_errors:
        raise ValueError("; ".join(repo_errors))

    return value


# Chunk: docs/chunks/federation_member_refs - One qualifier shape rule for comments and frontmatter
def classify_qualifier_shape(qualifier: str) -> tuple[str, str | None]:
    """Classify a ``::`` qualifier by shape alone.

    The single authority for what a qualifier *is*, shared by the comment
    grammar (``backreferences._classify_qualifier``) and the frontmatter
    model (``models.references.SymbolicReference``) so the two cannot drift:

    - no ``/``  → ``"member"``: another VE tree in the same workspace. The
      shape is an identifier (dots allowed) with no length cap — how long a
      member name may be is the workspace manifest's rule.
    - one ``/`` → ``"repo"``: a GitHub-style ``org/repo`` reference to a
      tree in another repository.
    - anything else → ``"invalid"``, with a reason.

    Existence is deliberately not checked here: a well-formed member
    qualifier naming a tree that does not exist is still ``"member"``, and
    reporting that is the workspace validator's job.

    Callers split on ``::`` first; `qualifier` must be non-empty and must
    not itself contain ``::``.

    Returns:
        ``(kind, reason)`` where kind is ``"member"``, ``"repo"``, or
        ``"invalid"``; reason is None unless kind is ``"invalid"``.
    """
    slash_count = qualifier.count("/")
    if slash_count == 0:
        errors = validate_identifier(
            qualifier, "member qualifier", allow_dot=True, max_length=None
        )
        if errors:
            return "invalid", "; ".join(errors)
        return "member", None

    if slash_count == 1:
        try:
            _require_valid_repo_ref(qualifier, "repo qualifier")
        except ValueError as exc:
            return "invalid", str(exc)
        return "repo", None

    return "invalid", (
        f"qualifier '{qualifier}' must be a workspace member name (no '/') or an "
        "'org/repo' reference (exactly one '/')"
    )


# Regex for validating 40-character hex SHA
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


# Chunk: docs/chunks/chunk_create_task_aware - Model with org/repo format validation
class TaskConfig(BaseModel):
    """Configuration for cross-repository workflow artifact management.

    All repository references use GitHub's org/repo format.
    The external_artifact_repo specifies where all external workflow artifacts
    (chunks, narratives, investigations, subsystems) are stored.
    """

    external_artifact_repo: str  # org/repo format
    projects: list[str]  # list of org/repo format

    @field_validator("external_artifact_repo")
    @classmethod
    def validate_external_artifact_repo(cls, v: str) -> str:
        """Validate external_artifact_repo is in org/repo format."""
        return _require_valid_repo_ref(v, "external_artifact_repo")

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str]) -> list[str]:
        """Validate projects list is non-empty with org/repo format entries."""
        if not v:
            raise ValueError("projects must contain at least one project")
        for project in v:
            _require_valid_repo_ref(project, "project")
        return v
