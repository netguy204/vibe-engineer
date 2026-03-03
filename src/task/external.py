"""External artifact copy and remove operations for task context.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module handles copying artifacts from the external repo to project repos
as external references, and removing those references.
"""

import re
from pathlib import Path

import yaml

from artifact_ordering import ArtifactIndex
from external_refs import (
    load_external_ref,
    normalize_artifact_path,
    create_external_yaml,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)
from models import ArtifactType

from task.config import (
    load_task_config,
    resolve_repo_directory,
    resolve_project_ref,
)
from task.exceptions import TaskCopyExternalError, TaskRemoveExternalError
from task.artifact_ops import append_dependent_to_artifact


# Chunk: docs/chunks/remove_external_ref - Helper to remove dependent entry from artifact frontmatter
def remove_dependent_from_artifact(
    artifact_path: Path,
    artifact_type: ArtifactType,
    repo: str,
    artifact_id: str,
) -> bool:
    """Remove a dependent entry from artifact's frontmatter.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.
        repo: Repository reference to match (e.g., "acme/proj").
        artifact_id: Artifact ID to match (the name in the target project).

    Returns:
        True if an entry was removed, False if no matching entry found.

    Raises:
        FileNotFoundError: If main file doesn't exist in artifact_path.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        raise FileNotFoundError(f"{main_file} not found in {artifact_path}")

    # Read existing frontmatter
    content = main_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {main_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Get existing dependents or return early if none
    existing_dependents = frontmatter.get("dependents", []) or []
    if not existing_dependents:
        return False

    # Find and remove matching entry
    match_key = (repo, artifact_id)
    found = False
    new_dependents = []

    for existing in existing_dependents:
        existing_key = (
            existing.get("repo"),
            existing.get("artifact_id"),
        )
        if existing_key == match_key:
            found = True
            # Skip this entry (remove it)
        else:
            new_dependents.append(existing)

    if not found:
        return False

    # Update frontmatter and write back
    frontmatter["dependents"] = new_dependents
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"
    main_path.write_text(new_content)

    return True


# Chunk: docs/chunks/artifact_copy_backref - Back-reference update for copy-external
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path/project resolution for copy-external
def copy_artifact_as_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
    new_name: str | None = None,
) -> dict:
    """Copy an artifact from external repo as an external reference in target project.

    Creates an external.yaml in the target project that references an artifact
    already present in the external artifact repository.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Flexible project ref (e.g., "acme/proj" or just "proj")
        new_name: Optional new name for the artifact in destination

    Returns:
        Dict with keys:
        - external_yaml_path: Path to created external.yaml in target project

    Raises:
        TaskCopyExternalError: If any step fails, with user-friendly message.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Normalize artifact path with external repo context
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path,
            search_path=external_repo_path,
            external_repo_name=external_repo_path.name,
        )
    except ValueError as e:
        raise TaskCopyExternalError(str(e))

    # 4. Verify the artifact exists in external repo
    source_path = external_repo_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
    if not source_path.exists():
        raise TaskCopyExternalError(
            f"Artifact '{artifact_id}' does not exist in external repository at {source_path}"
        )

    # 5. Resolve flexible project reference
    try:
        target_project = resolve_project_ref(target_project, config.projects)
    except ValueError as e:
        raise TaskCopyExternalError(str(e))

    try:
        target_project_path = resolve_repo_directory(task_dir, target_project)
    except FileNotFoundError:
        raise TaskCopyExternalError(
            f"Target project '{target_project}' not found or not accessible"
        )

    # 6. Determine destination name
    dest_name = new_name if new_name else artifact_id

    # 7. Check for collision in target project
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    dest_path = target_project_path / "docs" / dir_name / dest_name
    if dest_path.exists():
        raise TaskCopyExternalError(
            f"Artifact '{dest_name}' already exists in target project at {dest_path}. "
            f"Use --name to specify a different name."
        )

    # 8. Get current tips for target project's causal ordering
    try:
        index = ArtifactIndex(target_project_path)
        tips = index.find_tips(artifact_type)
    except Exception:
        tips = []

    # 9. Create external.yaml (no pinned SHA - always resolve to HEAD)
    external_yaml_path = create_external_yaml(
        project_path=target_project_path,
        short_name=dest_name,
        external_repo_ref=config.external_artifact_repo,
        external_artifact_id=artifact_id,
        artifact_type=artifact_type,
        created_after=tips,
    )

    # 10. Update source artifact's dependents with back-reference
    dependent_entry = {
        "artifact_type": artifact_type.value,
        "artifact_id": dest_name,  # The name in the target project
        "repo": target_project,
    }
    append_dependent_to_artifact(source_path, artifact_type, dependent_entry)

    # Return result
    return {
        "external_yaml_path": external_yaml_path,
        "source_updated": True,
    }


# Chunk: docs/chunks/remove_external_ref - Core function removing external.yaml and updating dependents
def remove_artifact_from_external(
    task_dir: Path,
    artifact_path: str,
    target_project: str,
) -> dict:
    """Remove an artifact's external reference from a target project.

    Inverse of copy_artifact_as_external(). Removes the external.yaml from the
    target project and updates the artifact's dependents list in the external repo.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Flexible project ref (e.g., "acme/proj" or just "proj")

    Returns:
        Dict with keys:
        - removed: bool - True if external.yaml was removed
        - dependent_removed: bool - True if dependent entry was removed from source
        - orphaned: bool - True if this was the last project link (warning)
        - directory_cleaned: bool - True if empty directory was removed

    Raises:
        TaskRemoveExternalError: If any step fails, with user-friendly message.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Normalize artifact path with external repo context
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path,
            search_path=external_repo_path,
            external_repo_name=external_repo_path.name,
        )
    except ValueError as e:
        raise TaskRemoveExternalError(str(e))

    # 4. Verify the artifact exists in external repo
    source_path = external_repo_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
    if not source_path.exists():
        raise TaskRemoveExternalError(
            f"Artifact '{artifact_id}' does not exist in external repository at {source_path}"
        )

    # 5. Resolve flexible project reference
    try:
        target_project = resolve_project_ref(target_project, config.projects)
    except ValueError as e:
        raise TaskRemoveExternalError(str(e))

    try:
        target_project_path = resolve_repo_directory(task_dir, target_project)
    except FileNotFoundError:
        raise TaskRemoveExternalError(
            f"Target project '{target_project}' not found or not accessible"
        )

    # 6. Determine the artifact directory in target project
    # The artifact may have been copied with the same name as in external repo
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    target_artifact_dir = target_project_path / "docs" / dir_name / artifact_id
    external_yaml_path = target_artifact_dir / "external.yaml"

    # 7. Check if external.yaml exists (idempotent - return early if not)
    if not external_yaml_path.exists():
        return {
            "removed": False,
            "dependent_removed": False,
            "orphaned": False,
            "directory_cleaned": False,
        }

    # 8. Load external.yaml to get the actual artifact_id in external repo
    # (may differ if --name was used during copy)
    ref = load_external_ref(target_artifact_dir)
    source_artifact_id = ref.artifact_id

    # Update source_path if artifact_id differs (--name was used)
    if source_artifact_id != artifact_id:
        source_path = external_repo_path / "docs" / dir_name / source_artifact_id

    # 9. Delete external.yaml
    external_yaml_path.unlink()
    removed = True

    # 10. Remove directory if now empty
    directory_cleaned = False
    if target_artifact_dir.exists():
        remaining_files = list(target_artifact_dir.iterdir())
        if not remaining_files:
            target_artifact_dir.rmdir()
            directory_cleaned = True

    # 11. Remove dependent entry from source artifact's frontmatter
    # The dependent entry uses artifact_id as the name in the target project
    dependent_removed = False
    try:
        dependent_removed = remove_dependent_from_artifact(
            source_path,
            artifact_type,
            target_project,
            artifact_id,  # The name in the target project
        )
    except (FileNotFoundError, ValueError):
        # Source artifact may not have a dependents field, or frontmatter is malformed
        pass

    # 12. Check if dependents list is now empty (orphan warning)
    orphaned = False
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = source_path / main_file
    if main_path.exists():
        content = main_path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            dependents = frontmatter.get("dependents", []) or []
            orphaned = len(dependents) == 0

    return {
        "removed": removed,
        "dependent_removed": dependent_removed,
        "orphaned": orphaned,
        "directory_cleaned": directory_cleaned,
    }
