"""Resolve external chunk references and retrieve their content.

This module provides functions to resolve external chunk references and
read their GOAL.md and PLAN.md content, supporting both task directory mode
(using local worktrees) and single repo mode (using the repo cache).
"""
# Chunk: docs/chunks/external_resolve - External chunk resolution

from dataclasses import dataclass
from pathlib import Path

import repo_cache
from git_utils import get_current_sha
from task_utils import (
    is_task_directory,
    load_task_config,
    load_external_ref,
    resolve_repo_directory,
    is_external_chunk,
    TaskChunkError,
)


@dataclass
class ResolveResult:
    """Result of resolving an external chunk."""

    repo: str
    external_chunk_id: str
    track: str
    resolved_sha: str
    goal_content: str | None
    plan_content: str | None


def find_chunk_in_project(project_path: Path, local_chunk_id: str) -> Path | None:
    """Find a chunk directory matching the local chunk ID in a project.

    Args:
        project_path: Path to the project directory
        local_chunk_id: Chunk ID pattern to match (e.g., "0001-feature" or "0001")

    Returns:
        Path to the matching chunk directory, or None if not found
    """
    chunks_dir = project_path / "docs" / "chunks"
    if not chunks_dir.exists():
        return None

    for chunk_dir in chunks_dir.iterdir():
        if chunk_dir.is_dir():
            # Match by exact name or by prefix (e.g., "0001" matches "0001-feature")
            if chunk_dir.name == local_chunk_id or chunk_dir.name.startswith(f"{local_chunk_id}-"):
                return chunk_dir

    return None


def resolve_task_directory(
    task_dir: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external chunk in task directory mode.

    Uses local worktrees to access external chunk content.

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
    # Parse project:chunk format if present
    if ":" in local_chunk_id:
        parts = local_chunk_id.split(":", 1)
        project_filter = parts[0]
        local_chunk_id = parts[1]

    config = load_task_config(task_dir)

    # Filter projects to search
    projects_to_search = config.projects
    if project_filter:
        # Match project filter against projects list
        matching = [p for p in config.projects if p == project_filter or p.endswith(f"/{project_filter}")]
        if not matching:
            raise TaskChunkError(f"Project '{project_filter}' not found in task configuration")
        projects_to_search = matching

    # Find matching chunk directories
    matches: list[tuple[str, Path]] = []

    for project_ref in projects_to_search:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            continue

        chunk_dir = find_chunk_in_project(project_path, local_chunk_id)
        if chunk_dir and chunk_dir.exists():
            matches.append((project_ref, chunk_dir))

    if not matches:
        raise TaskChunkError(f"Chunk '{local_chunk_id}' not found")

    if len(matches) > 1 and not project_filter:
        project_names = [m[0] for m in matches]
        raise TaskChunkError(
            f"Chunk '{local_chunk_id}' exists in multiple projects: {', '.join(project_names)}. "
            "Use --project to disambiguate."
        )

    project_ref, chunk_dir = matches[0]

    # Verify it's an external chunk
    if not is_external_chunk(chunk_dir):
        raise TaskChunkError(
            f"Chunk '{local_chunk_id}' is not an external reference (has GOAL.md instead of external.yaml)"
        )

    # Load external ref
    ref = load_external_ref(chunk_dir)

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, ref.repo)
    except FileNotFoundError as e:
        raise TaskChunkError(f"External repository '{ref.repo}' not found") from e

    # Determine SHA to use
    if at_pinned:
        if not ref.pinned:
            raise TaskChunkError(
                f"Cannot use --at-pinned: chunk '{local_chunk_id}' has no pinned SHA"
            )
        resolved_sha = ref.pinned
    else:
        # Use current HEAD of external repo
        try:
            resolved_sha = get_current_sha(external_repo_path)
        except ValueError as e:
            raise TaskChunkError(f"Failed to get current SHA from external repo: {e}") from e

    # Read content from external repo at the resolved SHA
    external_chunk_dir = external_repo_path / "docs" / "chunks" / ref.chunk

    if at_pinned:
        # Read at pinned SHA using git show
        goal_content = _read_file_at_sha(external_repo_path, resolved_sha, f"docs/chunks/{ref.chunk}/GOAL.md")
        plan_content = _read_file_at_sha(external_repo_path, resolved_sha, f"docs/chunks/{ref.chunk}/PLAN.md")
    else:
        # Read from working tree
        goal_path = external_chunk_dir / "GOAL.md"
        plan_path = external_chunk_dir / "PLAN.md"

        if not goal_path.exists():
            raise TaskChunkError(
                f"External chunk '{ref.chunk}' not found in repository '{ref.repo}'"
            )

        goal_content = goal_path.read_text()
        plan_content = plan_path.read_text() if plan_path.exists() else None

    return ResolveResult(
        repo=ref.repo,
        external_chunk_id=ref.chunk,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        goal_content=goal_content,
        plan_content=plan_content,
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


def resolve_single_repo(
    repo_path: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
) -> ResolveResult:
    """Resolve external chunk in single repo mode using cache.

    Uses the repo cache to clone/fetch the external repository and read content.

    Args:
        repo_path: Path to the local repository
        local_chunk_id: Local chunk ID (e.g., "0001-feature")
        at_pinned: If True, use pinned SHA instead of resolving track

    Returns:
        ResolveResult with resolved chunk information and content

    Raises:
        TaskChunkError: If chunk cannot be resolved
    """
    # Find chunk directory
    chunk_dir = find_chunk_in_project(repo_path, local_chunk_id)
    if not chunk_dir:
        raise TaskChunkError(f"Chunk '{local_chunk_id}' not found")

    # Verify it's an external chunk
    if not is_external_chunk(chunk_dir):
        raise TaskChunkError(
            f"Chunk '{local_chunk_id}' is not an external reference (has GOAL.md instead of external.yaml)"
        )

    # Load external ref
    ref = load_external_ref(chunk_dir)

    # Ensure repo is cached (this also fetches if already cached)
    try:
        repo_cache.ensure_cached(ref.repo)
    except ValueError as e:
        raise TaskChunkError(f"Failed to access external repository '{ref.repo}': {e}") from e

    # Determine SHA to use
    if at_pinned:
        if not ref.pinned:
            raise TaskChunkError(
                f"Cannot use --at-pinned: chunk '{local_chunk_id}' has no pinned SHA"
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
    goal_path = f"docs/chunks/{ref.chunk}/GOAL.md"
    plan_path = f"docs/chunks/{ref.chunk}/PLAN.md"

    try:
        goal_content = repo_cache.get_file_at_ref(ref.repo, resolved_sha, goal_path)
    except ValueError as e:
        raise TaskChunkError(
            f"External chunk '{ref.chunk}' not found in repository '{ref.repo}': {e}"
        ) from e

    try:
        plan_content = repo_cache.get_file_at_ref(ref.repo, resolved_sha, plan_path)
    except ValueError:
        plan_content = None

    return ResolveResult(
        repo=ref.repo,
        external_chunk_id=ref.chunk,
        track=ref.track or "main",
        resolved_sha=resolved_sha,
        goal_content=goal_content,
        plan_content=plan_content,
    )
