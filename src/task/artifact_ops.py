"""Generic artifact CRUD operations for task context.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module provides generic create/list/update operations for task artifacts,
replacing the duplicated type-specific implementations. The generic functions
are parameterized by ArtifactType and delegate to the appropriate manager class.
"""

import re

import yaml

from pathlib import Path

from artifact_ordering import ArtifactIndex
from chunks import Chunks
from external_refs import (
    is_external_artifact,
    create_external_yaml,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)
from models import ArtifactType

from task.config import (
    load_task_config,
    resolve_repo_directory,
)
from task.exceptions import (
    TaskChunkError,
    TaskNarrativeError,
    TaskInvestigationError,
    TaskSubsystemError,
    TaskArtifactListError,
)


def _get_manager_for_type(project_path: Path, artifact_type: ArtifactType):
    """Get the appropriate manager instance for an artifact type.

    Args:
        project_path: Path to the project directory.
        artifact_type: The artifact type.

    Returns:
        Manager instance (Chunks, Narratives, Investigations, or Subsystems).
    """
    if artifact_type == ArtifactType.CHUNK:
        return Chunks(project_path)
    elif artifact_type == ArtifactType.NARRATIVE:
        from narratives import Narratives
        return Narratives(project_path)
    elif artifact_type == ArtifactType.INVESTIGATION:
        from investigations import Investigations
        return Investigations(project_path)
    elif artifact_type == ArtifactType.SUBSYSTEM:
        from subsystems import Subsystems
        return Subsystems(project_path)
    else:
        raise ValueError(f"Unknown artifact type: {artifact_type}")


def _get_error_class_for_type(artifact_type: ArtifactType):
    """Get the appropriate error class for an artifact type.

    Args:
        artifact_type: The artifact type.

    Returns:
        Exception class for the artifact type.
    """
    if artifact_type == ArtifactType.CHUNK:
        return TaskChunkError
    elif artifact_type == ArtifactType.NARRATIVE:
        return TaskNarrativeError
    elif artifact_type == ArtifactType.INVESTIGATION:
        return TaskInvestigationError
    elif artifact_type == ArtifactType.SUBSYSTEM:
        return TaskSubsystemError
    else:
        return TaskArtifactListError


# Chunk: docs/chunks/artifact_promote - Generic helper to add dependents to any artifact type
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
    from frontmatter import update_frontmatter_field

    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        raise FileNotFoundError(f"{main_file} not found in {artifact_path}")

    update_frontmatter_field(main_path, "dependents", dependents)


# Chunk: docs/chunks/artifact_copy_backref - Append dependent entry with idempotency
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


# Chunk: docs/chunks/chunk_create_task_aware - Updates GOAL.md frontmatter with dependents
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
    add_dependents_to_artifact(chunk_path, ArtifactType.CHUNK, dependents)


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
    add_dependents_to_artifact(narrative_path, ArtifactType.NARRATIVE, dependents)


# Chunk: docs/chunks/task_aware_investigations - Helper to update investigation with dependents
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
    add_dependents_to_artifact(investigation_path, ArtifactType.INVESTIGATION, dependents)


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
    add_dependents_to_artifact(subsystem_path, ArtifactType.SUBSYSTEM, dependents)


# Chunk: docs/chunks/chunk_create_task_aware - Orchestrator for multi-repo chunk creation
# Chunk: docs/chunks/chunknaming_drop_ticket - Task context chunk creation without ticket in directory name
# Chunk: docs/chunks/coderef_format_prompting - Pass projects to chunk template in task context
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use ExternalArtifactRef format for dependents
# Chunk: docs/chunks/future_chunk_creation - Extended with status parameter for cross-repo chunk creation supporting FUTURE/IMPLEMENTING
# Chunk: docs/chunks/ordering_remove_seqno - Multi-repo chunk creation updated for short_name format
# Chunk: docs/chunks/selective_project_linking - Optional project filtering for task chunk creation
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


# Chunk: docs/chunks/selective_project_linking - Optional project filtering for task narrative creation
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


# Chunk: docs/chunks/selective_project_linking - Optional project filtering for task investigation creation
# Chunk: docs/chunks/task_aware_investigations - Task directory investigation creation
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


# Chunk: docs/chunks/selective_project_linking - Optional project filtering for task subsystem creation
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


# Chunk: docs/chunks/artifact_list_ordering - Updated for new list_chunks return type
# Chunk: docs/chunks/consolidate_ext_refs - Updated to handle ExternalArtifactRef objects
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


# Chunk: docs/chunks/task_aware_investigations - Lists investigations from external repo
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


# Chunk: docs/chunks/chunk_list_repo_source - Return tuple of (chunk_name, external_artifact_repo) for task context
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


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/chunk_create_task_aware - Calculates next sequential chunk ID for a project
# Chunk: docs/chunks/artifact_list_ordering - Updated to use enumerate_chunks for directory-based ID calculation
def get_next_chunk_id(project_path: Path) -> str:
    """Return next sequential chunk ID (e.g., '0005') for a project.

    DEPRECATED: This function is only needed for legacy external.yaml creation.
    New artifact creation uses short_name only without sequence prefixes.

    Args:
        project_path: Path to the project directory

    Returns:
        4-digit zero-padded string for the next chunk ID
    """
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
    from investigations import Investigations
    from narratives import Narratives
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
    from investigations import Investigations
    from narratives import Narratives
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
    # Chunk: docs/chunks/project_artifact_registry - Uses Project for unified manager access
    # Chunk: docs/chunks/chunks_class_decouple - Calls Project.list_proposed_chunks() directly
    from project import Project

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
    external_project = Project(external_repo_path)
    external_proposed = external_project.list_proposed_chunks()

    # Build project lists
    project_results = []
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            # Skip inaccessible projects
            continue

        # Collect proposed chunks from this project
        proj = Project(project_path)
        proj_proposed = proj.list_proposed_chunks()

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


# Chunk: docs/chunks/consolidate_ext_ref_utils - Convenience wrapper using is_external_artifact for chunks
def is_external_chunk(chunk_path: Path) -> bool:
    """Detect if chunk_path is an external chunk reference.

    An external chunk has external.yaml but no GOAL.md.

    Note: This is a convenience wrapper around is_external_artifact()
    for chunk-specific code.
    """
    return is_external_artifact(chunk_path, ArtifactType.CHUNK)


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
    from task.exceptions import TaskActivateError

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
