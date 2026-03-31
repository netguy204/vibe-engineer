"""Artifact demotion logic for task context.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact manager pattern
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/artifact_demote_to_project - Demote external artifacts to project-local

This module handles demoting task-level artifacts back to project-local when
they only reference a single project. This is the inverse of promote_artifact().
"""

import re
import shutil
from pathlib import Path

import yaml

from external_refs import (
    is_external_artifact,
    load_external_ref,
    normalize_artifact_path,
    ARTIFACT_MAIN_FILE,
    ARTIFACT_DIR_NAME,
)
from models import ArtifactType

from task.config import (
    load_task_config,
    resolve_repo_directory,
    resolve_project_ref,
)
from task.exceptions import TaskDemoteError
from task.external import remove_dependent_from_artifact


def _read_artifact_frontmatter(artifact_path: Path, artifact_type: ArtifactType) -> dict:
    """Read and parse the frontmatter from an artifact's main file.

    Args:
        artifact_path: Path to the artifact directory.
        artifact_type: Type of artifact to determine main file.

    Returns:
        Parsed frontmatter dict, or empty dict if not parseable.
    """
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    main_path = artifact_path / main_file

    if not main_path.exists():
        return {}

    content = main_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}

    return yaml.safe_load(match.group(1)) or {}


def demote_artifact(
    task_dir: Path,
    artifact_path: str,
    target_project: str | None = None,
) -> dict:
    """Demote an external artifact back to a project-local artifact.

    This is the inverse of promote_artifact(). It moves an artifact from the
    external repo into the single project that references it, replacing the
    external.yaml pointer with the actual artifact files.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        artifact_path: Flexible path to artifact (e.g., "docs/chunks/my_chunk",
                       "chunks/my_chunk", or just "my_chunk")
        target_project: Optional project ref to demote to. Required if
                        multiple dependents exist.

    Returns:
        Dict with keys:
        - demoted_artifact: str - artifact ID
        - artifact_type: str - e.g., "chunk"
        - target_project: str - org/repo
        - local_path: Path - path in project
        - external_cleaned: bool - whether external copy was cleaned

    Raises:
        TaskDemoteError: If any step fails, with user-friendly message.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskDemoteError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskDemoteError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Normalize the artifact path
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path,
            search_path=external_repo_path,
            external_repo_name=external_repo_path.name,
        )
    except ValueError as e:
        raise TaskDemoteError(str(e))

    # 4. Verify the artifact exists in the external repo
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    source_path = external_repo_path / "docs" / dir_name / artifact_id
    if not source_path.exists():
        raise TaskDemoteError(
            f"Artifact '{artifact_id}' does not exist in external repository at {source_path}"
        )

    # 5. Read frontmatter to get dependents list
    frontmatter = _read_artifact_frontmatter(source_path, artifact_type)
    dependents = frontmatter.get("dependents", []) or []

    # 6. Validate exactly one dependent (or target_project specified)
    if len(dependents) == 0:
        raise TaskDemoteError(
            f"Artifact '{artifact_id}' has no dependent projects. "
            f"Cannot demote an orphaned artifact."
        )

    if target_project is not None:
        # Resolve the specified target project
        try:
            target_project = resolve_project_ref(target_project, config.projects)
        except ValueError as e:
            raise TaskDemoteError(str(e))

        # Verify it's actually a dependent
        dep_repos = [d.get("repo") for d in dependents]
        if target_project not in dep_repos:
            raise TaskDemoteError(
                f"Project '{target_project}' is not a dependent of artifact '{artifact_id}'. "
                f"Dependents: {', '.join(dep_repos)}"
            )
    elif len(dependents) > 1:
        dep_repos = [d.get("repo") for d in dependents]
        raise TaskDemoteError(
            f"Artifact '{artifact_id}' has multiple dependent projects: "
            f"{', '.join(dep_repos)}. "
            f"Specify --project to choose which project to demote to, "
            f"or use 've task demote --auto' to demote single-project artifacts."
        )
    else:
        # Exactly one dependent
        target_project = dependents[0].get("repo")

    # 7. Resolve the target project directory
    try:
        target_project_path = resolve_repo_directory(task_dir, target_project)
    except FileNotFoundError:
        raise TaskDemoteError(
            f"Target project '{target_project}' not found or not accessible"
        )

    # 8. Verify the target project has an external.yaml for this artifact
    target_artifact_dir = target_project_path / "docs" / dir_name / artifact_id
    external_yaml_path = target_artifact_dir / "external.yaml"

    if not external_yaml_path.exists():
        raise TaskDemoteError(
            f"Artifact '{artifact_id}' is not an external reference in project "
            f"'{target_project}' (no external.yaml found at {external_yaml_path}). "
            f"Cannot demote an artifact that is already local."
        )

    # Load external.yaml to get created_after for restoration
    ext_ref = load_external_ref(target_artifact_dir)
    original_created_after = ext_ref.created_after

    # 9. Copy artifact files from external repo to the target project
    #    First remove the external.yaml, then copy all files from source
    external_yaml_path.unlink()

    # Copy all files from external repo artifact directory to target project
    for item in source_path.iterdir():
        dest_item = target_artifact_dir / item.name
        if item.is_file():
            shutil.copy2(item, dest_item)
        elif item.is_dir():
            if dest_item.exists():
                shutil.rmtree(dest_item)
            shutil.copytree(item, dest_item)

    # 10. Restore original created_after from external.yaml if present
    if original_created_after:
        from frontmatter import update_frontmatter_field

        main_file = ARTIFACT_MAIN_FILE[artifact_type]
        local_main_path = target_artifact_dir / main_file
        if local_main_path.exists():
            update_frontmatter_field(local_main_path, "created_after", original_created_after)

    # 11. Remove dependent entry from external artifact's frontmatter
    #     Find the matching dependent entry for this target project
    dep_artifact_id = artifact_id  # Default: same name
    for dep in dependents:
        if dep.get("repo") == target_project:
            dep_artifact_id = dep.get("artifact_id", artifact_id)
            break

    try:
        remove_dependent_from_artifact(
            source_path,
            artifact_type,
            target_project,
            dep_artifact_id,
        )
    except (FileNotFoundError, ValueError):
        # Non-fatal: source may not have proper frontmatter
        pass

    # 12. Check if external artifact is now orphaned (no remaining dependents)
    updated_frontmatter = _read_artifact_frontmatter(source_path, artifact_type)
    remaining_dependents = updated_frontmatter.get("dependents", []) or []
    external_cleaned = len(remaining_dependents) == 0

    # Also remove external.yaml pointers from other projects that might reference
    # this artifact (shouldn't normally exist for single-dependent case)

    return {
        "demoted_artifact": artifact_id,
        "artifact_type": artifact_type.value,
        "target_project": target_project,
        "local_path": target_artifact_dir,
        "external_cleaned": external_cleaned,
    }


def scan_demotable_artifacts(
    task_dir: Path,
) -> list[dict]:
    """Scan all task-level artifacts and identify those eligible for demotion.

    An artifact is demotable if it has exactly one dependent project. Artifacts
    with zero dependents are orphaned (reported but not demotable). Artifacts
    with two or more dependents are shared and not demotable.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        List of dicts with keys:
        - artifact_id: str
        - artifact_type: str
        - target_project: str
        - reason: str

    Raises:
        TaskDemoteError: If task config cannot be loaded.
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskDemoteError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskDemoteError(
            f"External artifact repository '{config.external_artifact_repo}' not found"
        )

    candidates = []

    # 3. Iterate over all artifact types
    for artifact_type in ArtifactType:
        dir_name = ARTIFACT_DIR_NAME[artifact_type]
        artifacts_dir = external_repo_path / "docs" / dir_name

        if not artifacts_dir.exists():
            continue

        for artifact_dir in sorted(artifacts_dir.iterdir()):
            if not artifact_dir.is_dir():
                continue

            artifact_id = artifact_dir.name

            # Read frontmatter
            frontmatter = _read_artifact_frontmatter(artifact_dir, artifact_type)
            dependents = frontmatter.get("dependents", []) or []

            if len(dependents) == 1:
                target_project = dependents[0].get("repo", "unknown")

                # Additional heuristic: check code_paths and code_references
                reason = "single dependent project"
                code_paths = frontmatter.get("code_paths", []) or []
                code_references = frontmatter.get("code_references", []) or []

                # Check if code_references have cross-project qualifiers (::)
                has_cross_project_refs = False
                for ref in code_references:
                    ref_str = ref if isinstance(ref, str) else ref.get("ref", "")
                    if "::" in ref_str:
                        has_cross_project_refs = True
                        break

                if code_paths and not has_cross_project_refs:
                    reason = "single dependent, code confined to one project"

                candidates.append({
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type.value,
                    "target_project": target_project,
                    "reason": reason,
                })
            # Skip 0 dependents (orphaned) and 2+ dependents (shared)

    return candidates
