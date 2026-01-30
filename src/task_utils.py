"""Utility functions for cross-repository task management."""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from artifact_ordering import ArtifactIndex
from chunks import Chunks
from external_refs import (
    is_external_artifact,
    load_external_ref,
    create_external_yaml,
    normalize_artifact_path,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)
from git_utils import get_current_sha
from models import TaskConfig, ExternalArtifactRef, ArtifactType


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


def is_task_directory(path: Path) -> bool:
    """Detect if path contains a .ve-task.yaml file."""
    return (path / ".ve-task.yaml").exists()


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


def is_external_chunk(chunk_path: Path) -> bool:
    """Detect if chunk_path is an external chunk reference.

    An external chunk has external.yaml but no GOAL.md.

    Note: This is a convenience wrapper around is_external_artifact()
    for chunk-specific code.
    """
    return is_external_artifact(chunk_path, ArtifactType.CHUNK)


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


# load_external_ref is imported from external_refs


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
def get_next_chunk_id(project_path: Path) -> str:
    """Return next sequential chunk ID (e.g., '0005') for a project.

    DEPRECATED: This function is only needed for legacy external.yaml creation.
    New artifact creation uses short_name only without sequence prefixes.

    Args:
        project_path: Path to the project directory

    Returns:
        4-digit zero-padded string for the next chunk ID
    """
    import re

    chunks = Chunks(project_path)
    # Use enumerate_chunks() which just lists directories (doesn't require GOAL.md)
    chunk_dirs = chunks.enumerate_chunks()

    if not chunk_dirs:
        return "0001"

    # Extract highest chunk number by parsing directory names
    pattern = re.compile(r"^(\d{4})-")
    highest_number = 0
    for chunk_name in chunk_dirs:
        match = pattern.match(chunk_name)
        if match:
            chunk_number = int(match.group(1))
            if chunk_number > highest_number:
                highest_number = chunk_number
    return f"{highest_number + 1:04d}"


# create_external_yaml is imported from external_refs


def update_frontmatter_field(
    goal_path: Path,
    field: str,
    value,
) -> None:
    """Update a single field in GOAL.md frontmatter.

    Args:
        goal_path: Path to the GOAL.md file
        field: The frontmatter field name to update
        value: The new value for the field

    Raises:
        FileNotFoundError: If goal_path doesn't exist
        ValueError: If the file has no frontmatter
    """
    if not goal_path.exists():
        raise FileNotFoundError(f"File not found: {goal_path}")

    content = goal_path.read_text()

    # Parse frontmatter between --- markers
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {goal_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Update the field
    frontmatter[field] = value

    # Reconstruct the file
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"

    goal_path.write_text(new_content)


def add_dependents_to_chunk(
    chunk_path: Path,
    dependents: list[dict],
) -> None:
    """Update chunk GOAL.md frontmatter to include dependents list.

    Args:
        chunk_path: Path to the chunk directory containing GOAL.md
        dependents: List of {repo, chunk} dicts to add as dependents

    Raises:
        FileNotFoundError: If GOAL.md doesn't exist in chunk_path
    """
    goal_path = chunk_path / "GOAL.md"
    if not goal_path.exists():
        raise FileNotFoundError(f"GOAL.md not found in {chunk_path}")

    update_frontmatter_field(goal_path, "dependents", dependents)


class TaskChunkError(Exception):
    """Error during task chunk creation with user-friendly message."""

    pass


def create_task_chunk(
    task_dir: Path,
    short_name: str,
    ticket_id: str | None = None,
    status: str = "IMPLEMENTING",
    projects: list[str] | None = None,
) -> dict:
    """Create chunk in task directory context.

    Orchestrates multi-repo chunk creation:
    1. Creates chunk in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external chunk's GOAL.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the chunk
        ticket_id: Optional ticket ID
        status: Initial status for the chunk (default: "IMPLEMENTING")
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - external_chunk_path: Path to created chunk in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskChunkError: If any step fails, with user-friendly message
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # (Moved before chunk creation to pass correct projects to template)
    effective_projects = projects if projects else config.projects

    # 3. Create chunk in external repo with task context for proper template examples
    chunks = Chunks(external_repo_path)
    external_chunk_path = chunks.create_chunk(
        ticket_id,
        short_name,
        status=status,
        task_context=True,
        projects=effective_projects,  # Use filtered projects, not all projects
    )
    external_artifact_id = external_chunk_path.name  # Now short_name format

    # 4-5. For each project: create external.yaml with causal ordering, build dependents
    dependents = []
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskChunkError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Build project artifact ID (short_name only, ticket stored in frontmatter)
        project_artifact_id = short_name

        # Get current tips for this project's causal ordering
        try:
            index = ArtifactIndex(project_path)
            tips = index.find_tips(ArtifactType.CHUNK)
        except Exception:
            tips = []

        # Create external.yaml with created_after (no pinned SHA - always resolve to HEAD)
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=project_artifact_id,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            artifact_type=ArtifactType.CHUNK,
            created_after=tips,
        )

        # Build dependent entry using ExternalArtifactRef format
        dependents.append({
            "artifact_type": ArtifactType.CHUNK.value,
            "artifact_id": project_artifact_id,
            "repo": project_ref,
        })

        # Track created path
        project_refs[project_ref] = external_yaml_path

    # 7. Update external chunk's GOAL.md with dependents
    add_dependents_to_chunk(external_chunk_path, dependents)

    # 8. Return results
    return {
        "external_chunk_path": external_chunk_path,
        "project_refs": project_refs,
    }


def list_task_chunks(task_dir: Path) -> list[dict]:
    """List chunks from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by chunk number descending.

    Raises:
        TaskChunkError: If external repo not accessible
    """
    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # List chunks from external repo
    chunks = Chunks(external_repo_path)
    chunk_list = chunks.list_chunks()

    results = []
    for chunk_name in chunk_list:
        frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        # Convert ExternalArtifactRef objects to dicts for API compatibility
        dependents = [
            {"artifact_type": d.artifact_type.value, "artifact_id": d.artifact_id, "repo": d.repo}
            for d in frontmatter.dependents
        ] if frontmatter else []
        results.append({
            "name": chunk_name,
            "status": status,
            "dependents": dependents,
        })

    return results


def get_current_task_chunk(task_dir: Path) -> tuple[str | None, str]:
    """Get the current (IMPLEMENTING) chunk from external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        Tuple of (chunk_name, external_artifact_repo):
        - chunk_name: The chunk directory name if an IMPLEMENTING chunk exists, None otherwise
        - external_artifact_repo: The external_artifact_repo from task config

    Raises:
        TaskChunkError: If external repo not accessible
    """
    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External chunk repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # Get current chunk from external repo
    chunks = Chunks(external_repo_path)
    return (chunks.get_current_chunk(), config.external_artifact_repo)


class TaskNarrativeError(Exception):
    """Error during task narrative creation with user-friendly message."""

    pass


class TaskInvestigationError(Exception):
    """Error during task investigation creation with user-friendly message."""

    pass


class TaskSubsystemError(Exception):
    """Error during task subsystem creation with user-friendly message."""

    pass


def add_dependents_to_narrative(
    narrative_path: Path,
    dependents: list[dict],
) -> None:
    """Update narrative OVERVIEW.md frontmatter to include dependents list.

    Args:
        narrative_path: Path to the narrative directory containing OVERVIEW.md
        dependents: List of {artifact_type, artifact_id, repo} dicts to add as dependents

    Raises:
        FileNotFoundError: If OVERVIEW.md doesn't exist in narrative_path
    """
    overview_path = narrative_path / "OVERVIEW.md"
    if not overview_path.exists():
        raise FileNotFoundError(f"OVERVIEW.md not found in {narrative_path}")

    update_frontmatter_field(overview_path, "dependents", dependents)


def add_dependents_to_investigation(
    investigation_path: Path,
    dependents: list[dict],
) -> None:
    """Update investigation OVERVIEW.md frontmatter to include dependents list.

    Args:
        investigation_path: Path to the investigation directory containing OVERVIEW.md
        dependents: List of {artifact_type, artifact_id, repo} dicts to add as dependents

    Raises:
        FileNotFoundError: If OVERVIEW.md doesn't exist in investigation_path
    """
    overview_path = investigation_path / "OVERVIEW.md"
    if not overview_path.exists():
        raise FileNotFoundError(f"OVERVIEW.md not found in {investigation_path}")

    update_frontmatter_field(overview_path, "dependents", dependents)


def add_dependents_to_subsystem(
    subsystem_path: Path,
    dependents: list[dict],
) -> None:
    """Update subsystem OVERVIEW.md frontmatter to include dependents list.

    Args:
        subsystem_path: Path to the subsystem directory containing OVERVIEW.md
        dependents: List of {artifact_type, artifact_id, repo} dicts to add as dependents

    Raises:
        FileNotFoundError: If OVERVIEW.md doesn't exist in subsystem_path
    """
    overview_path = subsystem_path / "OVERVIEW.md"
    if not overview_path.exists():
        raise FileNotFoundError(f"OVERVIEW.md not found in {subsystem_path}")

    update_frontmatter_field(overview_path, "dependents", dependents)


def create_task_narrative(
    task_dir: Path,
    short_name: str,
    projects: list[str] | None = None,
) -> dict:
    """Create narrative in task directory context.

    Orchestrates multi-repo narrative creation:
    1. Creates narrative in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external narrative's OVERVIEW.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the narrative
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - external_narrative_path: Path to created narrative in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskNarrativeError: If any step fails, with user-friendly message
    """
    from narratives import Narratives

    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskNarrativeError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskNarrativeError(
            f"External narrative repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Create narrative in external repo
    narratives = Narratives(external_repo_path)
    external_narrative_path = narratives.create_narrative(short_name)
    external_artifact_id = external_narrative_path.name

    # 4-5. For each project: create external.yaml with causal ordering, build dependents
    effective_projects = projects if projects else config.projects
    dependents = []
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskNarrativeError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Get current tips for this project's causal ordering
        try:
            index = ArtifactIndex(project_path)
            tips = index.find_tips(ArtifactType.NARRATIVE)
        except Exception:
            tips = []

        # Create external.yaml with created_after (no pinned SHA - always resolve to HEAD)
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            artifact_type=ArtifactType.NARRATIVE,
            created_after=tips,
        )

        # Build dependent entry using ExternalArtifactRef format
        dependents.append({
            "artifact_type": ArtifactType.NARRATIVE.value,
            "artifact_id": short_name,
            "repo": project_ref,
        })

        # Track created path
        project_refs[project_ref] = external_yaml_path

    # 7. Update external narrative's OVERVIEW.md with dependents
    add_dependents_to_narrative(external_narrative_path, dependents)

    # 8. Return results
    return {
        "external_narrative_path": external_narrative_path,
        "project_refs": project_refs,
    }


def list_task_narratives(task_dir: Path) -> list[dict]:
    """List narratives from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by narrative name descending.

    Raises:
        TaskNarrativeError: If external repo not accessible
    """
    from narratives import Narratives

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskNarrativeError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskNarrativeError(
            f"External narrative repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # List narratives from external repo
    narratives = Narratives(external_repo_path)
    artifact_index = ArtifactIndex(external_repo_path)

    # Get narratives in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.NARRATIVE)
    narrative_list = list(reversed(ordered))

    results = []
    for narrative_name in narrative_list:
        frontmatter = narratives.parse_narrative_frontmatter(narrative_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        # Convert ExternalArtifactRef objects to dicts for API compatibility
        dependents = [
            {"artifact_type": d.artifact_type.value, "artifact_id": d.artifact_id, "repo": d.repo}
            for d in frontmatter.dependents
        ] if frontmatter else []
        results.append({
            "name": narrative_name,
            "status": status,
            "dependents": dependents,
        })

    return results


def create_task_investigation(
    task_dir: Path,
    short_name: str,
    projects: list[str] | None = None,
) -> dict:
    """Create investigation in task directory context.

    Orchestrates multi-repo investigation creation:
    1. Creates investigation in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external investigation's OVERVIEW.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the investigation
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - external_investigation_path: Path to created investigation in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskInvestigationError: If any step fails, with user-friendly message
    """
    from investigations import Investigations

    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskInvestigationError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskInvestigationError(
            f"External investigation repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Create investigation in external repo
    investigations = Investigations(external_repo_path)
    external_investigation_path = investigations.create_investigation(short_name)
    external_artifact_id = external_investigation_path.name

    # 4-5. For each project: create external.yaml with causal ordering, build dependents
    effective_projects = projects if projects else config.projects
    dependents = []
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskInvestigationError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Get current tips for this project's causal ordering
        try:
            index = ArtifactIndex(project_path)
            tips = index.find_tips(ArtifactType.INVESTIGATION)
        except Exception:
            tips = []

        # Create external.yaml with created_after (no pinned SHA - always resolve to HEAD)
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            artifact_type=ArtifactType.INVESTIGATION,
            created_after=tips,
        )

        # Build dependent entry using ExternalArtifactRef format
        dependents.append({
            "artifact_type": ArtifactType.INVESTIGATION.value,
            "artifact_id": short_name,
            "repo": project_ref,
        })

        # Track created path
        project_refs[project_ref] = external_yaml_path

    # 7. Update external investigation's OVERVIEW.md with dependents
    add_dependents_to_investigation(external_investigation_path, dependents)

    # 8. Return results
    return {
        "external_investigation_path": external_investigation_path,
        "project_refs": project_refs,
    }


def list_task_investigations(task_dir: Path) -> list[dict]:
    """List investigations from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by investigation name descending.

    Raises:
        TaskInvestigationError: If external repo not accessible
    """
    from investigations import Investigations

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskInvestigationError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskInvestigationError(
            f"External investigation repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # List investigations from external repo
    investigations = Investigations(external_repo_path)
    artifact_index = ArtifactIndex(external_repo_path)

    # Get investigations in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.INVESTIGATION)
    investigation_list = list(reversed(ordered))

    results = []
    for investigation_name in investigation_list:
        frontmatter = investigations.parse_investigation_frontmatter(investigation_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        # Convert ExternalArtifactRef objects to dicts for API compatibility
        dependents = [
            {"artifact_type": d.artifact_type.value, "artifact_id": d.artifact_id, "repo": d.repo}
            for d in frontmatter.dependents
        ] if frontmatter else []
        results.append({
            "name": investigation_name,
            "status": status,
            "dependents": dependents,
        })

    return results


def create_task_subsystem(
    task_dir: Path,
    short_name: str,
    projects: list[str] | None = None,
) -> dict:
    """Create subsystem in task directory context.

    Orchestrates multi-repo subsystem creation:
    1. Creates subsystem in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external subsystem's OVERVIEW.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the subsystem
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - external_subsystem_path: Path to created subsystem in external repo
        - project_refs: Dict mapping project repo ref to created external.yaml path

    Raises:
        TaskSubsystemError: If any step fails, with user-friendly message
    """
    from subsystems import Subsystems

    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskSubsystemError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskSubsystemError(
            f"External subsystem repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Create subsystem in external repo
    subsystems = Subsystems(external_repo_path)
    external_subsystem_path = subsystems.create_subsystem(short_name)
    external_artifact_id = external_subsystem_path.name

    # 4-5. For each project: create external.yaml with causal ordering, build dependents
    effective_projects = projects if projects else config.projects
    dependents = []
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskSubsystemError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Get current tips for this project's causal ordering
        try:
            index = ArtifactIndex(project_path)
            tips = index.find_tips(ArtifactType.SUBSYSTEM)
        except Exception:
            tips = []

        # Create external.yaml with created_after (no pinned SHA - always resolve to HEAD)
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            artifact_type=ArtifactType.SUBSYSTEM,
            created_after=tips,
        )

        # Build dependent entry using ExternalArtifactRef format
        dependents.append({
            "artifact_type": ArtifactType.SUBSYSTEM.value,
            "artifact_id": short_name,
            "repo": project_ref,
        })

        # Track created path
        project_refs[project_ref] = external_yaml_path

    # 7. Update external subsystem's OVERVIEW.md with dependents
    add_dependents_to_subsystem(external_subsystem_path, dependents)

    # 8. Return results
    return {
        "external_subsystem_path": external_subsystem_path,
        "project_refs": project_refs,
    }


def list_task_subsystems(task_dir: Path) -> list[dict]:
    """List subsystems from external repo with their dependents.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys: name, status, dependents
        Sorted by causal ordering (newest first).

    Raises:
        TaskSubsystemError: If external repo not accessible
    """
    from subsystems import Subsystems

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskSubsystemError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskSubsystemError(
            f"External subsystem repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # List subsystems from external repo
    subsystems = Subsystems(external_repo_path)
    artifact_index = ArtifactIndex(external_repo_path)

    # Get subsystems in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.SUBSYSTEM)
    subsystem_list = list(reversed(ordered))

    results = []
    for subsystem_name in subsystem_list:
        frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        # Convert ExternalArtifactRef objects to dicts for API compatibility
        dependents = [
            {"artifact_type": d.artifact_type.value, "artifact_id": d.artifact_id, "repo": d.repo}
            for d in frontmatter.dependents
        ] if frontmatter else []
        results.append({
            "name": subsystem_name,
            "status": status,
            "dependents": dependents,
        })

    return results


class TaskPromoteError(Exception):
    """Error during artifact promotion with user-friendly message."""

    pass


class TaskArtifactListError(Exception):
    """Error during task artifact listing with user-friendly message."""

    pass


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


def identify_source_project(task_dir: Path, artifact_path: Path, config: TaskConfig) -> str:
    """Determine which project (org/repo format) contains the artifact.

    Args:
        task_dir: The task directory containing .ve-task.yaml.
        artifact_path: Path to the artifact being promoted.
        config: Loaded task configuration.

    Returns:
        The project reference in org/repo format.

    Raises:
        TaskPromoteError: If artifact is not within any configured project.
    """
    artifact_resolved = artifact_path.resolve()

    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            project_resolved = project_path.resolve()

            # Check if artifact_path is within this project
            try:
                artifact_resolved.relative_to(project_resolved)
                return project_ref
            except ValueError:
                continue
        except FileNotFoundError:
            continue

    raise TaskPromoteError(
        f"Artifact '{artifact_path}' is not within any configured project. "
        f"Projects: {', '.join(config.projects)}"
    )


def add_dependents_to_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    dependents: list[dict],
) -> None:
    """Update artifact's main file frontmatter to include dependents list.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        dependents: List of {artifact_type, artifact_id, repo} dicts.

    Raises:
        FileNotFoundError: If main file doesn't exist in artifact_path.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        raise FileNotFoundError(f"{main_file} not found in {artifact_path}")

    update_frontmatter_field(main_path, "dependents", dependents)


def append_dependent_to_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    dependent: dict,
) -> None:
    """Append a dependent entry to artifact's frontmatter, preserving existing entries.

    If an identical dependent already exists (same repo, artifact_type, artifact_id),
    it will be updated with the new pinned SHA rather than duplicated.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        dependent: Dict with keys: artifact_type, artifact_id, repo, pinned

    Raises:
        FileNotFoundError: If main file doesn't exist in artifact_path.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        raise FileNotFoundError(f"{main_file} not found in {artifact_path}")

    # Read existing frontmatter
    content = main_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {main_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Get existing dependents or create empty list
    existing_dependents = frontmatter.get("dependents", []) or []

    # Check for existing entry with same (repo, artifact_type, artifact_id) key
    # If found, update the pinned SHA; if not, append new entry
    match_key = (dependent["repo"], dependent["artifact_type"], dependent["artifact_id"])
    found = False

    for i, existing in enumerate(existing_dependents):
        existing_key = (
            existing.get("repo"),
            existing.get("artifact_type"),
            existing.get("artifact_id"),
        )
        if existing_key == match_key:
            # Update existing entry with new pinned SHA
            existing_dependents[i] = dependent
            found = True
            break

    if not found:
        existing_dependents.append(dependent)

    # Update frontmatter and write back
    frontmatter["dependents"] = existing_dependents
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"
    main_path.write_text(new_content)


def _get_artifact_created_after(artifact_path: Path, artifact_type: ArtifactType) -> list[str]:
    """Get the created_after field from an artifact's main file.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.

    Returns:
        List of artifact names from created_after, or empty list.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        return []

    import re as _re
    content = main_path.read_text()

    # Parse frontmatter
    match = _re.match(r"^---\s*\n(.*?)\n---\s*\n", content, _re.DOTALL)
    if not match:
        return []

    frontmatter = yaml.safe_load(match.group(1)) or {}
    created_after = frontmatter.get("created_after", [])

    if created_after is None:
        return []
    if isinstance(created_after, str):
        return [created_after]
    if isinstance(created_after, list):
        return created_after

    return []


def promote_artifact(
    artifact_path: Path,
    new_name: str | None = None,
) -> dict:
    """Promote a local artifact to the task-level external repository.

    Orchestrates artifact promotion:
    1. Validates artifact is local (not already external)
    2. Detects artifact type from path
    3. Finds task directory and loads config
    4. Identifies source project
    5. Checks for collision in external repo
    6. Copies artifact directory to external repo
    7. Updates promoted artifact's created_after to external tips
    8. Updates promoted artifact's dependents with source project
    9. Creates external.yaml in source, preserving original created_after

    Args:
        artifact_path: Path to the local artifact directory.
        new_name: Optional new name for destination (--name flag value).

    Returns:
        Dict with keys:
        - external_artifact_path: Path to promoted artifact in external repo
        - external_yaml_path: Path to created external.yaml in source

    Raises:
        TaskPromoteError: If any step fails, with user-friendly message.
    """
    import shutil
    from external_refs import (
        detect_artifact_type_from_path,
        is_external_artifact,
        ARTIFACT_DIR_NAME,
    )

    artifact_path = Path(artifact_path).resolve()

    # 1. Validate artifact exists and has a main document
    if not artifact_path.exists():
        raise TaskPromoteError(f"Artifact path does not exist: {artifact_path}")

    if not artifact_path.is_dir():
        raise TaskPromoteError(f"Artifact path is not a directory: {artifact_path}")

    # 2. Detect artifact type from path
    try:
        artifact_type = detect_artifact_type_from_path(artifact_path)
    except ValueError as e:
        raise TaskPromoteError(str(e))

    # Check if already external
    if is_external_artifact(artifact_path, artifact_type):
        raise TaskPromoteError(
            f"Artifact '{artifact_path.name}' is already an external reference. "
            f"Cannot promote an artifact that is already external."
        )

    # Verify main file exists
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    if not (artifact_path / main_file).exists():
        raise TaskPromoteError(
            f"Artifact '{artifact_path.name}' does not have a {main_file} file. "
            f"Only local artifacts with main documents can be promoted."
        )

    # 3. Find task directory
    task_dir = find_task_directory(artifact_path)
    if task_dir is None:
        raise TaskPromoteError(
            f"Cannot find task directory (.ve-task.yaml) above '{artifact_path}'. "
            f"Artifact promotion requires a task context."
        )

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskPromoteError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 4. Identify source project
    source_project = identify_source_project(task_dir, artifact_path, config)

    # 5. Resolve external repo and check for collision
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskPromoteError(
            f"External artifact repository '{config.external_artifact_repo}' not found"
        )

    # Determine destination name
    dest_name = new_name if new_name else artifact_path.name
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    dest_path = external_repo_path / "docs" / dir_name / dest_name

    if dest_path.exists():
        raise TaskPromoteError(
            f"Artifact '{dest_name}' already exists in external repository at {dest_path}. "
            f"Use --name to specify a different name."
        )

    # Save original created_after before copying
    original_created_after = _get_artifact_created_after(artifact_path, artifact_type)

    # 6. Copy artifact directory to external repo
    shutil.copytree(artifact_path, dest_path)

    # 7. Get external repo tips for the promoted artifact's created_after
    try:
        external_index = ArtifactIndex(external_repo_path)
        external_tips = external_index.find_tips(artifact_type)
        # Exclude the just-copied artifact from tips (it's not in the index yet)
        external_tips = [t for t in external_tips if t != dest_name]
    except Exception:
        external_tips = []

    # Update promoted artifact's created_after to external tips
    dest_main_path = dest_path / main_file
    if external_tips:
        update_frontmatter_field(dest_main_path, "created_after", external_tips)

    # 8. Update promoted artifact's dependents with source project
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": artifact_path.name,  # Original name in source project
        "repo": source_project,
    }
    add_dependents_to_artifact(dest_path, artifact_type, [dependent_entry])

    # 9. Clear source directory and create external.yaml
    # Remove all files from source directory
    for item in artifact_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    # Create external.yaml with original created_after (no pinned SHA - always resolve to HEAD)
    external_yaml_path = create_external_yaml(
        project_path=artifact_path.parent.parent.parent,  # Go up from artifact to project root
        short_name=artifact_path.name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=dest_name,
        artifact_type=artifact_type,
        created_after=original_created_after,
    )

    return {
        "external_artifact_path": dest_path,
        "external_yaml_path": external_yaml_path,
    }


def _list_local_artifacts(
    project_path: Path,
    artifact_type: ArtifactType,
) -> list[dict]:
    """List local artifacts for a project, excluding external references.

    Args:
        project_path: Path to the project directory
        artifact_type: Type of artifacts to list

    Returns:
        List of dicts with keys: name, status, is_tip
        Sorted by causal ordering (newest first).
    """
    from chunks import Chunks
    from narratives import Narratives
    from investigations import Investigations
    from subsystems import Subsystems

    artifact_index = ArtifactIndex(project_path)
    tips = set(artifact_index.find_tips(artifact_type))

    # Get ordered list (oldest first) and reverse for newest first
    ordered = artifact_index.get_ordered(artifact_type)
    artifact_list = list(reversed(ordered))

    # Get appropriate manager and parse frontmatter
    results = []
    for artifact_name in artifact_list:
        # Check if this is an external reference - skip if so
        artifact_dir = (
            project_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_name
        )
        if is_external_artifact(artifact_dir, artifact_type):
            continue

        # Parse frontmatter based on artifact type
        if artifact_type == ArtifactType.CHUNK:
            manager = Chunks(project_path)
            frontmatter = manager.parse_chunk_frontmatter(artifact_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
        elif artifact_type == ArtifactType.NARRATIVE:
            manager = Narratives(project_path)
            frontmatter = manager.parse_narrative_frontmatter(artifact_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
        elif artifact_type == ArtifactType.INVESTIGATION:
            manager = Investigations(project_path)
            frontmatter = manager.parse_investigation_frontmatter(artifact_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
        elif artifact_type == ArtifactType.SUBSYSTEM:
            manager = Subsystems(project_path)
            frontmatter = manager.parse_subsystem_frontmatter(artifact_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
        else:
            status = "UNKNOWN"

        results.append({
            "name": artifact_name,
            "status": status,
            "is_tip": artifact_name in tips,
        })

    return results


def list_task_artifacts_grouped(
    task_dir: Path,
    artifact_type: ArtifactType,
) -> dict:
    """List artifacts from task context grouped by location.

    Collects artifacts from all locations in a task (external repo + each project)
    and groups them by source. External repo artifacts show their dependents;
    local artifacts are filtered to exclude external references.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_type: Type of artifacts to list

    Returns:
        Dict with keys:
        - external: {repo, artifacts: [{name, status, dependents, is_tip}]}
        - projects: [{repo, artifacts: [{name, status, is_tip}]}]

    Raises:
        TaskArtifactListError: If external repo not accessible
    """
    from chunks import Chunks
    from narratives import Narratives
    from investigations import Investigations
    from subsystems import Subsystems

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskArtifactListError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskArtifactListError(
            f"External repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # Build external artifacts list
    artifact_index = ArtifactIndex(external_repo_path)
    tips = set(artifact_index.find_tips(artifact_type))

    # Get ordered list (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(artifact_type)
    artifact_list = list(reversed(ordered))

    # Get appropriate manager for external repo
    if artifact_type == ArtifactType.CHUNK:
        manager = Chunks(external_repo_path)
    elif artifact_type == ArtifactType.NARRATIVE:
        manager = Narratives(external_repo_path)
    elif artifact_type == ArtifactType.INVESTIGATION:
        manager = Investigations(external_repo_path)
    elif artifact_type == ArtifactType.SUBSYSTEM:
        manager = Subsystems(external_repo_path)
    else:
        raise TaskArtifactListError(f"Unknown artifact type: {artifact_type}")

    # Parse external artifacts with dependents
    external_artifacts = []
    for artifact_name in artifact_list:
        if artifact_type == ArtifactType.CHUNK:
            frontmatter = manager.parse_chunk_frontmatter(artifact_name)
        elif artifact_type == ArtifactType.NARRATIVE:
            frontmatter = manager.parse_narrative_frontmatter(artifact_name)
        elif artifact_type == ArtifactType.INVESTIGATION:
            frontmatter = manager.parse_investigation_frontmatter(artifact_name)
        elif artifact_type == ArtifactType.SUBSYSTEM:
            frontmatter = manager.parse_subsystem_frontmatter(artifact_name)
        else:
            frontmatter = None

        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        dependents = []
        if frontmatter and hasattr(frontmatter, 'dependents') and frontmatter.dependents:
            dependents = [
                {"artifact_type": d.artifact_type.value, "artifact_id": d.artifact_id, "repo": d.repo}
                for d in frontmatter.dependents
            ]

        external_artifacts.append({
            "name": artifact_name,
            "status": status,
            "dependents": dependents,
            "is_tip": artifact_name in tips,
        })

    # Build project lists
    project_results = []
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            # Skip inaccessible projects
            continue

        local_artifacts = _list_local_artifacts(project_path, artifact_type)
        project_results.append({
            "repo": project_ref,
            "artifacts": local_artifacts,
        })

    return {
        "external": {
            "repo": config.external_artifact_repo,
            "artifacts": external_artifacts,
        },
        "projects": project_results,
    }


def list_task_proposed_chunks(task_dir: Path) -> dict:
    """List proposed chunks from task context grouped by repository.

    Collects proposed chunks from investigations, narratives, and subsystems
    across all repositories in the task (external repo + project repos).

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        Dict with keys:
        - external: {repo, proposed_chunks: [{prompt, source_type, source_id}]}
        - projects: [{repo, proposed_chunks: [...]}]

    Raises:
        TaskChunkError: If external repo not accessible
    """
    from investigations import Investigations
    from narratives import Narratives
    from subsystems import Subsystems

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskChunkError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskChunkError(
            f"External repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # Collect proposed chunks from external repo
    chunks = Chunks(external_repo_path)
    investigations = Investigations(external_repo_path)
    narratives = Narratives(external_repo_path)
    subsystems = Subsystems(external_repo_path)

    external_proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems)

    # Build project lists
    project_results = []
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            # Skip inaccessible projects
            continue

        # Collect proposed chunks from this project
        proj_chunks = Chunks(project_path)
        proj_investigations = Investigations(project_path)
        proj_narratives = Narratives(project_path)
        proj_subsystems = Subsystems(project_path)

        proj_proposed = proj_chunks.list_proposed_chunks(
            proj_investigations, proj_narratives, proj_subsystems
        )

        project_results.append({
            "repo": project_ref,
            "proposed_chunks": proj_proposed,
        })

    return {
        "external": {
            "repo": config.external_artifact_repo,
            "proposed_chunks": external_proposed,
        },
        "projects": project_results,
    }


class TaskCopyExternalError(Exception):
    """Error during artifact copy as external with user-friendly message."""

    pass


def copy_artifact_as_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
    new_name: str | None = None,
) -> dict:
    """Copy an artifact from external repo as an external reference in target project.

    Creates an external.yaml in the target project that references an artifact
    already present in the external artifact repository.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Flexible project ref (e.g., "acme/proj" or just "proj")
        new_name: Optional new name for the artifact in destination

    Returns:
        Dict with keys:
        - external_yaml_path: Path to created external.yaml in target project

    Raises:
        TaskCopyExternalError: If any step fails, with user-friendly message.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Normalize artifact path with external repo context
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path,
            search_path=external_repo_path,
            external_repo_name=external_repo_path.name,
        )
    except ValueError as e:
        raise TaskCopyExternalError(str(e))

    # 4. Verify the artifact exists in external repo
    source_path = external_repo_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
    if not source_path.exists():
        raise TaskCopyExternalError(
            f"Artifact '{artifact_id}' does not exist in external repository at {source_path}"
        )

    # 5. Resolve flexible project reference
    try:
        target_project = resolve_project_ref(target_project, config.projects)
    except ValueError as e:
        raise TaskCopyExternalError(str(e))

    try:
        target_project_path = resolve_repo_directory(task_dir, target_project)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"Target project '{target_project}' not found or not accessible"
        )

    # 6. Determine destination name
    dest_name = new_name if new_name else artifact_id

    # 7. Check for collision in target project
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    dest_path = target_project_path / "docs" / dir_name / dest_name
    if dest_path.exists():
        raise TaskCopyExternalError(
            f"Artifact '{dest_name}' already exists in target project at {dest_path}. "
            f"Use --name to specify a different name."
        )

    # 8. Get current tips for target project's causal ordering
    try:
        index = ArtifactIndex(target_project_path)
        tips = index.find_tips(artifact_type)
    except Exception:
        tips = []

    # 9. Create external.yaml (no pinned SHA - always resolve to HEAD)
    external_yaml_path = create_external_yaml(
        project_path=target_project_path,
        short_name=dest_name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=artifact_id,
        artifact_type=artifact_type,
        created_after=tips,
    )

    # 10. Update source artifact's dependents with back-reference
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": dest_name,  # The name in the target project
        "repo": target_project,
    }
    append_dependent_to_artifact(source_path, artifact_type, dependent_entry)

    # Return result
    return {
        "external_yaml_path": external_yaml_path,
        "source_updated": True,
    }


class TaskRemoveExternalError(Exception):
    """Error during artifact removal from external with user-friendly message."""

    pass


def remove_dependent_from_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    repo: str,
    artifact_id: str,
) -> bool:
    """Remove a dependent entry from artifact's frontmatter.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        repo: Repository reference to match (e.g., "acme/proj").
        artifact_id: Artifact ID to match (the name in the target project).

    Returns:
        True if an entry was removed, False if no matching entry found.

    Raises:
        FileNotFoundError: If main file doesn't exist in artifact_path.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        raise FileNotFoundError(f"{main_file} not found in {artifact_path}")

    # Read existing frontmatter
    content = main_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {main_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Get existing dependents or return early if none
    existing_dependents = frontmatter.get("dependents", []) or []
    if not existing_dependents:
        return False

    # Find and remove matching entry
    match_key = (repo, artifact_id)
    found = False
    new_dependents = []

    for existing in existing_dependents:
        existing_key = (
            existing.get("repo"),
            existing.get("artifact_id"),
        )
        if existing_key == match_key:
            found = True
            # Skip this entry (remove it)
        else:
            new_dependents.append(existing)

    if not found:
        return False

    # Update frontmatter and write back
    frontmatter["dependents"] = new_dependents
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"
    main_path.write_text(new_content)

    return True


def remove_artifact_from_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
) -> dict:
    """Remove an artifact's external reference from a target project.

    Inverse of copy_artifact_as_external(). Removes the external.yaml from the
    target project and updates the artifact's dependents list in the external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Flexible project ref (e.g., "acme/proj" or just "proj")

    Returns:
        Dict with keys:
        - removed: bool - True if external.yaml was removed
        - dependent_removed: bool - True if dependent entry was removed from source
        - orphaned: bool - True if this was the last project link (warning)
        - directory_cleaned: bool - True if empty directory was removed

    Raises:
        TaskRemoveExternalError: If any step fails, with user-friendly message.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Normalize artifact path with external repo context
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path,
            search_path=external_repo_path,
            external_repo_name=external_repo_path.name,
        )
    except ValueError as e:
        raise TaskRemoveExternalError(str(e))

    # 4. Verify the artifact exists in external repo
    source_path = external_repo_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
    if not source_path.exists():
        raise TaskRemoveExternalError(
            f"Artifact '{artifact_id}' does not exist in external repository at {source_path}"
        )

    # 5. Resolve flexible project reference
    try:
        target_project = resolve_project_ref(target_project, config.projects)
    except ValueError as e:
        raise TaskRemoveExternalError(str(e))

    try:
        target_project_path = resolve_repo_directory(task_dir, target_project)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"Target project '{target_project}' not found or not accessible"
        )

    # 6. Determine the artifact directory in target project
    # The artifact may have been copied with the same name as in external repo
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    target_artifact_dir = target_project_path / "docs" / dir_name / artifact_id
    external_yaml_path = target_artifact_dir / "external.yaml"

    # 7. Check if external.yaml exists (idempotent - return early if not)
    if not external_yaml_path.exists():
        return {
            "removed": False,
            "dependent_removed": False,
            "orphaned": False,
            "directory_cleaned": False,
        }

    # 8. Load external.yaml to get the actual artifact_id in external repo
    # (may differ if --name was used during copy)
    ref = load_external_ref(target_artifact_dir)
    source_artifact_id = ref.artifact_id

    # Update source_path if artifact_id differs (--name was used)
    if source_artifact_id != artifact_id:
        source_path = external_repo_path / "docs" / dir_name / source_artifact_id

    # 9. Delete external.yaml
    external_yaml_path.unlink()
    removed = True

    # 10. Remove directory if now empty
    directory_cleaned = False
    if target_artifact_dir.exists():
        remaining_files = list(target_artifact_dir.iterdir())
        if not remaining_files:
            target_artifact_dir.rmdir()
            directory_cleaned = True

    # 11. Remove dependent entry from source artifact's frontmatter
    # The dependent entry uses artifact_id as the name in the target project
    dependent_removed = False
    try:
        dependent_removed = remove_dependent_from_artifact(
            source_path,
            artifact_type,
            target_project,
            artifact_id,  # The name in the target project
        )
    except (FileNotFoundError, ValueError):
        # Source artifact may not have a dependents field, or frontmatter is malformed
        pass

    # 12. Check if dependents list is now empty (orphan warning)
    orphaned = False
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = source_path / main_file
    if main_path.exists():
        content = main_path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            dependents = frontmatter.get("dependents", []) or []
            orphaned = len(dependents) == 0

    return {
        "removed": removed,
        "dependent_removed": dependent_removed,
        "orphaned": orphaned,
        "directory_cleaned": directory_cleaned,
    }


class TaskFrictionError(Exception):
    """Error during task friction logging with user-friendly message."""

    pass


def create_task_friction_entry(
    task_dir: Path,
    title: str,
    description: str,
    impact: str,
    theme_id: str,
    theme_name: str | None = None,
    projects: list[str] | None = None,
) -> dict:
    """Create friction entry in task directory context.

    Orchestrates multi-repo friction entry creation:
    1. Creates friction entry in external repo's FRICTION.md
    2. Adds/updates external_friction_sources in each project's FRICTION.md

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        title: Brief title for the friction entry
        description: Detailed description of the friction
        impact: Severity level (low, medium, high, blocking)
        theme_id: Theme ID to cluster the entry under
        theme_name: Human-readable theme name (required if theme is new)
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - entry_id: The ID of the created entry (e.g., "F003")
        - external_repo_path: Path to external repo
        - project_refs: Dict mapping project repo ref to whether FRICTION.md was updated

    Raises:
        TaskFrictionError: If any step fails, with user-friendly message
    """
    from friction import Friction

    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskFrictionError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskFrictionError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Check that external repo has FRICTION.md
    friction_log = Friction(external_repo_path)
    if not friction_log.exists():
        raise TaskFrictionError(
            f"External repository '{config.external_artifact_repo}' does not have a FRICTION.md. "
            f"Run 've init' in the external repo first."
        )

    # 4. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskFrictionError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 5. Create friction entry in external repo
    try:
        entry_id = friction_log.append_entry(
            title=title,
            description=description,
            impact=impact,
            theme_id=theme_id,
            theme_name=theme_name,
        )
    except ValueError as e:
        raise TaskFrictionError(f"Failed to create friction entry: {e}")

    # 6. For each project: add/update external_friction_sources
    effective_projects = projects if projects else config.projects
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskFrictionError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Check if project has FRICTION.md
        project_friction = Friction(project_path)
        if not project_friction.exists():
            # Skip projects without FRICTION.md (with implicit warning via project_refs)
            project_refs[project_ref] = False
            continue

        # Add external friction source reference
        try:
            add_external_friction_source(
                project_path=project_path,
                external_repo_ref=config.external_artifact_repo,
                pinned_sha=pinned_sha,
                entry_id=entry_id,
            )
            project_refs[project_ref] = True
        except ValueError as e:
            raise TaskFrictionError(
                f"Failed to update FRICTION.md in project '{project_ref}': {e}"
            )

    # 7. Return results
    return {
        "entry_id": entry_id,
        "external_repo_path": external_repo_path,
        "project_refs": project_refs,
    }


def add_external_friction_source(
    project_path: Path,
    external_repo_ref: str,
    pinned_sha: str,
    entry_id: str,
) -> None:
    """Add or update external friction source reference in project's FRICTION.md.

    If an external_friction_sources entry for the same repo already exists,
    the entry_id is appended to entry_ids (if not already present) and
    pinned SHA is updated. Otherwise, a new entry is created.

    Args:
        project_path: Path to the project directory
        external_repo_ref: External repo in org/repo format
        pinned_sha: Commit SHA at time of reference creation
        entry_id: Friction entry ID to add (e.g., "F003")

    Raises:
        ValueError: If FRICTION.md doesn't exist or has invalid frontmatter
    """
    friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
    if not friction_path.exists():
        raise ValueError(f"FRICTION.md not found in {project_path}")

    content = friction_path.read_text()

    # Parse frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {friction_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Get or create external_friction_sources list
    external_sources = frontmatter.get("external_friction_sources", []) or []

    # Find existing entry for this repo
    found = False
    for source in external_sources:
        if source.get("repo") == external_repo_ref:
            # Update existing entry
            entry_ids = source.get("entry_ids", []) or []
            if entry_id not in entry_ids:
                entry_ids.append(entry_id)
                source["entry_ids"] = entry_ids
            source["pinned"] = pinned_sha
            found = True
            break

    if not found:
        # Create new entry
        external_sources.append({
            "repo": external_repo_ref,
            "track": "main",
            "pinned": pinned_sha,
            "entry_ids": [entry_id],
        })

    # Update frontmatter and write back
    frontmatter["external_friction_sources"] = external_sources
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"
    friction_path.write_text(new_content)


class TaskOverlapError(Exception):
    """Error during task overlap detection with user-friendly message."""

    pass


@dataclass
class TaskOverlapResult:
    """Result of task-aware overlap detection.

    Attributes:
        overlapping_chunks: List of (repo_ref, chunk_name) tuples for overlapping chunks.
                           repo_ref is the org/repo format or "external" for the external repo.
    """
    overlapping_chunks: list[tuple[str, str]]


def find_task_overlapping_chunks(
    task_dir: Path,
    chunk_id: str,
) -> TaskOverlapResult:
    """Find overlapping chunks across all repos in task context.

    Aggregates chunks from:
    1. External artifact repo
    2. All project repos

    Then computes overlap against the target chunk's code references,
    supporting project-qualified refs (e.g., "project_name::src/foo.py#Bar").

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        chunk_id: The chunk ID to check for overlaps

    Returns:
        TaskOverlapResult with list of (repo_ref, chunk_name) tuples

    Raises:
        TaskOverlapError: If task config or repos not accessible
        ValueError: If chunk_id not found
    """
    from chunks import Chunks, ChunkStatus, compute_symbolic_overlap
    from symbols import parse_reference, qualify_ref

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskOverlapError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskOverlapError(
            f"External repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # Find the target chunk (could be in external repo or a project)
    target_chunks = None
    target_chunk_name = None
    target_repo_ref = None
    target_project_path = None

    # First try external repo
    external_chunks = Chunks(external_repo_path)
    resolved = external_chunks.resolve_chunk_id(chunk_id)
    if resolved is not None:
        target_chunks = external_chunks
        target_chunk_name = resolved
        target_repo_ref = config.external_artifact_repo
        target_project_path = external_repo_path
    else:
        # Try project repos
        for project_ref in config.projects:
            try:
                project_path = resolve_repo_directory(task_dir, project_ref)
                project_chunks = Chunks(project_path)
                resolved = project_chunks.resolve_chunk_id(chunk_id)
                if resolved is not None:
                    target_chunks = project_chunks
                    target_chunk_name = resolved
                    target_repo_ref = project_ref
                    target_project_path = project_path
                    break
            except FileNotFoundError:
                continue

    if target_chunks is None:
        raise ValueError(f"Chunk '{chunk_id}' not found in any task repository")

    # Parse target chunk frontmatter
    frontmatter = target_chunks.parse_chunk_frontmatter(target_chunk_name)
    if frontmatter is None:
        raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}'")

    # Extract target code references
    code_refs = [{"ref": ref.ref, "implements": ref.implements} for ref in frontmatter.code_references]
    if not code_refs:
        return TaskOverlapResult(overlapping_chunks=[])

    target_refs = target_chunks._extract_symbolic_refs(code_refs)
    if not target_refs:
        return TaskOverlapResult(overlapping_chunks=[])

    # Build list of all candidate chunks across repos
    # Format: (repo_ref, chunks_instance, chunk_name, project_path)
    all_candidates: list[tuple[str, Chunks, str, Path]] = []

    # Add external repo chunks
    for name in external_chunks.enumerate_chunks():
        if name != target_chunk_name or target_repo_ref != config.external_artifact_repo:
            all_candidates.append((config.external_artifact_repo, external_chunks, name, external_repo_path))

    # Add project repo chunks
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            project_chunks = Chunks(project_path)
            for name in project_chunks.enumerate_chunks():
                # Skip the target chunk
                if name == target_chunk_name and project_ref == target_repo_ref:
                    continue
                # Skip external references (they point to external repo)
                if is_external_chunk(project_path / "docs" / "chunks" / name):
                    continue
                all_candidates.append((project_ref, project_chunks, name, project_path))
        except FileNotFoundError:
            continue

    # Check each candidate for overlap
    overlapping: list[tuple[str, str]] = []

    for repo_ref, chunks_instance, candidate_name, candidate_project_path in all_candidates:
        fm = chunks_instance.parse_chunk_frontmatter(candidate_name)
        if fm is None or fm.status != ChunkStatus.ACTIVE:
            continue

        candidate_refs_raw = [{"ref": ref.ref, "implements": ref.implements} for ref in fm.code_references]
        if not candidate_refs_raw:
            continue

        candidate_refs = chunks_instance._extract_symbolic_refs(candidate_refs_raw)
        if not candidate_refs:
            continue

        # Compute overlap - need to handle project-qualified refs
        # Normalize both target and candidate refs to (project_path, file, symbol) form
        # for proper comparison across projects
        if _compute_cross_project_overlap(
            target_refs,
            target_project_path,
            candidate_refs,
            candidate_project_path,
            task_dir,
            config.projects,
        ):
            overlapping.append((repo_ref, candidate_name))

    return TaskOverlapResult(overlapping_chunks=sorted(overlapping))


def _compute_cross_project_overlap(
    target_refs: list[str],
    target_project: Path,
    candidate_refs: list[str],
    candidate_project: Path,
    task_dir: Path,
    available_projects: list[str],
) -> bool:
    """Compute overlap between refs that may be from different projects.

    Handles project-qualified refs (e.g., "project::src/foo.py#Bar") by
    resolving them to absolute file paths for comparison.

    Args:
        target_refs: Target chunk's code references
        target_project: Default project for target's non-qualified refs
        candidate_refs: Candidate chunk's code references
        candidate_project: Default project for candidate's non-qualified refs
        task_dir: Task directory for resolving project refs
        available_projects: List of valid project refs

    Returns:
        True if any overlap exists, False otherwise.
    """
    # Normalize refs to (absolute_file_path, symbol_path) form
    def normalize_ref(ref: str, default_project: Path) -> tuple[Path, str | None]:
        """Normalize a ref to (absolute_file, symbol) tuple."""
        # Check if project-qualified (has :: before any #)
        hash_pos = ref.find("#")
        check_portion = ref[:hash_pos] if hash_pos != -1 else ref

        if "::" in check_portion:
            # Project-qualified ref
            try:
                project_path, file_path, symbol_path = resolve_project_qualified_ref(
                    ref, task_dir, available_projects
                )
                return (project_path / file_path, symbol_path)
            except (ValueError, FileNotFoundError):
                # Can't resolve - fall back to default project
                # Remove the project qualifier from the ref
                double_colon_pos = check_portion.find("::")
                ref = ref[double_colon_pos + 2:]

        # Non-qualified ref - parse file and symbol directly
        if "#" in ref:
            file_path, symbol_path = ref.split("#", 1)
        else:
            file_path = ref
            symbol_path = None

        return (default_project / file_path, symbol_path)

    # Normalize all refs
    target_normalized = [normalize_ref(r, target_project) for r in target_refs]
    candidate_normalized = [normalize_ref(r, candidate_project) for r in candidate_refs]

    # Check for overlap: same file and overlapping symbols
    for target_file, target_symbol in target_normalized:
        for candidate_file, candidate_symbol in candidate_normalized:
            # Files must match (comparing absolute paths)
            if target_file != candidate_file:
                continue

            # If either has no symbol, any file match is overlap
            if target_symbol is None or candidate_symbol is None:
                return True

            # Check symbol hierarchy (inline implementation)
            # Two symbols overlap if one is a prefix of the other (with :: separator)
            # or if they are the same
            if target_symbol == candidate_symbol:
                return True
            if target_symbol.startswith(candidate_symbol + "::"):
                return True
            if candidate_symbol.startswith(target_symbol + "::"):
                return True

    return False


class TaskActivateError(Exception):
    """Error during task chunk activation with user-friendly message."""

    pass


def activate_task_chunk(
    task_dir: Path,
    chunk_id: str,
) -> tuple[str, str]:
    """Activate a FUTURE chunk in task context.

    Searches for the chunk in the external repo and all project repos,
    then activates it by changing status to IMPLEMENTING.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        chunk_id: The chunk ID to activate

    Returns:
        Tuple of (repo_ref, activated_chunk_name)

    Raises:
        TaskActivateError: If task config or repos not accessible
        ValueError: If chunk not found or activation fails
    """
    from chunks import Chunks

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskActivateError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskActivateError(
            f"External repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # Try to find and activate the chunk
    # First try external repo (preferred location for task-level chunks)
    external_chunks = Chunks(external_repo_path)
    resolved = external_chunks.resolve_chunk_id(chunk_id)
    if resolved is not None:
        try:
            activated = external_chunks.activate_chunk(resolved)
            return (config.external_artifact_repo, activated)
        except ValueError as e:
            raise ValueError(f"Cannot activate chunk in external repo: {e}")

    # Try project repos
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            project_chunks = Chunks(project_path)
            resolved = project_chunks.resolve_chunk_id(chunk_id)
            if resolved is not None:
                # Skip external references
                chunk_dir = project_path / "docs" / "chunks" / resolved
                if is_external_chunk(chunk_dir):
                    continue
                try:
                    activated = project_chunks.activate_chunk(resolved)
                    return (project_ref, activated)
                except ValueError as e:
                    raise ValueError(f"Cannot activate chunk in {project_ref}: {e}")
        except FileNotFoundError:
            continue

    raise ValueError(f"Chunk '{chunk_id}' not found in any task repository")
