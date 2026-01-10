"""Sync external chunk references to match current repository state.

This module provides functionality for the `ve sync` command, which updates
`pinned` fields in external.yaml files to match the current HEAD of external
chunk repositories.
"""
# Chunk: docs/chunks/ve_sync_command - Sync external references
# Chunk: docs/chunks/external_resolve - Use repo cache for single-repo mode

from dataclasses import dataclass
from pathlib import Path

import yaml

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
class SyncResult:
    """Result of syncing a single external reference."""

    chunk_id: str
    old_sha: str
    new_sha: str
    updated: bool
    error: str | None = None


def find_external_refs(project_path: Path) -> list[Path]:
    """Find all external.yaml files in a project's docs/chunks directory.

    Args:
        project_path: Path to the project directory

    Returns:
        List of paths to external.yaml files
    """
    chunks_dir = project_path / "docs" / "chunks"
    if not chunks_dir.exists():
        return []

    external_refs = []
    for chunk_dir in chunks_dir.iterdir():
        if chunk_dir.is_dir() and is_external_chunk(chunk_dir):
            external_yaml = chunk_dir / "external.yaml"
            if external_yaml.exists():
                external_refs.append(external_yaml)

    return external_refs


def update_external_yaml(external_yaml_path: Path, new_sha: str) -> bool:
    """Update the pinned field in an external.yaml file.

    Args:
        external_yaml_path: Path to the external.yaml file
        new_sha: The new 40-character SHA to pin

    Returns:
        True if the file was modified, False if already current
    """
    with open(external_yaml_path) as f:
        data = yaml.safe_load(f)

    current_sha = data.get("pinned")
    if current_sha == new_sha:
        return False

    data["pinned"] = new_sha

    with open(external_yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return True


def sync_task_directory(
    task_dir: Path,
    dry_run: bool = False,
    project_filter: list[str] | None = None,
    chunk_filter: list[str] | None = None,
) -> list[SyncResult]:
    """Sync external references in task directory mode.

    Iterates all projects, finds external.yaml files, resolves current SHA
    from external chunk repo (local worktree), and updates pinned fields.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        dry_run: If True, report changes without modifying files
        project_filter: If provided, only sync specified projects
        chunk_filter: If provided, only sync specified chunk IDs

    Returns:
        List of SyncResult for each external reference processed
    """
    config = load_task_config(task_dir)
    results = []

    # Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_chunk_repo)
    except FileNotFoundError as e:
        raise TaskChunkError(
            f"External chunk repository '{config.external_chunk_repo}' not found"
        ) from e

    # Get current SHA from external repo
    try:
        current_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskChunkError(
            f"Failed to get SHA from external repository: {e}"
        ) from e

    # Filter projects if requested
    projects = config.projects
    if project_filter:
        projects = [p for p in projects if p in project_filter]

    # Process each project
    for project_ref in projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            # Skip projects that don't exist in task dir
            continue

        external_refs = find_external_refs(project_path)

        for external_yaml in external_refs:
            chunk_dir = external_yaml.parent
            chunk_id = chunk_dir.name

            # Apply chunk filter
            if chunk_filter and chunk_id not in chunk_filter:
                continue

            # Load current external ref
            try:
                ref = load_external_ref(chunk_dir)
            except Exception as e:
                results.append(
                    SyncResult(
                        chunk_id=f"{project_ref}:{chunk_id}",
                        old_sha="",
                        new_sha="",
                        updated=False,
                        error=str(e),
                    )
                )
                continue

            # Check if this ref points to our external repo
            # Note: In task directory mode, we only sync refs that point
            # to the configured external_chunk_repo
            if ref.repo != config.external_chunk_repo:
                # This external ref points elsewhere, try to resolve from local path
                try:
                    ref_repo_path = resolve_repo_directory(task_dir, ref.repo)
                    ref_sha = get_current_sha(ref_repo_path)
                except (FileNotFoundError, ValueError) as e:
                    results.append(
                        SyncResult(
                            chunk_id=f"{project_ref}:{chunk_id}",
                            old_sha=ref.pinned or "",
                            new_sha="",
                            updated=False,
                            error=f"Could not resolve repo '{ref.repo}': {e}",
                        )
                    )
                    continue
            else:
                ref_sha = current_sha

            old_sha = ref.pinned or ""
            would_update = old_sha != ref_sha

            if not dry_run and would_update:
                update_external_yaml(external_yaml, ref_sha)

            results.append(
                SyncResult(
                    chunk_id=f"{project_ref}:{chunk_id}",
                    old_sha=old_sha,
                    new_sha=ref_sha,
                    updated=would_update,
                )
            )

    return results


def sync_single_repo(
    repo_path: Path,
    dry_run: bool = False,
    chunk_filter: list[str] | None = None,
) -> list[SyncResult]:
    """Sync external references in single repo mode.

    Finds external.yaml files, uses repo cache to resolve current SHA
    from external repository, and updates pinned fields.

    Args:
        repo_path: Path to the repository
        dry_run: If True, report changes without modifying files
        chunk_filter: If provided, only sync specified chunk IDs

    Returns:
        List of SyncResult for each external reference processed
    """
    results = []
    external_refs = find_external_refs(repo_path)

    for external_yaml in external_refs:
        chunk_dir = external_yaml.parent
        chunk_id = chunk_dir.name

        # Apply chunk filter
        if chunk_filter and chunk_id not in chunk_filter:
            continue

        # Load current external ref
        try:
            ref = load_external_ref(chunk_dir)
        except Exception as e:
            results.append(
                SyncResult(
                    chunk_id=chunk_id,
                    old_sha="",
                    new_sha="",
                    updated=False,
                    error=str(e),
                )
            )
            continue

        # Resolve SHA using repo cache
        track = ref.track or "HEAD"
        try:
            remote_sha = repo_cache.resolve_ref(ref.repo, track)
        except ValueError as e:
            results.append(
                SyncResult(
                    chunk_id=chunk_id,
                    old_sha=ref.pinned or "",
                    new_sha="",
                    updated=False,
                    error=str(e),
                )
            )
            continue

        old_sha = ref.pinned or ""
        would_update = old_sha != remote_sha

        if not dry_run and would_update:
            update_external_yaml(external_yaml, remote_sha)

        results.append(
            SyncResult(
                chunk_id=chunk_id,
                old_sha=old_sha,
                new_sha=remote_sha,
                updated=would_update,
            )
        )

    return results
