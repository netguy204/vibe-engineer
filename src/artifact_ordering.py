"""Cached ordering system for workflow artifacts.

# Chunk: docs/chunks/0038-artifact_ordering_index - Causal ordering infrastructure
# Subsystem: docs/subsystems/0002-workflow_artifacts - Artifact ordering

This module provides the ArtifactIndex class which maintains ordered artifact
listings using git-hash-based staleness detection and topological sorting.
"""

import json
import re
import subprocess
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


def _topological_sort_multi_parent(deps: dict[str, list[str]]) -> list[str]:
    """Topological sort with multi-parent support using Kahn's algorithm.

    Args:
        deps: Mapping of artifact_name -> list of parent artifact names (created_after).

    Returns:
        List of artifact names in causal order (oldest first).
        Missing parents (referenced but not in deps) are not included in output.
    """
    if not deps:
        return []

    # Build in-degree count and reverse adjacency (children mapping)
    in_degree: dict[str, int] = defaultdict(int)
    children: dict[str, list[str]] = defaultdict(list)
    all_nodes = set(deps.keys())

    for artifact, parents in deps.items():
        in_degree[artifact] = len(parents)
        for parent in parents:
            children[parent].append(artifact)
            all_nodes.add(parent)

    # Find roots (nodes with no parents)
    roots = [n for n in all_nodes if in_degree[n] == 0]

    # Kahn's algorithm with sorted queue for determinism
    result: list[str] = []
    queue = sorted(roots)

    while queue:
        node = queue.pop(0)
        # Only include actual artifacts, not missing parents
        if node in deps:
            result.append(node)
        for child in sorted(children[node]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    return result


class ArtifactType(StrEnum):
    """Types of workflow artifacts that can be ordered."""

    CHUNK = "chunk"
    NARRATIVE = "narrative"
    INVESTIGATION = "investigation"
    SUBSYSTEM = "subsystem"


# Map artifact type to the file that defines ordering (GOAL.md or OVERVIEW.md)
_ARTIFACT_MAIN_FILE: dict[ArtifactType, str] = {
    ArtifactType.CHUNK: "GOAL.md",
    ArtifactType.NARRATIVE: "OVERVIEW.md",
    ArtifactType.INVESTIGATION: "OVERVIEW.md",
    ArtifactType.SUBSYSTEM: "OVERVIEW.md",
}


def _get_git_hash(file_path: Path) -> str | None:
    """Get the git blob hash for a file.

    Returns the hash of the file's current content (working tree),
    or None if git is not available or file does not exist.

    Args:
        file_path: Path to the file to hash.

    Returns:
        40-character hex hash string, or None on failure.
    """
    if not file_path.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "hash-object", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _get_all_artifact_hashes(
    artifact_dir: Path, artifact_type: ArtifactType
) -> dict[str, str]:
    """Get git hashes for all main files in artifact directories.

    Uses a single batched git command for efficiency.

    Args:
        artifact_dir: Directory containing artifact subdirectories.
        artifact_type: Type of artifact to determine main file name.

    Returns:
        Dict mapping artifact directory name to git hash.
    """
    if not artifact_dir.exists():
        return {}

    main_file = _ARTIFACT_MAIN_FILE[artifact_type]
    artifacts: list[tuple[str, Path]] = []

    for item in artifact_dir.iterdir():
        if item.is_dir():
            main_path = item / main_file
            if main_path.exists():
                artifacts.append((item.name, main_path))

    if not artifacts:
        return {}

    # Sort for deterministic ordering
    artifacts.sort(key=lambda x: x[0])

    # Hash all files in one git command
    files = [str(path) for _, path in artifacts]
    try:
        result = subprocess.run(
            ["git", "hash-object", "--"] + files,
            capture_output=True,
            text=True,
            check=True,
        )
        hashes = result.stdout.strip().split("\n")
        return {name: h for (name, _), h in zip(artifacts, hashes)}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}


# Regex to extract YAML frontmatter from markdown files
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _parse_created_after(file_path: Path) -> list[str]:
    """Parse the created_after field from a file's frontmatter.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.

    Returns:
        List of artifact names from created_after field.
        Returns empty list if file doesn't exist, has no frontmatter,
        invalid YAML, or missing created_after field.
    """
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text()
    except (OSError, IOError):
        return []

    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return []

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return []

    created_after = frontmatter.get("created_after", [])

    # Handle null/None
    if created_after is None:
        return []

    # Handle legacy single string format
    if isinstance(created_after, str):
        return [created_after]

    # Should be a list
    if isinstance(created_after, list):
        return created_after

    return []


# Map artifact type to its directory name under docs/
_ARTIFACT_DIR_NAME: dict[ArtifactType, str] = {
    ArtifactType.CHUNK: "chunks",
    ArtifactType.NARRATIVE: "narratives",
    ArtifactType.INVESTIGATION: "investigations",
    ArtifactType.SUBSYSTEM: "subsystems",
}

# Index format version for compatibility checks
_INDEX_VERSION = 1


class ArtifactIndex:
    """Cached ordering system for workflow artifacts.

    Provides ordered artifact listings and tip identification using:
    - Git blob hashes for staleness detection
    - Topological sort (Kahn's algorithm) for causal ordering
    - Fallback to sequence number order when created_after is empty

    The index is stored as gitignored JSON (.artifact-order.json) and
    automatically rebuilds when artifacts change.
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize the artifact index.

        Args:
            project_root: Root directory of the project. If None, uses cwd.
        """
        self._project_root = project_root or Path.cwd()
        self._index_file = self._project_root / ".artifact-order.json"
        self._cache: dict[str, Any] | None = None

    def _get_artifact_dir(self, artifact_type: ArtifactType) -> Path:
        """Get the directory path for an artifact type."""
        return self._project_root / "docs" / _ARTIFACT_DIR_NAME[artifact_type]

    def _load_index(self) -> dict[str, Any]:
        """Load the index from disk."""
        if not self._index_file.exists():
            return {}
        try:
            return json.loads(self._index_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, index: dict[str, Any]) -> None:
        """Save the index to disk."""
        self._index_file.write_text(json.dumps(index, indent=2))

    def _is_index_stale(
        self, index: dict[str, Any], artifact_type: ArtifactType
    ) -> bool:
        """Check if the index is stale for the given artifact type."""
        type_key = artifact_type.value
        type_index = index.get(type_key, {})

        if not type_index:
            return True

        if type_index.get("version") != _INDEX_VERSION:
            return True

        artifact_dir = self._get_artifact_dir(artifact_type)
        if not artifact_dir.exists():
            # No artifacts exist; stale if index has any
            return bool(type_index.get("hashes"))

        # Get current artifact set
        main_file = _ARTIFACT_MAIN_FILE[artifact_type]
        current_artifacts = {
            item.name
            for item in artifact_dir.iterdir()
            if item.is_dir() and (item / main_file).exists()
        }

        indexed_artifacts = set(type_index.get("hashes", {}).keys())

        # New or deleted artifacts
        if current_artifacts != indexed_artifacts:
            return True

        # Get current hashes
        current_hashes = _get_all_artifact_hashes(artifact_dir, artifact_type)

        # Check for modified artifacts
        for artifact_name, indexed_hash in type_index.get("hashes", {}).items():
            current_hash = current_hashes.get(artifact_name)
            if current_hash != indexed_hash:
                return True

        return False

    def _build_index_for_type(self, artifact_type: ArtifactType) -> dict[str, Any]:
        """Build index data for a specific artifact type."""
        artifact_dir = self._get_artifact_dir(artifact_type)

        if not artifact_dir.exists():
            return {
                "ordered": [],
                "tips": [],
                "hashes": {},
                "version": _INDEX_VERSION,
            }

        main_file = _ARTIFACT_MAIN_FILE[artifact_type]

        # Get all artifact directories
        artifacts = [
            item.name
            for item in artifact_dir.iterdir()
            if item.is_dir() and (item / main_file).exists()
        ]

        if not artifacts:
            return {
                "ordered": [],
                "tips": [],
                "hashes": {},
                "version": _INDEX_VERSION,
            }

        # Get hashes
        hashes = _get_all_artifact_hashes(artifact_dir, artifact_type)

        # Build dependency graph
        deps: dict[str, list[str]] = {}
        for artifact_name in artifacts:
            main_path = artifact_dir / artifact_name / main_file
            created_after = _parse_created_after(main_path)
            deps[artifact_name] = created_after

        # Topological sort
        ordered = _topological_sort_multi_parent(deps)

        # Find tips (artifacts not referenced in any created_after)
        all_parents: set[str] = set()
        for parents in deps.values():
            all_parents.update(parents)
        tips = [name for name in ordered if name not in all_parents]

        return {
            "ordered": ordered,
            "tips": tips,
            "hashes": hashes,
            "version": _INDEX_VERSION,
        }

    def _ensure_index_fresh(self, artifact_type: ArtifactType) -> dict[str, Any]:
        """Ensure index is fresh and return the type-specific data."""
        if self._cache is None:
            self._cache = self._load_index()

        if self._is_index_stale(self._cache, artifact_type):
            type_index = self._build_index_for_type(artifact_type)
            self._cache[artifact_type.value] = type_index
            self._save_index(self._cache)

        return self._cache.get(artifact_type.value, {})

    def get_ordered(self, artifact_type: ArtifactType) -> list[str]:
        """Get artifact names in causal order (oldest first).

        Args:
            artifact_type: Type of artifacts to list.

        Returns:
            List of artifact directory names in topological order.
            Falls back to sequence number order if created_after is not populated.
        """
        type_index = self._ensure_index_fresh(artifact_type)
        return type_index.get("ordered", [])

    def find_tips(self, artifact_type: ArtifactType) -> list[str]:
        """Find artifacts that have no dependents.

        Tips are artifacts that are not referenced in any other artifact's
        created_after field. These represent the current frontiers of work.

        Args:
            artifact_type: Type of artifacts to search.

        Returns:
            List of artifact directory names that are tips.
        """
        type_index = self._ensure_index_fresh(artifact_type)
        return type_index.get("tips", [])

    def rebuild(self, artifact_type: ArtifactType | None = None) -> None:
        """Force rebuild of the index.

        Args:
            artifact_type: Type to rebuild, or None to rebuild all types.
        """
        if self._cache is None:
            self._cache = self._load_index()

        if artifact_type is not None:
            type_index = self._build_index_for_type(artifact_type)
            self._cache[artifact_type.value] = type_index
        else:
            for atype in ArtifactType:
                type_index = self._build_index_for_type(atype)
                self._cache[atype.value] = type_index

        self._save_index(self._cache)
