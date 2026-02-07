"""Artifact promotion logic for task context.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module handles promoting local artifacts to the task-level external repository,
including proper causal ordering and back-reference tracking.
"""

import shutil
from pathlib import Path

import yaml

from artifact_ordering import ArtifactIndex
from external_refs import (
    detect_artifact_type_from_path,
    is_external_artifact,
    create_external_yaml,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)
from models import ArtifactType, TaskConfig

from task.config import (
    find_task_directory,
    load_task_config,
    resolve_repo_directory,
)
from task.exceptions import TaskPromoteError
from task.artifact_ops import add_dependents_to_artifact


# Chunk: docs/chunks/artifact_promote - Determine which project contains the artifact being promoted
def identify_source_project(task_dir: Path, artifact_path: Path, config: TaskConfig) -> str:
    """Determine which project (org/repo format) contains the artifact.

    Args:
        task_dir: The task directory containing .ve-task.yaml.
        artifact_path: Path to the artifact being promoted.
        config: Loaded task configuration.

    Returns:
        The project reference in org/repo format.

    Raises:
        TaskPromoteError: If artifact is not within any configured project.
    """
    artifact_resolved = artifact_path.resolve()

    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            project_resolved = project_path.resolve()

            # Check if artifact_path is within this project
            try:
                artifact_resolved.relative_to(project_resolved)
                return project_ref
            except ValueError:
                continue
        except FileNotFoundError:
            continue

    raise TaskPromoteError(
        f"Artifact '{artifact_path}' is not within any configured project. "
        f"Projects: {', '.join(config.projects)}"
    )


# Chunk: docs/chunks/artifact_promote - Parse created_after field from artifact's main file
def _get_artifact_created_after(artifact_path: Path, artifact_type: ArtifactType) -> list[str]:
    """Get the created_after field from an artifact's main file.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.

    Returns:
        List of artifact names from created_after, or empty list.
    """
    import re

    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        return []

    content = main_path.read_text()

    # Parse frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return []

    frontmatter = yaml.safe_load(match.group(1)) or {}
    created_after = frontmatter.get("created_after", [])

    if created_after is None:
        return []
    if isinstance(created_after, str):
        return [created_after]
    if isinstance(created_after, list):
        return created_after

    return []


# Chunk: docs/chunks/artifact_promote - Core promotion logic for artifact task-level promotion
def promote_artifact(
    artifact_path: Path,
    new_name: str | None = None,
) -> dict:
    """Promote a local artifact to the task-level external repository.

    Orchestrates artifact promotion:
    1. Validates artifact is local (not already external)
    2. Detects artifact type from path
    3. Finds task directory and loads config
    4. Identifies source project
    5. Checks for collision in external repo
    6. Copies artifact directory to external repo
    7. Updates promoted artifact's created_after to external tips
    8. Updates promoted artifact's dependents with source project
    9. Creates external.yaml in source, preserving original created_after

    Args:
        artifact_path: Path to the local artifact directory.
        new_name: Optional new name for destination (--name flag value).

    Returns:
        Dict with keys:
        - external_artifact_path: Path to promoted artifact in external repo
        - external_yaml_path: Path to created external.yaml in source

    Raises:
        TaskPromoteError: If any step fails, with user-friendly message.
    """
    from frontmatter import update_frontmatter_field

    artifact_path = Path(artifact_path).resolve()

    # 1. Validate artifact exists and has a main document
    if not artifact_path.exists():
        raise TaskPromoteError(f"Artifact path does not exist: {artifact_path}")

    if not artifact_path.is_dir():
        raise TaskPromoteError(f"Artifact path is not a directory: {artifact_path}")

    # 2. Detect artifact type from path
    try:
        artifact_type = detect_artifact_type_from_path(artifact_path)
    except ValueError as e:
        raise TaskPromoteError(str(e))

    # Check if already external
    if is_external_artifact(artifact_path, artifact_type):
        raise TaskPromoteError(
            f"Artifact '{artifact_path.name}' is already an external reference. "
            f"Cannot promote an artifact that is already external."
        )

    # Verify main file exists
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    if not (artifact_path / main_file).exists():
        raise TaskPromoteError(
            f"Artifact '{artifact_path.name}' does not have a {main_file} file. "
            f"Only local artifacts with main documents can be promoted."
        )

    # 3. Find task directory
    task_dir = find_task_directory(artifact_path)
    if task_dir is None:
        raise TaskPromoteError(
            f"Cannot find task directory (.ve-task.yaml) above '{artifact_path}'. "
            f"Artifact promotion requires a task context."
        )

    # Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskPromoteError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 4. Identify source project
    source_project = identify_source_project(task_dir, artifact_path, config)

    # 5. Resolve external repo and check for collision
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskPromoteError(
            f"External artifact repository '{config.external_artifact_repo}' not found"
        )

    # Determine destination name
    dest_name = new_name if new_name else artifact_path.name
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    dest_path = external_repo_path / "docs" / dir_name / dest_name

    if dest_path.exists():
        raise TaskPromoteError(
            f"Artifact '{dest_name}' already exists in external repository at {dest_path}. "
            f"Use --name to specify a different name."
        )

    # Save original created_after before copying
    original_created_after = _get_artifact_created_after(artifact_path, artifact_type)

    # 6. Copy artifact directory to external repo
    shutil.copytree(artifact_path, dest_path)

    # 7. Get external repo tips for the promoted artifact's created_after
    try:
        external_index = ArtifactIndex(external_repo_path)
        external_tips = external_index.find_tips(artifact_type)
        # Exclude the just-copied artifact from tips (it's not in the index yet)
        external_tips = [t for t in external_tips if t != dest_name]
    except Exception:
        external_tips = []

    # Update promoted artifact's created_after to external tips
    dest_main_path = dest_path / main_file
    if external_tips:
        update_frontmatter_field(dest_main_path, "created_after", external_tips)

    # 8. Update promoted artifact's dependents with source project
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": artifact_path.name,  # Original name in source project
        "repo": source_project,
    }
    add_dependents_to_artifact(dest_path, artifact_type, [dependent_entry])

    # 9. Clear source directory and create external.yaml
    # Remove all files from source directory
    for item in artifact_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    # Create external.yaml with original created_after (no pinned SHA - always resolve to HEAD)
    external_yaml_path = create_external_yaml(
        project_path=artifact_path.parent.parent.parent,  # Go up from artifact to project root
        short_name=artifact_path.name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=dest_name,
        artifact_type=artifact_type,
        created_after=original_created_after,
    )

    return {
        "external_artifact_path": dest_path,
        "external_yaml_path": external_yaml_path,
    }
