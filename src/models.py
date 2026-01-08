"""Pydantic models for chunk validation."""

from pydantic import BaseModel, field_validator

from validation import validate_identifier


def _require_valid_dir_name(value: str, field_name: str) -> str:
    """Validate a directory name, raising ValueError if invalid."""
    errors = validate_identifier(value, field_name, allow_dot=True, max_length=31)
    if errors:
        raise ValueError("; ".join(errors))
    return value


class TaskConfig(BaseModel):
    """Configuration for cross-repository chunk management."""

    external_chunk_repo: str
    projects: list[str]

    @field_validator("external_chunk_repo")
    @classmethod
    def validate_external_chunk_repo(cls, v: str) -> str:
        """Validate external_chunk_repo is a valid directory name."""
        return _require_valid_dir_name(v, "external_chunk_repo")

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str]) -> list[str]:
        """Validate projects list is non-empty with valid directory names."""
        if not v:
            raise ValueError("projects must contain at least one project")
        for project in v:
            _require_valid_dir_name(project, "project")
        return v


class ExternalChunkRef(BaseModel):
    """Reference to a chunk in an external project."""

    project: str
    chunk: str

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        """Validate project is a valid directory name."""
        return _require_valid_dir_name(v, "project")

    @field_validator("chunk")
    @classmethod
    def validate_chunk(cls, v: str) -> str:
        """Validate chunk is a valid directory name."""
        return _require_valid_dir_name(v, "chunk")


class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalChunkRef] = []


class CodeRange(BaseModel):
    """A range of lines in a file that implements a specific requirement."""

    lines: str  # "N-M" or "N" format
    implements: str


class CodeReference(BaseModel):
    """A file with code ranges that implement requirements."""

    file: str
    ranges: list[CodeRange]
