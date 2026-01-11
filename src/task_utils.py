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
    ARTIFACT_MAIN_FILE,
)
from git_utils import get_current_sha
from models import TaskConfig, ExternalArtifactRef, ArtifactType


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
# Chunk: docs/chunks/remove_sequence_prefix - DEPRECATED: No longer needed for new naming
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
# Chunk: docs/chunks/remove_sequence_prefix - Use short_name only directory format
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
# Chunk: docs/chunks/remove_sequence_prefix - Use short_name only directory format
# Chunk: docs/chunks/external_chunk_causal - Pass current tips to external.yaml
# Chunk: docs/chunks/consolidate_ext_refs - Use ExternalArtifactRef format
def create_task_chunk(
    task_dir: Path,
    short_name: str,
    ticket_id: str | None = None,
    status: str = "IMPLEMENTING",
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
    dependents = []
    project_refs = {}

    for project_ref in config.projects:
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
def get_current_task_chunk(task_dir: Path) -> str | None:
    """Get the current (IMPLEMENTING) chunk from external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        The chunk directory name if an IMPLEMENTING chunk exists, None otherwise.

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
    return chunks.get_current_chunk()


# Chunk: docs/chunks/task_aware_narrative_cmds - Task narrative error class
class TaskNarrativeError(Exception):
    """Error during task narrative creation with user-friendly message."""

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


# Chunk: docs/chunks/task_aware_narrative_cmds - Orchestrate multi-repo narrative
def create_task_narrative(
    task_dir: Path,
    short_name: str,
) -> dict:
    """Create narrative in task directory context.

    Orchestrates multi-repo narrative creation:
    1. Creates narrative in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external narrative's OVERVIEW.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the narrative

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
    dependents = []
    project_refs = {}

    for project_ref in config.projects:
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
    from artifact_ordering import ArtifactIndex

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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Task subsystem error class
class TaskSubsystemError(Exception):
    """Error during task subsystem creation with user-friendly message."""

    pass


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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Orchestrate multi-repo subsystem
def create_task_subsystem(
    task_dir: Path,
    short_name: str,
) -> dict:
    """Create subsystem in task directory context.

    Orchestrates multi-repo subsystem creation:
    1. Creates subsystem in external repo
    2. Creates external.yaml in each project with causal ordering
    3. Updates external subsystem's OVERVIEW.md with dependents

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        short_name: Short name for the subsystem

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
    dependents = []
    project_refs = {}

    for project_ref in config.projects:
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
