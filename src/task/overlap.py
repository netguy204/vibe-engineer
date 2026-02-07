"""Overlap detection for task context.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module handles detecting overlapping code references across chunks
in task context, supporting project-qualified references.
"""

from dataclasses import dataclass
from pathlib import Path

from chunks import Chunks, ChunkStatus
from external_refs import is_external_artifact
from models import ArtifactType

from task.config import (
    load_task_config,
    resolve_repo_directory,
    resolve_project_qualified_ref,
)
from task.exceptions import TaskOverlapError


@dataclass
class TaskOverlapResult:
    """Result of task-aware overlap detection.

    Attributes:
        overlapping_chunks: List of (repo_ref, chunk_name) tuples for overlapping chunks.
                           repo_ref is the org/repo format or "external" for the external repo.
    """
    overlapping_chunks: list[tuple[str, str]]


def _is_external_chunk(chunk_path: Path) -> bool:
    """Check if a chunk path is an external reference."""
    return is_external_artifact(chunk_path, ArtifactType.CHUNK)


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
                if _is_external_chunk(project_path / "docs" / "chunks" / name):
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
