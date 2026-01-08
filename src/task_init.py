"""Business logic for ve task init command."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from git_utils import is_git_repository


@dataclass
class TaskInitResult:
    """Result of a successful task init."""

    config_path: Path
    external_repo: str
    projects: list[str]


def _resolve_repo_path(cwd: Path, repo_ref: str) -> Path | None:
    """Resolve a repo reference to a filesystem path.

    Args:
        cwd: Task directory containing repositories
        repo_ref: Either org/repo format or plain directory name

    Returns:
        Path to the directory if found, None otherwise.
    """
    # If it's org/repo format, extract repo name
    if "/" in repo_ref:
        parts = repo_ref.split("/")
        if len(parts) == 2:
            org, repo = parts
            # Try just repo name first
            simple_path = cwd / repo
            if simple_path.exists() and simple_path.is_dir():
                return simple_path
            # Try nested org/repo
            nested_path = cwd / org / repo
            if nested_path.exists() and nested_path.is_dir():
                return nested_path
            return None

    # Plain directory name
    path = cwd / repo_ref
    if path.exists() and path.is_dir():
        return path
    return None


class TaskInit:
    """Initialize a task directory for cross-repository work."""

    def __init__(self, cwd: Path, external: str, projects: list[str]):
        """Create a TaskInit.

        Args:
            cwd: Current working directory where .ve-task.yaml will be created
            external: External chunk repository (org/repo format)
            projects: List of participating projects (org/repo format)
        """
        self.cwd = cwd
        self.external = external
        self.projects = projects

    def validate(self) -> list[str]:
        """Validate the task init configuration.

        Returns:
            List of validation error messages, empty if valid.
        """
        errors: list[str] = []

        # Check 1: .ve-task.yaml already exists
        if (self.cwd / ".ve-task.yaml").exists():
            errors.append("Task directory already exists (found .ve-task.yaml)")
            return errors

        # Check 2: No projects specified
        if not self.projects:
            errors.append("At least one --project is required")
            return errors

        # Check 3: Validate external directory
        errors.extend(self._validate_directory(self.external))

        # Check 4: Validate each project directory
        for project in self.projects:
            errors.extend(self._validate_directory(project))

        return errors

    def _validate_directory(self, repo_ref: str) -> list[str]:
        """Validate a single directory.

        Args:
            repo_ref: Repository reference (org/repo format or plain name)

        Returns:
            List of error messages for this directory.
        """
        errors: list[str] = []
        path = _resolve_repo_path(self.cwd, repo_ref)

        # Check if directory exists
        if path is None:
            errors.append(f"Directory '{repo_ref}' does not exist")
            return errors

        # Check if it's a git repository
        if not is_git_repository(path):
            errors.append(f"Directory '{repo_ref}' is not a git repository")
            return errors

        # Check if VE-initialized (docs/chunks/ exists)
        if not (path / "docs" / "chunks").exists():
            errors.append(
                f"Directory '{repo_ref}' is not a Vibe Engineer project (missing docs/chunks/)"
            )
            return errors

        return errors

    def execute(self) -> TaskInitResult:
        """Create the .ve-task.yaml file.

        Should only be called if validate() returns an empty list.

        Returns:
            TaskInitResult with path and configuration details.
        """
        config_path = self.cwd / ".ve-task.yaml"
        config_data = {
            "external_chunk_repo": self.external,
            "projects": self.projects,
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)

        return TaskInitResult(
            config_path=config_path,
            external_repo=self.external,
            projects=self.projects,
        )
