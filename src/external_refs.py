"""External artifact reference utilities.

# Chunk: docs/chunks/consolidate_ext_ref_utils - External reference consolidation
# Chunk: docs/chunks/external_chunk_causal - created_after parameter for causal ordering
# Subsystem: docs/subsystems/workflow_artifacts - External reference utilities

This module provides type-agnostic utilities for working with external artifact
references across all workflow artifact types (chunks, narratives, investigations,
subsystems).
"""

from pathlib import Path

import yaml

from models import ArtifactType, ExternalArtifactRef


# Map artifact type to the main document file
ARTIFACT_MAIN_FILE: dict[ArtifactType, str] = {
    ArtifactType.CHUNK: "GOAL.md",
    ArtifactType.NARRATIVE: "OVERVIEW.md",
    ArtifactType.INVESTIGATION: "OVERVIEW.md",
    ArtifactType.SUBSYSTEM: "OVERVIEW.md",
}

# Map artifact type to its directory name under docs/
ARTIFACT_DIR_NAME: dict[ArtifactType, str] = {
    ArtifactType.CHUNK: "chunks",
    ArtifactType.NARRATIVE: "narratives",
    ArtifactType.INVESTIGATION: "investigations",
    ArtifactType.SUBSYSTEM: "subsystems",
}


def get_main_file_for_type(artifact_type: ArtifactType) -> str:
    """Get the main document file name for an artifact type.

    Args:
        artifact_type: The type of artifact.

    Returns:
        The main file name (e.g., "GOAL.md" for chunks, "OVERVIEW.md" for others).
    """
    return ARTIFACT_MAIN_FILE[artifact_type]


def is_external_artifact(path: Path, artifact_type: ArtifactType) -> bool:
    """Detect if path is an external artifact reference.

    An external artifact has external.yaml but not the main document
    (GOAL.md for chunks, OVERVIEW.md for others).

    Args:
        path: Path to the artifact directory.
        artifact_type: The type of artifact to check.

    Returns:
        True if the path contains an external reference, False otherwise.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    has_external = (path / "external.yaml").exists()
    has_main = (path / main_file).exists()
    return has_external and not has_main


def detect_artifact_type_from_path(path: Path) -> ArtifactType:
    """Detect artifact type from directory path.

    Args:
        path: Path to an artifact directory (e.g., docs/chunks/my_feature).

    Returns:
        The detected ArtifactType.

    Raises:
        ValueError: If the path is not under a recognized artifact directory.
    """
    # Normalize path and check parts
    parts = path.parts

    # Look for the artifact type directory in the path
    for i, part in enumerate(parts):
        if part == "docs" and i + 1 < len(parts):
            type_dir = parts[i + 1]

            # Reverse lookup: find artifact type by directory name
            for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
                if dir_name == type_dir:
                    return artifact_type

    raise ValueError(
        f"Cannot detect artifact type from path: {path}. "
        f"Path must be under docs/chunks/, docs/narratives/, "
        f"docs/investigations/, or docs/subsystems/"
    )


# Chunk: docs/chunks/consolidate_ext_refs - Updated to return ExternalArtifactRef
def load_external_ref(path: Path) -> ExternalArtifactRef:
    """Load and validate external.yaml from artifact path.

    Args:
        path: Directory containing external.yaml.

    Returns:
        Validated ExternalArtifactRef.

    Raises:
        FileNotFoundError: If external.yaml doesn't exist.
        ValidationError: If YAML content is invalid.
    """
    ref_file = path / "external.yaml"
    if not ref_file.exists():
        raise FileNotFoundError(f"external.yaml not found in {path}")

    with open(ref_file) as f:
        data = yaml.safe_load(f)

    return ExternalArtifactRef.model_validate(data)


# Chunk: docs/chunks/chunk_create_task_aware - Original implementation in task_utils.py
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use artifact_type and artifact_id fields
# Chunk: docs/chunks/external_chunk_causal - created_after parameter for causal ordering
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible artifact path normalization
def normalize_artifact_path(
    input_path: str,
    search_path: Path | None = None,
    external_repo_name: str | None = None,
) -> tuple[ArtifactType, str]:
    """Normalize flexible artifact path to (type, artifact_id).

    Accepts any reasonable path format and returns the canonical tuple of
    artifact type and artifact ID.

    Args:
        input_path: User-provided path in any supported format.
        search_path: Project path to search when input is just an artifact name.
        external_repo_name: External repo directory name to strip if present.

    Returns:
        Tuple of (ArtifactType, artifact_id).

    Raises:
        ValueError: If artifact cannot be found, path is ambiguous, or absolute.

    Supported input formats:
        1. architecture/docs/chunks/foo -> strips leading directory, returns (CHUNK, "foo")
        2. docs/chunks/foo -> standard format, returns (CHUNK, "foo")
        3. chunks/foo -> infers docs/, returns (CHUNK, "foo")
        4. foo -> searches for artifact, returns (detected_type, "foo") or raises error
        5. docs/chunks/foo/ -> strips trailing slash
    """
    # Reject absolute paths
    if input_path.startswith("/"):
        raise ValueError(
            f"Absolute paths are not supported: {input_path}. "
            f"Use a relative path like 'docs/chunks/artifact_name'."
        )

    # Strip trailing slashes
    input_path = input_path.rstrip("/")

    # Split into parts
    parts = input_path.split("/")

    # If first part matches external_repo_name, strip it
    if external_repo_name and parts and parts[0] == external_repo_name:
        parts = parts[1:]

    # Build reverse lookup: directory name -> ArtifactType
    dir_to_type = {v: k for k, v in ARTIFACT_DIR_NAME.items()}

    # Check for docs/{type}/ pattern
    if len(parts) >= 3 and parts[0] == "docs" and parts[1] in dir_to_type:
        artifact_type = dir_to_type[parts[1]]
        artifact_id = parts[2]  # The artifact directory name
        return (artifact_type, artifact_id)

    # Check for {type}/ pattern (without docs)
    if len(parts) >= 2 and parts[0] in dir_to_type:
        artifact_type = dir_to_type[parts[0]]
        artifact_id = parts[1]  # The artifact directory name
        return (artifact_type, artifact_id)

    # If just an artifact name, search search_path for a match
    if len(parts) == 1:
        artifact_name = parts[0]

        if search_path is None:
            raise ValueError(
                f"Cannot resolve artifact '{artifact_name}' without a search path. "
                f"Use a full path like 'docs/chunks/{artifact_name}' or "
                f"'docs/investigations/{artifact_name}'."
            )

        # Search all artifact directories
        found: list[tuple[ArtifactType, str]] = []
        for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
            artifact_dir = search_path / "docs" / dir_name / artifact_name
            if artifact_dir.exists() and artifact_dir.is_dir():
                found.append((artifact_type, artifact_name))

        if len(found) == 0:
            # List available artifact types for the error message
            type_dirs = ", ".join(ARTIFACT_DIR_NAME.values())
            raise ValueError(
                f"Artifact '{artifact_name}' not found in {search_path}. "
                f"Searched in: {type_dirs}"
            )

        if len(found) > 1:
            # Ambiguous - exists in multiple directories
            locations = [f"docs/{ARTIFACT_DIR_NAME[t]}/{name}" for t, name in found]
            raise ValueError(
                f"Artifact '{artifact_name}' is ambiguous. "
                f"Found in multiple locations: {', '.join(locations)}. "
                f"Please specify the full path."
            )

        return found[0]

    # Could not parse the path
    raise ValueError(
        f"Cannot parse artifact path: {input_path}. "
        f"Expected format: 'docs/{{type}}/{{name}}' or just '{{name}}'."
    )


# Chunk: docs/chunks/accept_full_artifact_paths - Flexible artifact path prefix stripping
def strip_artifact_path_prefix(
    input_id: str,
    artifact_type: ArtifactType,
) -> str:
    """Strip docs/{type}/ prefix from artifact identifier if present.

    A simpler utility for cases where the artifact type is already known
    (e.g., in `ve chunk validate`) and we just need to strip path prefixes.

    Args:
        input_id: User-provided identifier (e.g., "docs/chunks/foo" or "foo").
        artifact_type: Expected artifact type.

    Returns:
        Just the artifact ID/shortname.
    """
    # Strip trailing slashes
    input_id = input_id.rstrip("/")

    # Get the expected directory name for this type
    dir_name = ARTIFACT_DIR_NAME[artifact_type]

    # Split into parts
    parts = input_id.split("/")

    # Check for docs/{type}/{id} pattern
    if len(parts) >= 3 and parts[0] == "docs" and parts[1] == dir_name:
        return parts[2]

    # Check for {type}/{id} pattern
    if len(parts) >= 2 and parts[0] == dir_name:
        return parts[1]

    # Return as-is if no recognized prefix
    return input_id


# Chunk: docs/chunks/chunk_create_task_aware - Create external.yaml in project directory
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use ExternalArtifactRef format
# Chunk: docs/chunks/external_chunk_causal - Added created_after parameter
# Chunk: docs/chunks/remove_sequence_prefix - Use short_name only directory format
def create_external_yaml(
    project_path: Path,
    short_name: str,
    external_repo_ref: str,
    external_artifact_id: str,
    pinned_sha: str,
    artifact_type: ArtifactType,
    track: str = "main",
    created_after: list[str] | None = None,
) -> Path:
    """Create external.yaml in project's artifact directory.

    Args:
        project_path: Path to the project directory.
        short_name: Short name for the artifact directory.
        external_repo_ref: External repo identifier (org/repo format).
        external_artifact_id: Artifact ID in the external repo.
        pinned_sha: 40-character SHA to pin.
        artifact_type: Type of artifact.
        track: Branch to track (default "main").
        created_after: List of local artifact names this external artifact depends on
                       (for local causal ordering).

    Returns:
        Path to the created external.yaml file.
    """
    artifact_dir_name = ARTIFACT_DIR_NAME[artifact_type]

    # Use short_name only (no sequence prefix)
    artifact_dir = project_path / "docs" / artifact_dir_name / short_name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    external_yaml_path = artifact_dir / "external.yaml"
    data = {
        "artifact_type": artifact_type.value,
        "artifact_id": external_artifact_id,
        "repo": external_repo_ref,
        "track": track,
        "pinned": pinned_sha,
    }
    if created_after:
        data["created_after"] = created_after

    with open(external_yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return external_yaml_path
