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


# Chunk: docs/chunks/consolidate_ext_refs - Updated to use artifact_type and artifact_id fields
# Chunk: docs/chunks/external_chunk_causal - created_after parameter for causal ordering
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
