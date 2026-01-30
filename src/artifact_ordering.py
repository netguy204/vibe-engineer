"""Cached ordering system for workflow artifacts.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Subsystem: docs/subsystems/workflow_artifacts - Artifact ordering
# Chunk: docs/chunks/ordering_active_only - Status-aware tip filtering for created_after

This module provides the ArtifactIndex class which maintains ordered artifact
listings using directory enumeration for staleness detection and topological sorting.
Works in any directory without requiring git.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from external_refs import ARTIFACT_MAIN_FILE, ARTIFACT_DIR_NAME, is_external_artifact
from models import ArtifactType


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


# _ARTIFACT_MAIN_FILE is imported from external_refs as ARTIFACT_MAIN_FILE


def _enumerate_artifacts(artifact_dir: Path, artifact_type: ArtifactType) -> set[str]:
    """Enumerate artifact directory names.

    Args:
        artifact_dir: Directory containing artifact subdirectories.
        artifact_type: Type of artifact to determine main file name.

    Returns:
        Set of artifact directory names. Includes directories that have:
        - The required main file (e.g., GOAL.md or OVERVIEW.md), OR
        - external.yaml (external artifact reference)
    """
    if not artifact_dir.exists():
        return set()

    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    result = set()

    for item in artifact_dir.iterdir():
        if not item.is_dir():
            continue

        main_path = item / main_file

        if main_path.exists():
            # Local artifact
            result.add(item.name)
        elif is_external_artifact(item, artifact_type):
            # External artifact reference
            result.add(item.name)

    return result


# Regex to extract YAML frontmatter from markdown files
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(file_path: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a markdown file.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.

    Returns:
        Parsed frontmatter dict, or None if file doesn't exist,
        has no frontmatter, or invalid YAML.
    """
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text()
    except (OSError, IOError):
        return None

    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None


def _parse_created_after(file_path: Path) -> list[str]:
    """Parse the created_after field from a file's frontmatter.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.

    Returns:
        List of artifact names from created_after field.
        Returns empty list if file doesn't exist, has no frontmatter,
        invalid YAML, or missing created_after field.
    """
    frontmatter = _parse_frontmatter(file_path)
    if frontmatter is None:
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


def _parse_yaml_created_after(file_path: Path) -> list[str]:
    """Parse created_after from a plain YAML file (e.g., external.yaml).

    Args:
        file_path: Path to a plain YAML file (not markdown frontmatter).

    Returns:
        List of artifact names from created_after field.
        Returns empty list if file doesn't exist, has invalid YAML,
        or missing created_after field.
    """
    if not file_path.exists():
        return []

    try:
        data = yaml.safe_load(file_path.read_text())
        if not data:
            return []

        created_after = data.get("created_after", [])

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
    except (yaml.YAMLError, OSError):
        return []


def _parse_status(file_path: Path) -> str | None:
    """Parse the status field from a file's frontmatter.

    Args:
        file_path: Path to the markdown file with YAML frontmatter.

    Returns:
        Status string, or None if file doesn't exist, has no frontmatter,
        invalid YAML, or missing/invalid status field.
    """
    frontmatter = _parse_frontmatter(file_path)
    if frontmatter is None:
        return None

    status = frontmatter.get("status")
    if isinstance(status, str):
        return status

    return None


# _ARTIFACT_DIR_NAME is imported from external_refs as ARTIFACT_DIR_NAME

# Statuses that are considered "active" for tip detection purposes.
# None means no status filtering (all statuses are tip-eligible).
_TIP_ELIGIBLE_STATUSES: dict[ArtifactType, set[str] | None] = {
    ArtifactType.CHUNK: {"ACTIVE", "IMPLEMENTING", "EXTERNAL"},
    ArtifactType.NARRATIVE: {"ACTIVE"},
    ArtifactType.INVESTIGATION: None,  # No filtering - all statuses are tips
    ArtifactType.SUBSYSTEM: None,  # No filtering - all statuses are tips
}

# Index format version for compatibility checks
_INDEX_VERSION = 3


class ArtifactIndex:
    """Cached ordering system for workflow artifacts.

    Provides ordered artifact listings and tip identification using:
    - Directory enumeration for staleness detection (no git required)
    - Topological sort (Kahn's algorithm) for causal ordering
    - Fallback to sequence number order when created_after is empty

    The index is stored as JSON (.artifact-order.json) and automatically
    rebuilds when artifacts are added or removed. Since created_after is
    immutable after artifact creation, content changes don't require rebuild.
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
        return self._project_root / "docs" / ARTIFACT_DIR_NAME[artifact_type]

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
        """Check if the index is stale for the given artifact type.

        Staleness is determined by:
        1. Directory set changes (artifacts added or removed)
        2. File modification times (any artifact file newer than the index)
        """
        type_key = artifact_type.value
        type_index = index.get(type_key, {})

        if not type_index:
            return True

        if type_index.get("version") != _INDEX_VERSION:
            return True

        artifact_dir = self._get_artifact_dir(artifact_type)
        stored_directories = set(type_index.get("directories", []))
        current_directories = _enumerate_artifacts(artifact_dir, artifact_type)

        if stored_directories != current_directories:
            return True

        # Check if any artifact files are newer than the index
        index_mtime = self._index_file.stat().st_mtime if self._index_file.exists() else 0
        for artifact_name in current_directories:
            artifact_path = artifact_dir / artifact_name
            # Check GOAL.md / OVERVIEW.md
            goal_path = artifact_path / ARTIFACT_MAIN_FILE[artifact_type]
            if goal_path.exists() and goal_path.stat().st_mtime > index_mtime:
                return True
            # Check external.yaml for external artifacts
            external_path = artifact_path / "external.yaml"
            if external_path.exists() and external_path.stat().st_mtime > index_mtime:
                return True

        return False

    def _build_index_for_type(self, artifact_type: ArtifactType) -> dict[str, Any]:
        """Build index data for a specific artifact type."""
        artifact_dir = self._get_artifact_dir(artifact_type)
        artifacts = _enumerate_artifacts(artifact_dir, artifact_type)

        if not artifacts:
            return {
                "ordered": [],
                "tips": [],
                "directories": [],
                "version": _INDEX_VERSION,
            }

        main_file = ARTIFACT_MAIN_FILE[artifact_type]

        # Build dependency graph and collect statuses
        deps: dict[str, list[str]] = {}
        statuses: dict[str, str | None] = {}
        for artifact_name in artifacts:
            main_path = artifact_dir / artifact_name / main_file
            external_path = artifact_dir / artifact_name / "external.yaml"

            if main_path.exists():
                # Local artifact
                created_after = _parse_created_after(main_path)
                status = _parse_status(main_path)
            elif external_path.exists():
                # External chunk reference
                created_after = _parse_yaml_created_after(external_path)
                status = "EXTERNAL"  # Pseudo-status, always tip-eligible
            else:
                # Should not happen given _enumerate_artifacts logic
                created_after = []
                status = None

            deps[artifact_name] = created_after
            statuses[artifact_name] = status

        # Topological sort
        ordered = _topological_sort_multi_parent(deps)

        # Find tips with status filtering
        # Tips are artifacts that:
        # 1. Have a tip-eligible status (or status filtering is disabled for this type), AND
        # 2. Are not referenced by any other tip-eligible artifact
        eligible_statuses = _TIP_ELIGIBLE_STATUSES[artifact_type]

        # Determine which artifacts are tip-eligible
        if eligible_statuses is not None:
            tip_eligible_artifacts = {
                name for name, status in statuses.items()
                if status is not None and status in eligible_statuses
            }
        else:
            tip_eligible_artifacts = set(artifacts)

        # Collect artifacts referenced by tip-eligible artifacts
        # Only references from tip-eligible artifacts count for excluding tips
        referenced_by_eligible: set[str] = set()
        for artifact_name in tip_eligible_artifacts:
            referenced_by_eligible.update(deps.get(artifact_name, []))

        tips: list[str] = []
        for name in ordered:
            # Only tip-eligible artifacts can be tips
            if name not in tip_eligible_artifacts:
                continue

            # Skip artifacts that are referenced by tip-eligible artifacts
            if name in referenced_by_eligible:
                continue

            tips.append(name)

        return {
            "ordered": ordered,
            "tips": tips,
            "directories": sorted(artifacts),
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

    def get_ancestors(self, artifact_type: ArtifactType, artifact_name: str) -> set[str]:
        """Get all ancestors (artifacts created before) of the given artifact.

        Uses the causal ordering to compute transitive closure of created_after
        relationships. An artifact A is an ancestor of B if B depends on A
        directly or transitively.

        Args:
            artifact_type: Type of artifact.
            artifact_name: Name of the artifact to find ancestors for.

        Returns:
            Set of artifact directory names that are ancestors.
        """
        artifact_dir = self._get_artifact_dir(artifact_type)
        main_file = ARTIFACT_MAIN_FILE[artifact_type]

        # Build dependency graph
        artifacts = _enumerate_artifacts(artifact_dir, artifact_type)
        deps: dict[str, list[str]] = {}
        for name in artifacts:
            main_path = artifact_dir / name / main_file
            external_path = artifact_dir / name / "external.yaml"

            if main_path.exists():
                created_after = _parse_created_after(main_path)
            elif external_path.exists():
                created_after = _parse_yaml_created_after(external_path)
            else:
                created_after = []

            deps[name] = created_after

        if artifact_name not in deps:
            return set()

        # BFS to find all ancestors
        ancestors: set[str] = set()
        queue = list(deps[artifact_name])

        while queue:
            parent = queue.pop(0)
            if parent in ancestors:
                continue
            if parent in deps:  # Only add if it exists
                ancestors.add(parent)
                queue.extend(deps.get(parent, []))

        return ancestors
