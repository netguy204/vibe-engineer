"""Business logic for ve task init command."""
# Chunk: docs/chunks/task_init - Task directory initialization
# Chunk: docs/chunks/task_init_scaffolding - Task CLAUDE.md and commands scaffolding
# Chunk: docs/chunks/task_config_local_paths - Local path resolution

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from git_utils import get_github_org_repo, is_git_repository
from template_system import TaskContext, render_template, render_to_directory


# Chunk: docs/chunks/task_init - Result of task init
# Chunk: docs/chunks/task_init_scaffolding - Added created_files tracking
@dataclass
class TaskInitResult:
    """Result of a successful task init."""

    config_path: Path
    external_repo: str
    projects: list[str]
    created_files: list[str] = field(default_factory=list)


# Chunk: docs/chunks/task_init - Resolve repo reference to path
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


# Chunk: docs/chunks/task_config_local_paths - Resolve to org/repo format
def _resolve_to_org_repo(cwd: Path, repo_ref: str) -> str:
    """Resolve a repo reference to org/repo format from its git remote.

    Args:
        cwd: Task directory containing repositories
        repo_ref: Either org/repo format or plain directory name

    Returns:
        The org/repo string extracted from the git remote URL

    Raises:
        ValueError: If directory doesn't exist, is not a git repo,
            or has no origin remote configured
    """
    path = _resolve_repo_path(cwd, repo_ref)
    if path is None:
        raise ValueError(f"Directory '{repo_ref}' does not exist")

    return get_github_org_repo(path)


# Chunk: docs/chunks/task_init - Task initialization class
# Chunk: docs/chunks/task_config_local_paths - Local path resolution in TaskInit
class TaskInit:
    """Initialize a task directory for cross-repository work."""

    def __init__(self, cwd: Path, external: str, projects: list[str]):
        """Create a TaskInit.

        Args:
            cwd: Current working directory where .ve-task.yaml will be created
            external: External chunk repository (org/repo format or plain directory name)
            projects: List of participating projects (org/repo format or plain directory names)
        """
        self.cwd = cwd
        self.external = external
        self.projects = projects
        # Resolved values are populated during validate()
        self._resolved_external: str | None = None
        self._resolved_projects: list[str] | None = None

    def validate(self) -> list[str]:
        """Validate the task init configuration.

        Resolves local directory names to org/repo format from git remotes.

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

        # Check 3: Validate and resolve external directory
        external_errors, resolved_external = self._validate_and_resolve(self.external)
        errors.extend(external_errors)
        self._resolved_external = resolved_external

        # Check 4: Validate and resolve each project directory
        resolved_projects = []
        for project in self.projects:
            project_errors, resolved_project = self._validate_and_resolve(project)
            errors.extend(project_errors)
            resolved_projects.append(resolved_project)
        self._resolved_projects = resolved_projects

        return errors

    def _validate_and_resolve(self, repo_ref: str) -> tuple[list[str], str | None]:
        """Validate a directory and resolve it to org/repo format.

        Args:
            repo_ref: Repository reference (org/repo format or plain name)

        Returns:
            Tuple of (error messages, resolved org/repo or None if errors)
        """
        errors: list[str] = []
        path = _resolve_repo_path(self.cwd, repo_ref)

        # Check if directory exists
        if path is None:
            errors.append(f"Directory '{repo_ref}' does not exist")
            return errors, None

        # Check if it's a git repository
        if not is_git_repository(path):
            errors.append(f"Directory '{repo_ref}' is not a git repository")
            return errors, None

        # Check if VE-initialized (docs/chunks/ exists)
        if not (path / "docs" / "chunks").exists():
            errors.append(
                f"Directory '{repo_ref}' is not a Vibe Engineer project (missing docs/chunks/)"
            )
            return errors, None

        # Try to resolve to org/repo from git remote
        try:
            org_repo = get_github_org_repo(path)
            return errors, org_repo
        except ValueError as e:
            # Provide clear error message with original input
            error_msg = str(e)
            if "no origin remote" in error_msg.lower():
                errors.append(f"Directory '{repo_ref}' has no origin remote configured")
            elif "not a github url" in error_msg.lower():
                errors.append(
                    f"Directory '{repo_ref}' remote is not a GitHub URL"
                )
            else:
                errors.append(f"Directory '{repo_ref}': {error_msg}")
            return errors, None

    # Chunk: docs/chunks/task_init_scaffolding - Render task CLAUDE.md
    def _render_claude_md(self) -> list[str]:
        """Render the task CLAUDE.md template to task root.

        Returns:
            List of created file paths (relative to task root).
        """
        created = []
        dest_file = self.cwd / "CLAUDE.md"

        task_context = TaskContext(
            external_artifact_repo=self.external,
            projects=self.projects,
        )
        rendered = render_template(
            "task", "CLAUDE.md.jinja2", **task_context.as_dict()
        )
        dest_file.write_text(rendered)
        created.append("CLAUDE.md")

        return created

    # Chunk: docs/chunks/task_init_scaffolding - Render command templates
    def _render_commands(self) -> list[str]:
        """Render command templates to .claude/commands/ with task context.

        Returns:
            List of created file paths (relative to task root).
        """
        created = []
        commands_dir = self.cwd / ".claude" / "commands"

        task_context = TaskContext(
            external_artifact_repo=self.external,
            projects=self.projects,
        )
        render_result = render_to_directory(
            "commands", commands_dir, **task_context.as_dict()
        )

        # Map paths to relative strings
        for path in render_result.created:
            created.append(f".claude/commands/{path.name}")

        return created

    def execute(self) -> TaskInitResult:
        """Create the .ve-task.yaml file and scaffolding.

        Should only be called if validate() returns an empty list.

        Returns:
            TaskInitResult with path and configuration details.
        """
        created_files = []

        # Create .ve-task.yaml
        config_path = self.cwd / ".ve-task.yaml"

        # Use resolved values from validate()
        external_repo = self._resolved_external or self.external
        projects = self._resolved_projects or self.projects

        config_data = {
            "external_artifact_repo": external_repo,
            "projects": projects,
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
        created_files.append(".ve-task.yaml")

        # Render CLAUDE.md
        created_files.extend(self._render_claude_md())

        # Render command templates
        created_files.extend(self._render_commands())

        return TaskInitResult(
            config_path=config_path,
            external_repo=external_repo,
            projects=projects,
            created_files=created_files,
        )
