"""Standalone git-repo-based entity creation and management.

# Chunk: docs/chunks/entity_repo_structure - Standalone entity git repo creation

Entities are portable specialists that move across the platform via git
submodules. Each entity has its own git repo that can be hosted on GitHub,
attached to any project, forked for divergent training, and merged to combine
learnings. This module creates the repo structure — the "blank entity" that
gets populated with knowledge over time.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from frontmatter import parse_frontmatter
from template_system import render_template


# Name pattern extends the existing ENTITY_NAME_PATTERN to also allow hyphens
# (kebab-case), matching the investigation's my-specialist example.
ENTITY_REPO_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


class EntityRepoMetadata(BaseModel):
    """Pydantic model for ENTITY.md frontmatter."""

    name: str
    created: str  # ISO 8601 datetime string
    specialization: Optional[str] = None
    origin: Optional[str] = None
    role: Optional[str] = None


def create_entity_repo(
    dest: Path,
    name: str,
    role: str | None = None,
) -> Path:
    """Create a standalone git-repo-based entity.

    Creates a directory structure with wiki/, memories/, and episodic/
    subdirectories, renders ENTITY.md and wiki page templates, initializes
    a git repo, and makes the initial commit.

    Args:
        dest: Parent directory where the entity repo will be created.
        name: Entity name (kebab-case or snake_case, must match
              ENTITY_REPO_NAME_PATTERN).
        role: Optional brief description of the entity's purpose.

    Returns:
        Path to the created entity repo directory.

    Raises:
        ValueError: If name is invalid or the destination already exists.
    """
    # Validate name
    if not ENTITY_REPO_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid entity name '{name}'. "
            "Name must start with a lowercase letter and contain only "
            "lowercase letters, digits, underscores, or hyphens."
        )

    repo_path = dest / name

    # Reject if already exists
    if repo_path.exists():
        raise ValueError(
            f"Entity directory '{repo_path}' already exists. "
            "Choose a different name or remove the existing directory."
        )

    # Create directory structure
    leaf_dirs = [
        repo_path / "wiki" / "domain",
        repo_path / "wiki" / "projects",
        repo_path / "wiki" / "techniques",
        repo_path / "wiki" / "relationships",
        repo_path / "memories" / "journal",
        repo_path / "memories" / "consolidated",
        repo_path / "memories" / "core",
        repo_path / "episodic",
    ]
    for d in leaf_dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    # Render ENTITY.md
    created = datetime.now(timezone.utc).isoformat()
    entity_md_content = render_template(
        "entity",
        "entity_md.jinja2",
        name=name,
        created=created,
        role=role,
    )
    (repo_path / "ENTITY.md").write_text(entity_md_content)

    # Render wiki pages
    wiki_dir = repo_path / "wiki"
    (wiki_dir / "wiki_schema.md").write_text(
        render_template("entity", "wiki_schema.md.jinja2")
    )
    (wiki_dir / "identity.md").write_text(
        render_template("entity", "wiki/identity.md.jinja2", created=created, role=role)
    )
    (wiki_dir / "index.md").write_text(
        render_template("entity", "wiki/index.md.jinja2", name=name, created=created)
    )
    (wiki_dir / "log.md").write_text(
        render_template("entity", "wiki/log.md.jinja2", created=created)
    )

    # Git init + initial commit
    _git_init(repo_path)
    _git_commit_all(repo_path, f"Initial entity state: {name}")

    return repo_path


def is_entity_repo(path: Path) -> bool:
    """Return True if path is a valid entity repo directory.

    A directory is an entity repo if it contains ENTITY.md with valid
    frontmatter that includes a 'name' field.

    Args:
        path: Directory to check.

    Returns:
        True if path is a valid entity repo, False for any failure.
    """
    try:
        entity_md = path / "ENTITY.md"
        if not entity_md.exists():
            return False
        metadata = parse_frontmatter(entity_md, EntityRepoMetadata)
        return metadata is not None and bool(metadata.name)
    except Exception:
        return False


def read_entity_metadata(path: Path) -> EntityRepoMetadata:
    """Read and return entity metadata from ENTITY.md.

    Args:
        path: Path to the entity repo directory.

    Returns:
        EntityRepoMetadata parsed from ENTITY.md frontmatter.

    Raises:
        FileNotFoundError: If ENTITY.md does not exist.
        ValueError: If ENTITY.md frontmatter is missing or invalid.
    """
    entity_md = path / "ENTITY.md"
    if not entity_md.exists():
        raise FileNotFoundError(
            f"ENTITY.md not found in '{path}'. "
            "Is this a valid entity repo?"
        )

    metadata = parse_frontmatter(entity_md, EntityRepoMetadata)
    if metadata is None:
        raise ValueError(
            f"Could not parse valid EntityRepoMetadata from '{entity_md}'. "
            "Frontmatter may be missing or have invalid fields."
        )

    return metadata


# ---------------------------------------------------------------------------
# Internal git helpers
# ---------------------------------------------------------------------------

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Entity Creator",
    "GIT_AUTHOR_EMAIL": "entity@ve.local",
    "GIT_COMMITTER_NAME": "Entity Creator",
    "GIT_COMMITTER_EMAIL": "entity@ve.local",
}


def _run_git(path: Path, *args: str, extra_env: dict | None = None) -> None:
    """Run a git command in the given directory, raising on failure."""
    import os

    env = {**os.environ, **_GIT_ENV}
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {path}:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


def _git_init(path: Path) -> None:
    """Initialize a git repository at path."""
    _run_git(path, "init", "-b", "main")


def _git_commit_all(path: Path, message: str) -> None:
    """Stage all files and create a commit."""
    _run_git(path, "add", "-A")
    _run_git(path, "commit", "-m", message)
