"""Sync external artifact references to match current repository state.

This module provides functionality for the `ve sync` command, which updates
`pinned` fields in external.yaml files to match the current HEAD of external
artifact repositories. Supports all workflow artifact types: chunks, narratives,
investigations, and subsystems.
"""
# Chunk: docs/chunks/ve_sync_command - Sync external references
# Chunk: docs/chunks/external_resolve - Use repo cache for single-repo mode
# Chunk: docs/chunks/consolidate_ext_ref_utils - Import from external_refs module
# Chunk: docs/chunks/sync_all_workflows - Extend sync to all workflow artifact types

from dataclasses import dataclass
from pathlib import Path

import yaml

import repo_cache
from external_refs import ARTIFACT_DIR_NAME, is_external_artifact, load_external_ref
from git_utils import get_current_sha
from models import ArtifactType
from task_utils import (
    is_task_directory,
    load_task_config,
    resolve_repo_directory,
    TaskChunkError,
)


@dataclass
class SyncResult:
    """Result of syncing a single external reference."""

    artifact_id: str
    artifact_type: ArtifactType
    old_sha: str
    new_sha: str
    updated: bool
    error: str | None = None

    @property
    def formatted_id(self) -> str:
        """Format artifact ID with type prefix (e.g., 'chunk:my_feature')."""
        return f"{self.artifact_type.value}:{self.artifact_id}"


def find_external_refs(
    project_path: Path,
    artifact_types: list[ArtifactType] | None = None,
) -> list[tuple[Path, ArtifactType]]:
    """Find all external.yaml files across workflow artifact directories.

    Searches for external references in all artifact type directories (chunks,
    narratives, investigations, subsystems) or a filtered subset.

    Args:
        project_path: Path to the project directory
        artifact_types: Optional list of artifact types to search. If None,
            searches all artifact types.

    Returns:
        List of tuples (external_yaml_path, artifact_type) for each external
        reference found.
    """
    # Default to all artifact types if not specified
    types_to_search = artifact_types if artifact_types is not None else list(ArtifactType)

    external_refs: list[tuple[Path, ArtifactType]] = []

    for artifact_type in types_to_search:
        dir_name = ARTIFACT_DIR_NAME[artifact_type]
        artifact_dir = project_path / "docs" / dir_name

        if not artifact_dir.exists():
            continue

        for item_dir in artifact_dir.iterdir():
            if item_dir.is_dir() and is_external_artifact(item_dir, artifact_type):
                external_yaml = item_dir / "external.yaml"
                if external_yaml.exists():
                    external_refs.append((external_yaml, artifact_type))

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
    artifact_filter: list[str] | None = None,
    artifact_types: list[ArtifactType] | None = None,
) -> list[SyncResult]:
    """Sync external references in task directory mode.

    Iterates all projects, finds external.yaml files across all workflow
    artifact types, resolves current SHA from external repo (local worktree),
    and updates pinned fields.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        dry_run: If True, report changes without modifying files
        project_filter: If provided, only sync specified projects
        artifact_filter: If provided, only sync specified artifact IDs
        artifact_types: If provided, only sync specified artifact types

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

        external_refs = find_external_refs(project_path, artifact_types=artifact_types)

        for external_yaml, artifact_type in external_refs:
            artifact_dir = external_yaml.parent
            artifact_id = artifact_dir.name

            # Apply artifact filter
            if artifact_filter and artifact_id not in artifact_filter:
                continue

            # Load current external ref
            try:
                ref = load_external_ref(artifact_dir)
            except Exception as e:
                results.append(
                    SyncResult(
                        artifact_id=f"{project_ref}:{artifact_id}",
                        artifact_type=artifact_type,
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
                            artifact_id=f"{project_ref}:{artifact_id}",
                            artifact_type=artifact_type,
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
                    artifact_id=f"{project_ref}:{artifact_id}",
                    artifact_type=artifact_type,
                    old_sha=old_sha,
                    new_sha=ref_sha,
                    updated=would_update,
                )
            )

    return results


def sync_single_repo(
    repo_path: Path,
    dry_run: bool = False,
    artifact_filter: list[str] | None = None,
    artifact_types: list[ArtifactType] | None = None,
) -> list[SyncResult]:
    """Sync external references in single repo mode.

    Finds external.yaml files across all workflow artifact types, uses repo
    cache to resolve current SHA from external repository, and updates pinned
    fields.

    Args:
        repo_path: Path to the repository
        dry_run: If True, report changes without modifying files
        artifact_filter: If provided, only sync specified artifact IDs
        artifact_types: If provided, only sync specified artifact types

    Returns:
        List of SyncResult for each external reference processed
    """
    results = []
    external_refs = find_external_refs(repo_path, artifact_types=artifact_types)

    for external_yaml, artifact_type in external_refs:
        artifact_dir = external_yaml.parent
        artifact_id = artifact_dir.name

        # Apply artifact filter
        if artifact_filter and artifact_id not in artifact_filter:
            continue

        # Load current external ref
        try:
            ref = load_external_ref(artifact_dir)
        except Exception as e:
            results.append(
                SyncResult(
                    artifact_id=artifact_id,
                    artifact_type=artifact_type,
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
                    artifact_id=artifact_id,
                    artifact_type=artifact_type,
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
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                old_sha=old_sha,
                new_sha=remote_sha,
                updated=would_update,
            )
        )

    return results
