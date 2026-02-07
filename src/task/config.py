"""Configuration loading and project resolution for task operations.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module handles:
- Task directory detection (.ve-task.yaml)
- Task configuration loading and validation
- Project reference resolution (org/repo format)
- Project-qualified code reference parsing
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from models import TaskConfig


def is_task_directory(path: Path) -> bool:
    """Detect if path contains a .ve-task.yaml file."""
    return (path / ".ve-task.yaml").exists()


def load_task_config(path: Path) -> TaskConfig:
    """Load and validate .ve-task.yaml from path.

    Args:
        path: Directory containing .ve-task.yaml

    Returns:
        Validated TaskConfig

    Raises:
        FileNotFoundError: If .ve-task.yaml doesn't exist
        ValidationError: If YAML content is invalid
    """
    config_file = path / ".ve-task.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f".ve-task.yaml not found in {path}")

    with open(config_file) as f:
        data = yaml.safe_load(f)

    return TaskConfig.model_validate(data)


# Chunk: docs/chunks/chunk_create_task_aware - Resolves org/repo reference to filesystem path
def resolve_repo_directory(task_dir: Path, repo_ref: str) -> Path:
    """Resolve a GitHub-style org/repo reference to a filesystem path.

    Resolution order:
    1. Try {task_dir}/{repo}/ (just the repo name)
    2. Try {task_dir}/{org}/{repo}/ (nested for collision handling)

    Args:
        task_dir: The task directory containing repository worktrees
        repo_ref: GitHub-style org/repo reference (e.g., "acme/service-a")

    Returns:
        Path to the repository directory

    Raises:
        ValueError: If repo_ref is not in org/repo format
        FileNotFoundError: If neither resolution path exists
    """
    if "/" not in repo_ref:
        raise ValueError(f"repo_ref must be in 'org/repo' format, got: {repo_ref}")

    parts = repo_ref.split("/")
    if len(parts) != 2:
        raise ValueError(f"repo_ref must have exactly one slash, got: {repo_ref}")

    org, repo = parts

    # Try just the repo name first (common case)
    simple_path = task_dir / repo
    if simple_path.exists() and simple_path.is_dir():
        return simple_path

    # Try nested org/repo for collision handling
    nested_path = task_dir / org / repo
    if nested_path.exists() and nested_path.is_dir():
        return nested_path

    raise FileNotFoundError(
        f"Repository '{repo_ref}' not found. "
        f"Tried: {simple_path}, {nested_path}"
    )


# Chunk: docs/chunks/selective_project_linking - Parse --projects CLI option into resolved refs
def parse_projects_option(
    projects_input: str | None,
    available_projects: list[str],
) -> list[str] | None:
    """Parse --projects option into resolved project refs.

    Args:
        projects_input: Comma-separated project refs from CLI (e.g., "proj1,acme/proj2").
        available_projects: List of valid project refs from task config.

    Returns:
        List of resolved canonical org/repo project refs, or None if projects_input
        is None or empty (indicating all projects should be used).

    Raises:
        ValueError: If any project ref cannot be resolved.
    """
    if projects_input is None:
        return None

    # Split on comma, strip whitespace
    project_names = [p.strip() for p in projects_input.split(",") if p.strip()]

    if not project_names:
        return None

    # Resolve each to canonical format
    return [resolve_project_ref(p, available_projects) for p in project_names]


# Chunk: docs/chunks/accept_full_artifact_paths - Flexible project reference resolution
def resolve_project_ref(
    project_input: str,
    available_projects: list[str],
) -> str:
    """Resolve flexible project reference to canonical org/repo format.

    Accepts either full org/repo format or just repo name and resolves
    to the full format from available projects.

    Args:
        project_input: User-provided project identifier (e.g., "dotter" or "acme/dotter").
        available_projects: List of valid project refs from task config.

    Returns:
        Canonical org/repo format.

    Raises:
        ValueError: If no match found or multiple ambiguous matches.
    """
    # If project_input contains /, validate it exists in available_projects
    if "/" in project_input:
        if project_input in available_projects:
            return project_input
        # Not found - raise error with available projects
        raise ValueError(
            f"Project '{project_input}' not found in available projects. "
            f"Available: {', '.join(available_projects)}"
        )

    # No slash - search available_projects for repos ending with /{project_input}
    matches = [
        proj for proj in available_projects
        if proj.endswith(f"/{project_input}")
    ]

    if len(matches) == 0:
        raise ValueError(
            f"Project '{project_input}' not found in available projects. "
            f"Available: {', '.join(available_projects)}"
        )

    if len(matches) > 1:
        raise ValueError(
            f"Project '{project_input}' is ambiguous. "
            f"Matches: {', '.join(matches)}. "
            f"Please specify the full org/repo format."
        )

    return matches[0]


def resolve_project_qualified_ref(
    ref: str,
    task_dir: Path,
    available_projects: list[str],
    default_project: Path | None = None,
) -> tuple[Path, str, str | None]:
    """Resolve a project-qualified code reference.

    Parses refs like "project_name::src/foo.py#Bar" and resolves the project
    path. For non-qualified refs (no "::" prefix), uses the default_project.

    Args:
        ref: Code reference (may be project-qualified like "proj::src/foo.py#Bar")
        task_dir: Task directory for resolving project names
        available_projects: List of valid project refs from task config
        default_project: Project path to use for non-qualified refs (required if ref is non-qualified)

    Returns:
        Tuple of (project_path, file_path, symbol_path or None)

    Raises:
        ValueError: If project cannot be resolved or default_project is None for non-qualified ref
    """
    # Check if this is a project-qualified reference
    # Only look for :: before the # (symbol separator)
    hash_pos = ref.find("#")
    check_portion = ref[:hash_pos] if hash_pos != -1 else ref
    is_project_qualified = "::" in check_portion

    if is_project_qualified:
        # Parse the project qualifier
        double_colon_pos = check_portion.find("::")
        project_input = ref[:double_colon_pos]
        remaining = ref[double_colon_pos + 2:]

        # Resolve the project reference
        project_ref = resolve_project_ref(project_input, available_projects)
        project_path = resolve_repo_directory(task_dir, project_ref)

        # Parse file and symbol from remaining
        if "#" in remaining:
            file_path, symbol_path = remaining.split("#", 1)
        else:
            file_path = remaining
            symbol_path = None

        return (project_path, file_path, symbol_path)
    else:
        # Non-qualified reference - use default_project
        if default_project is None:
            raise ValueError(
                f"Cannot resolve non-qualified reference '{ref}' without a default project"
            )

        # Parse file and symbol
        if "#" in ref:
            file_path, symbol_path = ref.split("#", 1)
        else:
            file_path = ref
            symbol_path = None

        return (default_project, file_path, symbol_path)


# Chunk: docs/chunks/artifact_promote - Walk up from artifact path to find task directory
def find_task_directory(start_path: Path) -> Path | None:
    """Walk up from start_path to find directory containing .ve-task.yaml.

    Args:
        start_path: Starting path to search from.

    Returns:
        Path to the task directory, or None if not found.
    """
    current = start_path.resolve()

    # Walk up the directory tree
    while current != current.parent:
        if (current / ".ve-task.yaml").exists():
            return current
        current = current.parent

    # Check root as well
    if (current / ".ve-task.yaml").exists():
        return current

    return None


@dataclass
class TaskProjectContext:
    """Context information when running from within a task's project.

    Attributes:
        task_dir: Path to the task directory containing .ve-task.yaml.
        project_ref: The project reference in org/repo format.
    """
    task_dir: Path
    project_ref: str


def check_task_project_context(project_dir: Path) -> TaskProjectContext | None:
    """Check if project_dir is within a project that's part of a task.

    This function detects when artifact creation commands are being run from
    inside a project directory that participates in a task (as opposed to
    from the task directory itself or from a standalone project).

    Args:
        project_dir: The directory from which the command is being run.

    Returns:
        TaskProjectContext if project_dir is within a task's project,
        None otherwise (either not in a task context, or at the task root).
    """
    project_dir = project_dir.resolve()

    # Walk up looking for .ve-task.yaml
    task_dir = find_task_directory(project_dir)
    if task_dir is None:
        # Not in any task context
        return None

    # Check if we're at the task root itself (not in a project)
    if project_dir == task_dir:
        # Running from task directory - this is correct behavior
        return None

    # We're in a subdirectory of a task - check if it's within a configured project
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        return None

    # Check each project to see if project_dir is within it
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            project_resolved = project_path.resolve()

            # Check if project_dir is the same as or within this project
            try:
                project_dir.relative_to(project_resolved)
                # Found! project_dir is within this project
                return TaskProjectContext(task_dir=task_dir, project_ref=project_ref)
            except ValueError:
                # Not within this project, try next
                continue
        except FileNotFoundError:
            # Project directory doesn't exist, skip
            continue

    # Not within any configured project (could be in external repo or other directory)
    return None
