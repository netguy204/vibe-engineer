"""Shared utilities and cross-cutting helpers for model validation."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Shared utilities module

import re

from pydantic import BaseModel, field_validator

from validation import validate_identifier


def _require_valid_dir_name(value: str, field_name: str) -> str:
    """Validate a directory name, raising ValueError if invalid."""
    errors = validate_identifier(value, field_name, allow_dot=True, max_length=31)
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
