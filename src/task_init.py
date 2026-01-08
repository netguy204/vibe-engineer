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


class TaskInit:
    """Initialize a task directory for cross-repository work."""

    def __init__(self, cwd: Path, external: str, projects: list[str]):
        """Create a TaskInit.

        Args:
            cwd: Current working directory where .ve-task.yaml will be created
            external: Name of the external chunk repository directory
            projects: List of participating project directory names
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

    def _validate_directory(self, name: str) -> list[str]:
        """Validate a single directory.

        Args:
            name: Directory name relative to cwd

        Returns:
            List of error messages for this directory.
        """
        errors: list[str] = []
        path = self.cwd / name

        # Check if directory exists
        if not path.exists():
            errors.append(f"Directory '{name}' does not exist")
            return errors

        # Check if it's a git repository
        if not is_git_repository(path):
            errors.append(f"Directory '{name}' is not a git repository")
            return errors

        # Check if VE-initialized (docs/chunks/ exists)
        if not (path / "docs" / "chunks").exists():
            errors.append(
                f"Directory '{name}' is not a Vibe Engineer project (missing docs/chunks/)"
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
