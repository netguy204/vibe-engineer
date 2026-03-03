"""Friction entry operations for task context.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_operations_decompose - Task utilities package decomposition

This module handles creating friction entries in the external repo and
linking them to project repos via external friction sources.
"""

import re
from pathlib import Path

import yaml

from friction import Friction
from git_utils import get_current_sha

from task.config import (
    load_task_config,
    resolve_repo_directory,
)
from task.exceptions import TaskFrictionError


# Chunk: docs/chunks/selective_artifact_friction - Add external friction source reference to project FRICTION.md
def add_external_friction_source(
    project_path: Path,
    external_repo_ref: str,
    pinned_sha: str,
    entry_id: str,
) -> None:
    """Add or update external friction source reference in project's FRICTION.md.

    If an external_friction_sources entry for the same repo already exists,
    the entry_id is appended to entry_ids (if not already present) and
    pinned SHA is updated. Otherwise, a new entry is created.

    Args:
        project_path: Path to the project directory
        external_repo_ref: External repo in org/repo format
        pinned_sha: Commit SHA at time of reference creation
        entry_id: Friction entry ID to add (e.g., "F003")

    Raises:
        ValueError: If FRICTION.md doesn't exist or has invalid frontmatter
    """
    friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
    if not friction_path.exists():
        raise ValueError(f"FRICTION.md not found in {project_path}")

    content = friction_path.read_text()

    # Parse frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {friction_path}")

    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    # Get or create external_friction_sources list
    external_sources = frontmatter.get("external_friction_sources", []) or []

    # Find existing entry for this repo
    found = False
    for source in external_sources:
        if source.get("repo") == external_repo_ref:
            # Update existing entry
            entry_ids = source.get("entry_ids", []) or []
            if entry_id not in entry_ids:
                entry_ids.append(entry_id)
                source["entry_ids"] = entry_ids
            source["pinned"] = pinned_sha
            found = True
            break

    if not found:
        # Create new entry
        external_sources.append({
            "repo": external_repo_ref,
            "track": "main",
            "pinned": pinned_sha,
            "entry_ids": [entry_id],
        })

    # Update frontmatter and write back
    frontmatter["external_friction_sources"] = external_sources
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_frontmatter}---\n{body}"
    friction_path.write_text(new_content)


# Chunk: docs/chunks/selective_artifact_friction - Task-aware friction entry creation with external references
def create_task_friction_entry(
    task_dir: Path,
    title: str,
    description: str,
    impact: str,
    theme_id: str,
    theme_name: str | None = None,
    projects: list[str] | None = None,
) -> dict:
    """Create friction entry in task directory context.

    Orchestrates multi-repo friction entry creation:
    1. Creates friction entry in external repo's FRICTION.md
    2. Adds/updates external_friction_sources in each project's FRICTION.md

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml
        title: Brief title for the friction entry
        description: Detailed description of the friction
        impact: Severity level (low, medium, high, blocking)
        theme_id: Theme ID to cluster the entry under
        theme_name: Human-readable theme name (required if theme is new)
        projects: Optional list of project refs to link (default: all projects)

    Returns:
        Dict with keys:
        - entry_id: The ID of the created entry (e.g., "F003")
        - external_repo_path: Path to external repo
        - project_refs: Dict mapping project repo ref to whether FRICTION.md was updated

    Raises:
        TaskFrictionError: If any step fails, with user-friendly message
    """
    # 1. Load task config
    try:
        config = load_task_config(task_dir)
    except FileNotFoundError:
        raise TaskFrictionError(
            f"Task configuration not found. Expected .ve-task.yaml in {task_dir}"
        )

    # 2. Resolve external repo path
    try:
        external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
    except FileNotFoundError:
        raise TaskFrictionError(
            f"External artifact repository '{config.external_artifact_repo}' not found or not accessible"
        )

    # 3. Check that external repo has FRICTION.md
    friction_log = Friction(external_repo_path)
    if not friction_log.exists():
        raise TaskFrictionError(
            f"External repository '{config.external_artifact_repo}' does not have a FRICTION.md. "
            f"Run 've init' in the external repo first."
        )

    # 4. Get current SHA from external repo
    try:
        pinned_sha = get_current_sha(external_repo_path)
    except ValueError as e:
        raise TaskFrictionError(
            f"Failed to resolve HEAD SHA in external repository '{config.external_artifact_repo}': {e}"
        )

    # 5. Create friction entry in external repo
    try:
        entry_id = friction_log.append_entry(
            title=title,
            description=description,
            impact=impact,
            theme_id=theme_id,
            theme_name=theme_name,
        )
    except ValueError as e:
        raise TaskFrictionError(f"Failed to create friction entry: {e}")

    # 6. For each project: add/update external_friction_sources
    effective_projects = projects if projects else config.projects
    project_refs = {}

    for project_ref in effective_projects:
        # Resolve project path
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
        except FileNotFoundError:
            raise TaskFrictionError(
                f"Project directory '{project_ref}' not found or not accessible"
            )

        # Check if project has FRICTION.md
        project_friction = Friction(project_path)
        if not project_friction.exists():
            # Skip projects without FRICTION.md (with implicit warning via project_refs)
            project_refs[project_ref] = False
            continue

        # Add external friction source reference
        try:
            add_external_friction_source(
                project_path=project_path,
                external_repo_ref=config.external_artifact_repo,
                pinned_sha=pinned_sha,
                entry_id=entry_id,
            )
            project_refs[project_ref] = True
        except ValueError as e:
            raise TaskFrictionError(
                f"Failed to update FRICTION.md in project '{project_ref}': {e}"
            )

    # 7. Return results
    return {
        "entry_id": entry_id,
        "external_repo_path": external_repo_path,
        "project_refs": project_refs,
    }
