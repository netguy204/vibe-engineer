"""Utility functions for cross-repository task management."""
# Chunk: docs/chunks/chunk_create_task_aware - Cross-repo task utilities
# Chunk: docs/chunks/future_chunk_creation - Status support
# Chunk: docs/chunks/external_chunk_causal - Causal ordering for external chunks
# Chunk: docs/chunks/consolidate_ext_refs - Use ExternalArtifactRef for external.yaml
# Chunk: docs/chunks/consolidate_ext_ref_utils - Import from external_refs module

import re
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


# Chunk: docs/chunks/selective_project_linking - Parse --projects option into resolved project refs
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


# Chunk: docs/chunks/chunk_create_task_aware - Detect task directory
def is_task_directory(path: Path) -> bool:
    """Detect if path contains a .ve-task.yaml file."""
    return (path / ".ve-task.yaml").exists()


# Chunk: docs/chunks/chunk_create_task_aware - Resolve org/repo to path
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


# Chunk: docs/chunks/chunk_create_task_aware - Detect external chunk
# Chunk: docs/chunks/consolidate_ext_ref_utils - Delegate to external_refs module
def is_external_chunk(chunk_path: Path) -> bool:
    """Detect if chunk_path is an external chunk reference.

    An external chunk has external.yaml but no GOAL.md.

    Note: This is a convenience wrapper around is_external_artifact()
    for chunk-specific code.
    """
    return is_external_artifact(chunk_path, ArtifactType.CHUNK)


# Chunk: docs/chunks/chunk_create_task_aware - Load task configuration
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


# Chunk: docs/chunks/chunk_create_task_aware - Load external chunk reference
# Chunk: docs/chunks/consolidate_ext_refs - Updated to return ExternalArtifactRef
# Chunk: docs/chunks/consolidate_ext_ref_utils - Now imported from external_refs module
# load_external_ref is imported from external_refs


# Chunk: docs/chunks/chunk_create_task_aware - Get next chunk ID
# Chunk: docs/chunks/artifact_list_ordering - Use enumerate_chunks for directory-based ID
# Chunk: docs/chunks/ordering_remove_seqno - DEPRECATED: No longer needed for new naming
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


# Chunk: docs/chunks/chunk_create_task_aware - Create external.yaml
# Chunk: docs/chunks/ordering_remove_seqno - Use short_name only directory format
# Chunk: docs/chunks/external_chunk_causal - Support created_after for causal ordering
# Chunk: docs/chunks/consolidate_ext_refs - Use artifact_type and artifact_id fields
# Chunk: docs/chunks/consolidate_ext_ref_utils - Now imported from external_refs module
# create_external_yaml is imported from external_refs


# Chunk: docs/chunks/chunk_create_task_aware - Update frontmatter field
# Chunk: docs/chunks/future_chunk_creation - Used for status updates
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


# Chunk: docs/chunks/chunk_create_task_aware - Add dependents to chunk
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


# Chunk: docs/chunks/chunk_create_task_aware - Task chunk error class
class TaskChunkError(Exception):
    """Error during task chunk creation with user-friendly message."""

    pass


# Chunk: docs/chunks/chunk_create_task_aware - Orchestrate multi-repo chunk
# Chunk: docs/chunks/future_chunk_creation - Status parameter support
# Chunk: docs/chunks/ordering_remove_seqno - Use short_name only directory format
# Chunk: docs/chunks/external_chunk_causal - Pass current tips to external.yaml
# Chunk: docs/chunks/consolidate_ext_refs - Use ExternalArtifactRef format
# Chunk: docs/chunks/selective_project_linking - Optional project filtering
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

    # 3. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskChunkError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 4. Create chunk in external repo
    chunks = Chunks(external_repo_path)
    external_chunk_path = chunks.create_chunk(ticket_id, short_name, status=status)
    external_artifact_id = external_chunk_path.name  # Now short_name format

    # 5-6. For each project: create external.yaml with causal ordering, build dependents
    # Chunk: docs/chunks/selective_project_linking - Use filtered projects if specified
    effective_projects = projects if projects else config.projects
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

        # Build project artifact ID (short_name only, with ticket if provided)
        if ticket_id:
            project_artifact_id = f"{short_name}-{ticket_id}"
        else:
            project_artifact_id = short_name

        # Get current tips for this project's causal ordering
        try:
            index = ArtifactIndex(project_path)
            tips = index.find_tips(ArtifactType.CHUNK)
        except Exception:
            tips = []

        # Create external.yaml with created_after
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=project_artifact_id,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            pinned_sha=pinned_sha,
            created_after=tips,
            artifact_type=ArtifactType.CHUNK,
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


# Chunk: docs/chunks/list_task_aware - Task-aware chunk listing
# Chunk: docs/chunks/consolidate_ext_refs - Use ExternalArtifactRef format
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
    # Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks return type
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


# Chunk: docs/chunks/list_task_aware - Task-aware current chunk
# Chunk: docs/chunks/chunk_list_repo_source - Return repo ref with chunk name
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


# Chunk: docs/chunks/task_aware_narrative_cmds - Task narrative error class
class TaskNarrativeError(Exception):
    """Error during task narrative creation with user-friendly message."""

    pass


# Chunk: docs/chunks/task_aware_investigations - Task investigation error class
class TaskInvestigationError(Exception):
    """Error during task investigation creation with user-friendly message."""

    pass


# Chunk: docs/chunks/task_aware_subsystem_cmds - Task subsystem error class
class TaskSubsystemError(Exception):
    """Error during task subsystem creation with user-friendly message."""

    pass


# Chunk: docs/chunks/task_aware_narrative_cmds - Add dependents to narrative
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


# Chunk: docs/chunks/task_aware_investigations - Add dependents to investigation
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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Add dependents to subsystem
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


# Chunk: docs/chunks/task_aware_narrative_cmds - Orchestrate multi-repo narrative
# Chunk: docs/chunks/selective_project_linking - Optional project filtering
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

    # 3. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskNarrativeError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 4. Create narrative in external repo
    narratives = Narratives(external_repo_path)
    external_narrative_path = narratives.create_narrative(short_name)
    external_artifact_id = external_narrative_path.name

    # 5-6. For each project: create external.yaml with causal ordering, build dependents
    # Chunk: docs/chunks/selective_project_linking - Use filtered projects if specified
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

        # Create external.yaml with created_after
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            pinned_sha=pinned_sha,
            created_after=tips,
            artifact_type=ArtifactType.NARRATIVE,
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


# Chunk: docs/chunks/task_aware_narrative_cmds - Task-aware narrative listing
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


# Chunk: docs/chunks/task_aware_investigations - Orchestrate multi-repo investigation
# Chunk: docs/chunks/selective_project_linking - Optional project filtering
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

    # 3. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskInvestigationError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 4. Create investigation in external repo
    investigations = Investigations(external_repo_path)
    external_investigation_path = investigations.create_investigation(short_name)
    external_artifact_id = external_investigation_path.name

    # 5-6. For each project: create external.yaml with causal ordering, build dependents
    # Chunk: docs/chunks/selective_project_linking - Use filtered projects if specified
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

        # Create external.yaml with created_after
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            pinned_sha=pinned_sha,
            created_after=tips,
            artifact_type=ArtifactType.INVESTIGATION,
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


# Chunk: docs/chunks/task_aware_investigations - Task-aware investigation listing
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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Orchestrate multi-repo subsystem
# Chunk: docs/chunks/selective_project_linking - Optional project filtering
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

    # 3. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskSubsystemError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 4. Create subsystem in external repo
    subsystems = Subsystems(external_repo_path)
    external_subsystem_path = subsystems.create_subsystem(short_name)
    external_artifact_id = external_subsystem_path.name

    # 5-6. For each project: create external.yaml with causal ordering, build dependents
    # Chunk: docs/chunks/selective_project_linking - Use filtered projects if specified
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

        # Create external.yaml with created_after
        external_yaml_path = create_external_yaml(
            project_path=project_path,
            short_name=short_name,
            external_repo_ref=config.external_artifact_repo,
            external_artifact_id=external_artifact_id,
            pinned_sha=pinned_sha,
            created_after=tips,
            artifact_type=ArtifactType.SUBSYSTEM,
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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem listing
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


# Chunk: docs/chunks/artifact_promote - Task promote error class
class TaskPromoteError(Exception):
    """Error during artifact promotion with user-friendly message."""

    pass


# Chunk: docs/chunks/task_status_command - Grouped task artifact listing
class TaskArtifactListError(Exception):
    """Error during task artifact listing with user-friendly message."""

    pass


# Chunk: docs/chunks/artifact_promote - Find task directory from artifact path
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


# Chunk: docs/chunks/artifact_promote - Identify source project from artifact path
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


# Chunk: docs/chunks/artifact_promote - Generic add_dependents helper
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


# Chunk: docs/chunks/artifact_copy_backref - Append dependent with idempotency
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


# Chunk: docs/chunks/artifact_promote - Parse frontmatter for created_after
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


# Chunk: docs/chunks/artifact_promote - Promote artifact to external repo
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

    # 6. Get current SHA from external repo for pinned
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskPromoteError(
            f"Failed to resolve HEAD SHA in external repository: {e}"
        )

    # Save original created_after before copying
    original_created_after = _get_artifact_created_after(artifact_path, artifact_type)

    # 7. Copy artifact directory to external repo
    shutil.copytree(artifact_path, dest_path)

    # 8. Get external repo tips for the promoted artifact's created_after
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

    # 9. Update promoted artifact's dependents with source project
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": artifact_path.name,  # Original name in source project
        "repo": source_project,
    }
    add_dependents_to_artifact(dest_path, artifact_type, [dependent_entry])

    # 10. Clear source directory and create external.yaml
    # Remove all files from source directory
    for item in artifact_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    # Create external.yaml with original created_after
    external_yaml_path = create_external_yaml(
        project_path=artifact_path.parent.parent.parent,  # Go up from artifact to project root
        short_name=artifact_path.name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=dest_name,
        pinned_sha=pinned_sha,
        created_after=original_created_after,
        artifact_type=artifact_type,
    )

    return {
        "external_artifact_path": dest_path,
        "external_yaml_path": external_yaml_path,
    }


# Chunk: docs/chunks/task_status_command - Helper to list local artifacts with tips
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


# Chunk: docs/chunks/task_status_command - Grouped task artifact listing
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


# Chunk: docs/chunks/task_list_proposed - Task-aware proposed chunk listing
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


# Chunk: docs/chunks/copy_as_external - Copy external artifact error class
class TaskCopyExternalError(Exception):
    """Error during artifact copy as external with user-friendly message."""

    pass


# Chunk: docs/chunks/copy_as_external - Copy artifact as external reference
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible artifact and project resolution
# Chunk: docs/chunks/artifact_copy_backref - Back-reference update for copy-external
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

    # 8. Get current SHA from external repo for pinned
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskCopyExternalError(
            f"Failed to resolve HEAD SHA in external repository: {e}"
        )

    # 9. Get current tips for target project's causal ordering
    try:
        index = ArtifactIndex(target_project_path)
        tips = index.find_tips(artifact_type)
    except Exception:
        tips = []

    # 10. Create external.yaml with all parameters
    external_yaml_path = create_external_yaml(
        project_path=target_project_path,
        short_name=dest_name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=artifact_id,
        pinned_sha=pinned_sha,
        created_after=tips,
        artifact_type=artifact_type,
    )

    # 11. Update source artifact's dependents with back-reference
    # Chunk: docs/chunks/artifact_copy_backref - Back-reference update for copy-external
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": dest_name,  # The name in the target project
        "repo": target_project,
        "pinned": pinned_sha,
    }
    append_dependent_to_artifact(source_path, artifact_type, dependent_entry)

    # Return result
    return {
        "external_yaml_path": external_yaml_path,
        "source_updated": True,
    }


# Chunk: docs/chunks/remove_external_ref - Remove external artifact error class
class TaskRemoveExternalError(Exception):
    """Error during artifact removal from external with user-friendly message."""

    pass


# Chunk: docs/chunks/remove_external_ref - Remove dependent from artifact frontmatter
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


# Chunk: docs/chunks/remove_external_ref - Remove artifact from external project
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
