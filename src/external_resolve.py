"""Resolve external artifact references and retrieve their content.

# Chunk: docs/chunks/external_resolve - External chunk resolution
# Chunk: docs/chunks/consolidate_ext_ref_utils - Import from external_refs module
# Chunk: docs/chunks/external_resolve_all_types - Extended to all artifact types

This module provides functions to resolve external artifact references and
read their content, supporting both task directory mode (using local worktrees)
and single repo mode (using the repo cache).

Supports all artifact types: chunks, narratives, investigations, and subsystems.
"""

from dataclasses import dataclass
from pathlib import Path

import repo_cache
from external_refs import (
    ARTIFACT_DIR_NAME,
    ARTIFACT_MAIN_FILE,
    detect_artifact_type_from_path,
    is_external_artifact,
    load_external_ref,
)
from git_utils import get_current_sha
from models import ArtifactType
from task_utils import (
    is_task_directory,
    load_task_config,
    resolve_repo_directory,
    TaskChunkError,
)


# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
@dataclass
class ResolveResult:
    """Result of resolving an external artifact reference."""

    repo: str
    artifact_type: ArtifactType
    artifact_id: str
    track: str
    resolved_sha: str
    main_content: str | None  # GOAL.md for chunks, OVERVIEW.md for others
    secondary_content: str | None  # PLAN.md for chunks, None for others


# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
def find_artifact_in_project(
    project_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
) -> Path | None:
    """Find an artifact directory matching the local artifact ID in a project.

    Args:
        project_path: Path to the project directory
        local_artifact_id: Artifact ID pattern to match (e.g., "0001-feature" or "0001")
        artifact_type: The type of artifact to find

    Returns:
        Path to the matching artifact directory, or None if not found
    """
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    artifacts_dir = project_path / "docs" / dir_name
    if not artifacts_dir.exists():
        return None

    for artifact_dir in artifacts_dir.iterdir():
        if artifact_dir.is_dir():
            # Match by exact name or by prefix (e.g., "0001" matches "0001-feature")
            if artifact_dir.name == local_artifact_id or artifact_dir.name.startswith(f"{local_artifact_id}-"):
                return artifact_dir

    return None


def find_chunk_in_project(project_path: Path, local_chunk_id: str) -> Path | None:
    """Find a chunk directory matching the local chunk ID in a project.

    This is a backward-compatible wrapper around find_artifact_in_project.

    Args:
        project_path: Path to the project directory
        local_chunk_id: Chunk ID pattern to match (e.g., "0001-feature" or "0001")

    Returns:
        Path to the matching chunk directory, or None if not found
    """
    return find_artifact_in_project(project_path, local_chunk_id, ArtifactType.CHUNK)


# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
def resolve_artifact_task_directory(
    task_dir: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
    at_pinned: bool = False,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external artifact in task directory mode.

    Uses local worktrees to access external artifact content.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        local_artifact_id: Local artifact ID or qualified project:artifact format
        artifact_type: The type of artifact to resolve
        at_pinned: If True, use pinned SHA instead of current HEAD
        project_filter: If provided, only look in this project

    Returns:
        ResolveResult with resolved artifact information and content

    Raises:
        TaskChunkError: If artifact cannot be resolved
    """
    artifact_type_name = artifact_type.value
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    dir_name = ARTIFACT_DIR_NAME[artifact_type]

    # Parse project:artifact format if present
    if ":" in local_artifact_id:
        parts = local_artifact_id.split(":", 1)
        project_filter = parts[0]
        local_artifact_id = parts[1]

    config = load_task_config(task_dir)

    # Filter projects to search
    projects_to_search = config.projects
    if project_filter:
        # Match project filter against projects list
        matching = [p for p in config.projects if p == project_filter or p.endswith(f"/{project_filter}")]
        if not matching:
            raise TaskChunkError(f"Project '{project_filter}' not found in task configuration")
        projects_to_search = matching

    # Find matching artifact directories
    matches: list[tuple[str, Path]] = []

    for project_ref in projects_to_search:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            continue

        artifact_dir = find_artifact_in_project(project_path, local_artifact_id, artifact_type)
        if artifact_dir and artifact_dir.exists():
            matches.append((project_ref, artifact_dir))

    if not matches:
        raise TaskChunkError(f"{artifact_type_name.capitalize()} '{local_artifact_id}' not found")

    if len(matches) > 1 and not project_filter:
        project_names = [m[0] for m in matches]
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{local_artifact_id}' exists in multiple projects: {', '.join(project_names)}. "
            "Use --project to disambiguate."
        )

    project_ref, artifact_dir = matches[0]

    # Verify it's an external artifact
    if not is_external_artifact(artifact_dir, artifact_type):
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{local_artifact_id}' is not an external reference (has {main_file} instead of external.yaml)"
        )

    # Load external ref
    ref = load_external_ref(artifact_dir)

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, ref.repo)
    except FileNotFoundError as e:
        raise TaskChunkError(f"External repository '{ref.repo}' not found") from e

    # Determine SHA to use
    if at_pinned:
        if not ref.pinned:
            raise TaskChunkError(
                f"Cannot use --at-pinned: {artifact_type_name} '{local_artifact_id}' has no pinned SHA"
            )
        resolved_sha = ref.pinned
    else:
        # Use current HEAD of external repo
        try:
            resolved_sha = get_current_sha(external_repo_path)
        except ValueError as e:
            raise TaskChunkError(f"Failed to get current SHA from external repo: {e}") from e

    # Read content from external repo at the resolved SHA
    external_artifact_dir = external_repo_path / "docs" / dir_name / ref.artifact_id

    # For chunks, we have both main (GOAL.md) and secondary (PLAN.md) files
    # For other artifact types, we only have the main file (OVERVIEW.md)
    secondary_file = "PLAN.md" if artifact_type == ArtifactType.CHUNK else None

    if at_pinned:
        # Read at pinned SHA using git show
        main_content = _read_file_at_sha(
            external_repo_path, resolved_sha, f"docs/{dir_name}/{ref.artifact_id}/{main_file}"
        )
        if secondary_file:
            secondary_content = _read_file_at_sha(
                external_repo_path, resolved_sha, f"docs/{dir_name}/{ref.artifact_id}/{secondary_file}"
            )
        else:
            secondary_content = None
    else:
        # Read from working tree
        main_path = external_artifact_dir / main_file

        if not main_path.exists():
            raise TaskChunkError(
                f"External {artifact_type_name} '{ref.artifact_id}' not found in repository '{ref.repo}'"
            )

        main_content = main_path.read_text()
        if secondary_file:
            secondary_path = external_artifact_dir / secondary_file
            secondary_content = secondary_path.read_text() if secondary_path.exists() else None
        else:
            secondary_content = None

    return ResolveResult(
        repo=ref.repo,
        artifact_type=artifact_type,
        artifact_id=ref.artifact_id,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        main_content=main_content,
        secondary_content=secondary_content,
    )


def resolve_task_directory(
    task_dir: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external chunk in task directory mode.

    This is a backward-compatible wrapper around resolve_artifact_task_directory.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        local_chunk_id: Local chunk ID or qualified project:chunk format
        at_pinned: If True, use pinned SHA instead of current HEAD
        project_filter: If provided, only look in this project

    Returns:
        ResolveResult with resolved chunk information and content

    Raises:
        TaskChunkError: If chunk cannot be resolved
    """
    return resolve_artifact_task_directory(
        task_dir=task_dir,
        local_artifact_id=local_chunk_id,
        artifact_type=ArtifactType.CHUNK,
        at_pinned=at_pinned,
        project_filter=project_filter,
    )


def _read_file_at_sha(repo_path: Path, sha: str, file_path: str) -> str | None:
    """Read a file at a specific SHA from a local git repository.

    Args:
        repo_path: Path to the git repository
        sha: The SHA to read from
        file_path: Path to the file within the repository

    Returns:
        The file content, or None if the file doesn't exist at that SHA
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "show", f"{sha}:{file_path}"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
def resolve_artifact_single_repo(
    repo_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
    at_pinned: bool = False,
) -> ResolveResult:
    """Resolve external artifact in single repo mode using cache.

    Uses the repo cache to clone/fetch the external repository and read content.

    Args:
        repo_path: Path to the local repository
        local_artifact_id: Local artifact ID (e.g., "0001-feature")
        artifact_type: The type of artifact to resolve
        at_pinned: If True, use pinned SHA instead of resolving track

    Returns:
        ResolveResult with resolved artifact information and content

    Raises:
        TaskChunkError: If artifact cannot be resolved
    """
    artifact_type_name = artifact_type.value
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    dir_name = ARTIFACT_DIR_NAME[artifact_type]

    # Find artifact directory
    artifact_dir = find_artifact_in_project(repo_path, local_artifact_id, artifact_type)
    if not artifact_dir:
        raise TaskChunkError(f"{artifact_type_name.capitalize()} '{local_artifact_id}' not found")

    # Verify it's an external artifact
    if not is_external_artifact(artifact_dir, artifact_type):
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{local_artifact_id}' is not an external reference (has {main_file} instead of external.yaml)"
        )

    # Load external ref
    ref = load_external_ref(artifact_dir)

    # Ensure repo is cached (this also fetches if already cached)
    try:
        repo_cache.ensure_cached(ref.repo)
    except ValueError as e:
        raise TaskChunkError(f"Failed to access external repository '{ref.repo}': {e}") from e

    # Determine SHA to use
    if at_pinned:
        if not ref.pinned:
            raise TaskChunkError(
                f"Cannot use --at-pinned: {artifact_type_name} '{local_artifact_id}' has no pinned SHA"
            )
        resolved_sha = ref.pinned
    else:
        # Resolve track to SHA via cache
        track = ref.track or "HEAD"
        try:
            resolved_sha = repo_cache.resolve_ref(ref.repo, track)
        except ValueError as e:
            raise TaskChunkError(f"Failed to resolve track '{track}': {e}") from e

    # Read content from cache
    # For chunks, we have both main (GOAL.md) and secondary (PLAN.md) files
    # For other artifact types, we only have the main file (OVERVIEW.md)
    main_path = f"docs/{dir_name}/{ref.artifact_id}/{main_file}"
    secondary_file = "PLAN.md" if artifact_type == ArtifactType.CHUNK else None

    try:
        main_content = repo_cache.get_file_at_ref(ref.repo, resolved_sha, main_path)
    except ValueError as e:
        raise TaskChunkError(
            f"External {artifact_type_name} '{ref.artifact_id}' not found in repository '{ref.repo}': {e}"
        ) from e

    if secondary_file:
        secondary_path = f"docs/{dir_name}/{ref.artifact_id}/{secondary_file}"
        try:
            secondary_content = repo_cache.get_file_at_ref(ref.repo, resolved_sha, secondary_path)
        except ValueError:
            secondary_content = None
    else:
        secondary_content = None

    return ResolveResult(
        repo=ref.repo,
        artifact_type=artifact_type,
        artifact_id=ref.artifact_id,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        main_content=main_content,
        secondary_content=secondary_content,
    )


def resolve_single_repo(
    repo_path: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
) -> ResolveResult:
    """Resolve external chunk in single repo mode using cache.

    This is a backward-compatible wrapper around resolve_artifact_single_repo.

    Args:
        repo_path: Path to the local repository
        local_chunk_id: Local chunk ID (e.g., "0001-feature")
        at_pinned: If True, use pinned SHA instead of resolving track

    Returns:
        ResolveResult with resolved chunk information and content

    Raises:
        TaskChunkError: If chunk cannot be resolved
    """
    return resolve_artifact_single_repo(
        repo_path=repo_path,
        local_artifact_id=local_chunk_id,
        artifact_type=ArtifactType.CHUNK,
        at_pinned=at_pinned,
    )
