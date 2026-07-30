"""Resolve external artifact references and retrieve their content.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/external_resolve - External chunk resolution infrastructure
# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
# Chunk: docs/chunks/external_resolve_enhance - Enhanced resolve with local path and directory listing
# Chunk: docs/chunks/external_artifact_unpin - Always resolve to HEAD
# Chunk: docs/chunks/federation_peer_refs - Peer (intra-workspace) resolution

This module provides functions to resolve external artifact references and
read their content, supporting three contexts:

- task directory mode (using local worktrees),
- single repo mode (using the repo cache), and
- peer mode, for `tree:` pointers at another VE tree in the same workspace.

Peer resolution is the existing mechanism minus its hardest parts: the target is
in the same working copy, so there is no clone to cache and no track to resolve
to a SHA - only a manifest lookup and a file read. Because a pointer's flavor is
recorded in the pointer itself, both entry points dispatch on it rather than
requiring callers to know which context they are in.

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
from models import ArtifactType, ExternalArtifactRef
from task import (
    is_task_directory,
    load_task_config,
    resolve_repo_directory,
    TaskChunkError,
)
from workspace import (
    WORKSPACE_MANIFEST_NAME,
    WorkspaceError,
    WorkspaceNotFoundError,
    load_workspace,
)

# Chunk: docs/chunks/federation_peer_refs - Context label for peer resolution
PEER_CONTEXT_MODE = "workspace_peer (same working copy)"


@dataclass
class ResolveResult:
    """Result of resolving an external artifact reference.

    `repo`/`track`/`resolved_sha` describe a cross-repository resolution and are
    None for peer references, which have no separate history to pin; `tree` and
    `why` describe a peer resolution and are None for cross-repo references.
    """

    repo: str | None
    artifact_type: ArtifactType
    artifact_id: str
    track: str | None
    resolved_sha: str | None
    main_content: str | None  # GOAL.md for chunks, OVERVIEW.md for others
    secondary_content: str | None  # PLAN.md for chunks, None for others
    local_path: Path | None = None  # Filesystem path to artifact directory
    directory_contents: list[str] | None = None  # Files in the artifact directory
    context_mode: str = "unknown"  # task_directory, single_repo, or workspace_peer
    tree: str | None = None  # Workspace member name, for peer references
    why: str | None = None  # The interest note recorded on the pointer

    # Chunk: docs/chunks/federation_peer_refs - Uniform target rendering
    @property
    def target_display(self) -> str:
        """The resolved target, formatted for human output."""
        if self.tree is not None:
            return f"tree:{self.tree}"
        return self.repo or "(no target)"


def find_artifact_in_project(
    project_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
) -> Path | None:
    """Find an artifact directory matching the local artifact ID in a project.

    Args:
        project_path: Path to the project directory
        local_artifact_id: Artifact ID to match (e.g., "feature_name")
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
            # Match by exact name
            if artifact_dir.name == local_artifact_id:
                return artifact_dir

    return None


# Chunk: docs/chunks/federation_peer_refs - Manifest-based resolution of a peer pointer
def resolve_peer_pointer(
    pointer_dir: Path,
    ref: ExternalArtifactRef,
    artifact_type: ArtifactType,
) -> ResolveResult:
    """Resolve a `tree:` pointer through the workspace manifest.

    The pointer directory - not the process's working directory - is the starting
    point for finding the manifest, so a pointer resolves the same way no matter
    where the command was run from. That is the whole defect this addresses: a
    reference must not mean different things from different directories.

    Args:
        pointer_dir: The artifact directory holding the external.yaml.
        ref: The loaded reference (must carry `tree`).
        artifact_type: The type of artifact being resolved.

    Returns:
        ResolveResult describing the artifact in the member's tree.

    Raises:
        TaskChunkError: If the workspace, the member, or the artifact is missing.
    """
    artifact_type_name = artifact_type.value
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    dir_name = ARTIFACT_DIR_NAME[artifact_type]

    try:
        ws = load_workspace(pointer_dir)
    except WorkspaceNotFoundError as e:
        raise TaskChunkError(
            f"'{pointer_dir}' points at tree '{ref.tree}', but no "
            f"{WORKSPACE_MANIFEST_NAME} exists at or above it, so there is no "
            f"registry to resolve member names against. Run `ve workspace init` "
            f"at the root of the repository holding your VE trees, then "
            f"`ve workspace add {ref.tree} <path>`. ({e})"
        ) from e
    except WorkspaceError as e:
        raise TaskChunkError(f"Workspace manifest is unusable: {e}") from e

    try:
        member_root = ws.resolve(ref.tree)
    except KeyError as e:
        # Workspace.resolve's message already lists the registered members.
        raise TaskChunkError(
            f"'{pointer_dir}' points at tree '{ref.tree}', which is not "
            f"registered: {e.args[0]}"
        ) from e

    external_artifact_dir = member_root / "docs" / dir_name / ref.artifact_id

    if not external_artifact_dir.is_dir():
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{ref.artifact_id}' does not exist "
            f"in tree '{ref.tree}': expected {external_artifact_dir}. Either the "
            f"artifact was renamed or removed, or this pointer was never resolvable "
            f"(check the target with `ve {artifact_type_name} list --project-dir "
            f"{member_root}`)"
        )

    main_path = external_artifact_dir / main_file
    if not main_path.exists():
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} directory '{external_artifact_dir}' "
            f"exists in tree '{ref.tree}' but has no {main_file}, so it carries no "
            f"content to resolve to"
        )

    secondary_file = "PLAN.md" if artifact_type == ArtifactType.CHUNK else None
    main_content = main_path.read_text()
    if secondary_file:
        secondary_path = external_artifact_dir / secondary_file
        secondary_content = secondary_path.read_text() if secondary_path.exists() else None
    else:
        secondary_content = None

    return ResolveResult(
        repo=None,
        artifact_type=artifact_type,
        artifact_id=ref.artifact_id,
        track=None,
        resolved_sha=None,
        main_content=main_content,
        secondary_content=secondary_content,
        local_path=external_artifact_dir,
        directory_contents=sorted(
            f.name for f in external_artifact_dir.iterdir() if f.is_file()
        ),
        context_mode=PEER_CONTEXT_MODE,
        tree=ref.tree,
        why=ref.why,
    )


# Chunk: docs/chunks/federation_peer_refs - Peer resolution entry point
def resolve_artifact_peer(
    project_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
) -> ResolveResult:
    """Resolve a peer artifact reference in `project_path` via the workspace manifest.

    Args:
        project_path: Path to the tree containing the pointer.
        local_artifact_id: Local pointer directory name.
        artifact_type: The type of artifact to resolve.

    Returns:
        ResolveResult with the target artifact's content.

    Raises:
        TaskChunkError: If the pointer is missing, is not external, is not a peer
            reference, or cannot be resolved.
    """
    artifact_type_name = artifact_type.value
    main_file = ARTIFACT_MAIN_FILE[artifact_type]

    artifact_dir = find_artifact_in_project(project_path, local_artifact_id, artifact_type)
    if not artifact_dir:
        raise TaskChunkError(f"{artifact_type_name.capitalize()} '{local_artifact_id}' not found")

    if not is_external_artifact(artifact_dir, artifact_type):
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{local_artifact_id}' is not an external "
            f"reference (has {main_file} instead of external.yaml)"
        )

    ref = load_external_ref(artifact_dir)
    if not ref.is_peer:
        raise TaskChunkError(
            f"{artifact_type_name.capitalize()} '{local_artifact_id}' is a cross-repository "
            f"reference to '{ref.repo}', not a peer reference to a workspace member"
        )

    return resolve_peer_pointer(artifact_dir, ref, artifact_type)


def find_chunk_in_project(project_path: Path, local_chunk_id: str) -> Path | None:
    """Find a chunk directory matching the local chunk ID in a project.

    This is a backward-compatible wrapper around find_artifact_in_project.

    Args:
        project_path: Path to the project directory
        local_chunk_id: Chunk ID to match (e.g., "feature_name")

    Returns:
        Path to the matching chunk directory, or None if not found
    """
    return find_artifact_in_project(project_path, local_chunk_id, ArtifactType.CHUNK)


def resolve_artifact_task_directory(
    task_dir: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external artifact in task directory mode.

    Uses local worktrees to access external artifact content.
    Always resolves to current HEAD of the external repository.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        local_artifact_id: Local artifact ID or qualified project:artifact format
        artifact_type: The type of artifact to resolve
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

    # Chunk: docs/chunks/federation_peer_refs - Peer pointers resolve inside their own workspace
    # A `tree:` pointer inside a task project addresses that project's workspace,
    # not the task's external artifact repo, so it never reaches the repo logic.
    if ref.is_peer:
        return resolve_peer_pointer(artifact_dir, ref, artifact_type)

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, ref.repo)
    except FileNotFoundError as e:
        raise TaskChunkError(f"External repository '{ref.repo}' not found") from e

    # Always use current HEAD of external repo
    try:
        resolved_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskChunkError(f"Failed to get current SHA from external repo: {e}") from e

    # Read content from external repo working tree
    external_artifact_dir = external_repo_path / "docs" / dir_name / ref.artifact_id

    # For chunks, we have both main (GOAL.md) and secondary (PLAN.md) files
    # For other artifact types, we only have the main file (OVERVIEW.md)
    secondary_file = "PLAN.md" if artifact_type == ArtifactType.CHUNK else None

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

    # Get local path and directory contents from the worktree
    # Note: We read directly from the worktree, which may have uncommitted changes
    # This is intentional - the worktree is the user's source of truth in task mode
    local_path = external_artifact_dir
    directory_contents = sorted([f.name for f in external_artifact_dir.iterdir() if f.is_file()])

    return ResolveResult(
        repo=ref.repo,
        artifact_type=artifact_type,
        artifact_id=ref.artifact_id,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        main_content=main_content,
        secondary_content=secondary_content,
        local_path=local_path,
        directory_contents=directory_contents,
        context_mode="task_directory",
    )


def resolve_task_directory(
    task_dir: Path,
    local_chunk_id: str,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external chunk in task directory mode.

    This is a backward-compatible wrapper around resolve_artifact_task_directory.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        local_chunk_id: Local chunk ID or qualified project:chunk format
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
        project_filter=project_filter,
    )


def resolve_artifact_single_repo(
    repo_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
) -> ResolveResult:
    """Resolve external artifact in single repo mode using cache.

    Uses the repo cache to clone/fetch the external repository and read content.
    Always resolves to the tracked branch (or HEAD if no track specified).

    Args:
        repo_path: Path to the local repository
        local_artifact_id: Local artifact ID (e.g., "feature_name")
        artifact_type: The type of artifact to resolve

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

    # Chunk: docs/chunks/federation_peer_refs - Peer pointers never touch the repo cache
    if ref.is_peer:
        return resolve_peer_pointer(artifact_dir, ref, artifact_type)

    # Ensure repo is cached (this also fetches if already cached)
    try:
        repo_cache.ensure_cached(ref.repo)
    except ValueError as e:
        raise TaskChunkError(f"Failed to access external repository '{ref.repo}': {e}") from e

    # Resolve track to SHA via cache (always use HEAD/track, never pinned)
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

    # Get local path from cache and list directory contents from working tree
    # Note: ensure_cached() already did fetch+reset, so working tree reflects origin/HEAD
    cache_path = repo_cache.get_repo_path(ref.repo)
    local_path = cache_path / "docs" / dir_name / ref.artifact_id

    # List directory contents from the working tree
    # Since ensure_cached() already reset to origin/HEAD, this is guaranteed to be current
    if local_path.exists():
        directory_contents = sorted([f.name for f in local_path.iterdir() if f.is_file()])
    else:
        directory_contents = []

    return ResolveResult(
        repo=ref.repo,
        artifact_type=artifact_type,
        artifact_id=ref.artifact_id,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        main_content=main_content,
        secondary_content=secondary_content,
        local_path=local_path,
        directory_contents=directory_contents,
        context_mode="single_repo (via cache)",
    )


def resolve_single_repo(
    repo_path: Path,
    local_chunk_id: str,
) -> ResolveResult:
    """Resolve external chunk in single repo mode using cache.

    This is a backward-compatible wrapper around resolve_artifact_single_repo.

    Args:
        repo_path: Path to the local repository
        local_chunk_id: Local chunk ID (e.g., "feature_name")

    Returns:
        ResolveResult with resolved chunk information and content

    Raises:
        TaskChunkError: If chunk cannot be resolved
    """
    return resolve_artifact_single_repo(
        repo_path=repo_path,
        local_artifact_id=local_chunk_id,
        artifact_type=ArtifactType.CHUNK,
    )
