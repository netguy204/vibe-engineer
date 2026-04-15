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
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dataclasses import dataclass

from pydantic import BaseModel

from frontmatter import parse_frontmatter
from template_system import render_template


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_push_pull - Custom exception for diverged histories
class MergeNeededError(RuntimeError):
    """Raised when pull cannot fast-forward because histories have diverged."""
    pass


# ---------------------------------------------------------------------------
# Push/pull result dataclasses
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_push_pull - Push result dataclass
@dataclass
class PushResult:
    """Result of a push_entity operation."""
    commits_pushed: int
    has_uncommitted: bool


# Chunk: docs/chunks/entity_push_pull - Pull result dataclass
@dataclass
class PullResult:
    """Result of a pull_entity operation."""
    commits_merged: int
    up_to_date: bool


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


def _run_git_output(path: Path, *args: str, extra_env: dict | None = None) -> str:
    """Run a git command and return stdout. Raises RuntimeError on failure."""
    import os

    env = {**os.environ, **_GIT_ENV}
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {path}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Name derivation
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_attach_detach - Name derivation for entity attach
def derive_entity_name_from_url(url: str) -> str:
    """Derive an entity name from a repo URL or local path.

    Algorithm:
    1. Strip trailing slash
    2. Take the last path component (after the last '/' — works for URLs, SSH, paths)
    3. Strip '.git' suffix if present
    4. Strip 'entity-' prefix if present
    5. Return the result
    """
    # Strip trailing slash
    url = url.rstrip("/")
    # Last component after '/'
    last = url.rsplit("/", 1)[-1]
    # Strip .git suffix
    if last.endswith(".git"):
        last = last[:-4]
    # Strip entity- prefix
    if last.startswith("entity-"):
        last = last[len("entity-"):]
    return last


# ---------------------------------------------------------------------------
# Attached entity model
# ---------------------------------------------------------------------------


class AttachedEntityInfo(BaseModel):
    """Info about an entity attached as a git submodule."""

    name: str
    remote_url: Optional[str]       # None if not a submodule or no remote
    specialization: Optional[str]   # From ENTITY.md frontmatter
    status: str                     # "clean" | "uncommitted" | "ahead" | "unknown"


# ---------------------------------------------------------------------------
# Submodule operations
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_attach_detach - Submodule attach implementation
def attach_entity(project_dir: Path, repo_url: str, name: str) -> Path:
    """Attach an entity repository to a project as a git submodule.

    Args:
        project_dir: Path to the project git repository.
        repo_url: URL or local path to the entity's git repository.
        name: Name to use for the entity (subdirectory under .entities/).

    Returns:
        Path to the attached entity directory (.entities/<name>).

    Raises:
        RuntimeError: If project_dir is not a git repo or submodule add fails.
        ValueError: If the cloned repo is not a valid entity repo.
    """
    # Validate project_dir is a git repo
    check = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "--git-dir"],
        capture_output=True, text=True,
    )
    if check.returncode != 0:
        raise RuntimeError(
            f"'{project_dir}' is not a git repository"
        )

    # Ensure .entities/ exists
    entities_dir = project_dir / ".entities"
    entities_dir.mkdir(exist_ok=True)

    # Run git submodule add
    # Allow local file:// protocol (needed when repo_url is a local path)
    submodule_path = f".entities/{name}"
    try:
        _run_git(
            project_dir,
            "submodule", "add", repo_url, submodule_path,
            extra_env={"GIT_CONFIG_COUNT": "1",
                       "GIT_CONFIG_KEY_0": "protocol.file.allow",
                       "GIT_CONFIG_VALUE_0": "always"},
        )
    except RuntimeError as e:
        raise RuntimeError(f"Failed to attach entity '{name}': {e}") from e

    # Validate the cloned repo is an entity repo
    entity_path = project_dir / ".entities" / name
    if not is_entity_repo(entity_path):
        # Cleanup the partial submodule
        subprocess.run(
            ["git", "-C", str(project_dir), "submodule", "deinit", "-f", submodule_path],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(project_dir), "rm", "-f", submodule_path],
            capture_output=True,
        )
        modules_path = project_dir / ".git" / "modules" / ".entities" / name
        if modules_path.exists():
            shutil.rmtree(modules_path)
        raise ValueError("Attached repo is not a valid entity repo — missing ENTITY.md")

    return entity_path


# Chunk: docs/chunks/entity_attach_detach - Submodule detach implementation
def detach_entity(project_dir: Path, name: str, force: bool = False) -> None:
    """Detach an entity repository from a project.

    Args:
        project_dir: Path to the project git repository.
        name: Name of the entity to detach (subdirectory under .entities/).
        force: If True, detach even if the entity has uncommitted changes.

    Raises:
        ValueError: If the entity is not found.
        RuntimeError: If the entity has uncommitted changes and force=False.
    """
    entity_path = project_dir / ".entities" / name
    if not entity_path.exists():
        raise ValueError(f"Entity '{name}' not found at '{entity_path}'")

    # Check for uncommitted changes
    status_result = subprocess.run(
        ["git", "-C", str(entity_path), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if status_result.stdout.strip() and not force:
        raise RuntimeError(
            f"Entity '{name}' has uncommitted changes. Use force=True to override."
        )

    submodule_path = f".entities/{name}"

    # Full removal sequence
    subprocess.run(
        ["git", "-C", str(project_dir), "submodule", "deinit", "-f", submodule_path],
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(project_dir), "rm", "-f", submodule_path],
        capture_output=True,
    )
    modules_path = project_dir / ".git" / "modules" / ".entities" / name
    if modules_path.exists():
        shutil.rmtree(modules_path)


# ---------------------------------------------------------------------------
# Push / pull / set-origin operations
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_push_pull - Push entity repo to remote origin
def push_entity(entity_path: Path) -> PushResult:
    """Push the entity repo's current branch to its remote origin.

    Args:
        entity_path: Path to the entity repo directory.

    Returns:
        PushResult with commits_pushed count and has_uncommitted flag.

    Raises:
        ValueError: If entity_path is not a valid entity repo.
        RuntimeError: If no remote origin is configured, or if the entity is
            in detached HEAD state, or if git push fails.
    """
    if not is_entity_repo(entity_path):
        raise ValueError(
            f"'{entity_path}' is not a valid entity repo (missing ENTITY.md)."
        )

    # Check for remote origin
    remote_check = subprocess.run(
        ["git", "-C", str(entity_path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if remote_check.returncode != 0:
        raise RuntimeError(
            f"Entity '{entity_path.name}' has no remote origin configured. "
            "Use 've entity set-origin' to add one."
        )

    # Check for uncommitted changes
    status_out = _run_git_output(entity_path, "status", "--porcelain")
    has_uncommitted = bool(status_out.strip())

    # Determine current branch
    branch = _run_git_output(entity_path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch == "HEAD":
        raise RuntimeError(
            f"Entity '{entity_path.name}' is in detached HEAD state — "
            "checkout a branch first."
        )

    # Count commits ahead of origin before pushing
    try:
        ahead_out = _run_git_output(
            entity_path, "rev-list", f"origin/{branch}..HEAD"
        )
        commits_pushed = len([l for l in ahead_out.splitlines() if l.strip()])
    except RuntimeError:
        # origin/<branch> doesn't exist yet (first push) — count all commits
        try:
            all_out = _run_git_output(entity_path, "rev-list", "HEAD")
            commits_pushed = len([l for l in all_out.splitlines() if l.strip()])
        except RuntimeError:
            commits_pushed = 0

    # Push
    _run_git(entity_path, "push", "origin", branch)

    return PushResult(commits_pushed=commits_pushed, has_uncommitted=has_uncommitted)


# Chunk: docs/chunks/entity_push_pull - Pull entity repo from remote origin
def pull_entity(entity_path: Path) -> PullResult:
    """Fetch and fast-forward merge the entity repo from its remote origin.

    Args:
        entity_path: Path to the entity repo directory.

    Returns:
        PullResult with commits_merged count and up_to_date flag.

    Raises:
        ValueError: If entity_path is not a valid entity repo.
        RuntimeError: If no remote origin is configured or if the entity is
            in detached HEAD state.
        MergeNeededError: If histories have diverged (fast-forward not possible).
    """
    if not is_entity_repo(entity_path):
        raise ValueError(
            f"'{entity_path}' is not a valid entity repo (missing ENTITY.md)."
        )

    # Check for remote origin
    remote_check = subprocess.run(
        ["git", "-C", str(entity_path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if remote_check.returncode != 0:
        raise RuntimeError(
            f"Entity '{entity_path.name}' has no remote origin configured. "
            "Use 've entity set-origin' to add one."
        )

    # Determine current branch
    branch = _run_git_output(entity_path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch == "HEAD":
        raise RuntimeError(
            f"Entity '{entity_path.name}' is in detached HEAD state — "
            "checkout a branch first."
        )

    # Fetch remote state
    _run_git(entity_path, "fetch", "origin")

    # Check divergence
    # Commits on origin not in local (need to merge in)
    incoming_out = _run_git_output(
        entity_path, "rev-list", f"HEAD..origin/{branch}"
    )
    incoming = [l for l in incoming_out.splitlines() if l.strip()]

    # Commits in local not on origin (local is ahead)
    local_only_out = _run_git_output(
        entity_path, "rev-list", f"origin/{branch}..HEAD"
    )
    local_only = [l for l in local_only_out.splitlines() if l.strip()]

    if incoming and local_only:
        raise MergeNeededError(
            f"Entity '{entity_path.name}' histories have diverged "
            f"({len(incoming)} incoming, {len(local_only)} local). "
            "Use 've entity merge' to resolve."
        )

    if local_only and not incoming:
        # Local is strictly ahead — also a diverged case (merge needed if we
        # ever want a rebase, but for now treat as MergeNeeded)
        raise MergeNeededError(
            f"Entity '{entity_path.name}' is ahead of origin with {len(local_only)} "
            "local commit(s). Push first or use 've entity merge'."
        )

    if not incoming:
        # Already up to date
        return PullResult(commits_merged=0, up_to_date=True)

    # Fast-forward possible
    _run_git(entity_path, "merge", "--ff-only", f"origin/{branch}")
    return PullResult(commits_merged=len(incoming), up_to_date=False)


# Chunk: docs/chunks/entity_push_pull - Set or update entity repo remote origin
def set_entity_origin(entity_path: Path, url: str) -> None:
    """Set or update the remote origin URL for an entity's repo.

    Args:
        entity_path: Path to the entity repo directory.
        url: Remote URL (GitHub HTTPS/SSH or local path). Must be non-empty.

    Raises:
        ValueError: If entity_path is not a valid entity repo or url is empty.
    """
    if not is_entity_repo(entity_path):
        raise ValueError(
            f"'{entity_path}' is not a valid entity repo (missing ENTITY.md)."
        )

    if not url.strip():
        raise ValueError("URL must not be empty.")

    # Check if origin already exists
    remote_check = subprocess.run(
        ["git", "-C", str(entity_path), "remote"],
        capture_output=True, text=True,
    )
    existing_remotes = remote_check.stdout.splitlines()

    if "origin" in existing_remotes:
        _run_git(entity_path, "remote", "set-url", "origin", url)
    else:
        _run_git(entity_path, "remote", "add", "origin", url)


# Chunk: docs/chunks/entity_attach_detach - List attached entity submodules
def list_attached_entities(project_dir: Path) -> list[AttachedEntityInfo]:
    """List all entities attached as git submodules.

    Args:
        project_dir: Path to the project git repository.

    Returns:
        List of AttachedEntityInfo for each attached entity submodule.
    """
    entities_dir = project_dir / ".entities"
    if not entities_dir.exists():
        return []

    results = []
    for d in sorted(entities_dir.iterdir()):
        if not d.is_dir():
            continue
        # Detect submodule: submodule checkout has .git as a file, not directory
        git_marker = d / ".git"
        if not git_marker.is_file():
            continue

        # Get remote URL
        remote_url: Optional[str] = None
        url_result = subprocess.run(
            ["git", "-C", str(d), "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        if url_result.returncode == 0:
            remote_url = url_result.stdout.strip() or None

        # Get specialization from ENTITY.md
        specialization: Optional[str] = None
        try:
            metadata = read_entity_metadata(d)
            specialization = metadata.specialization
        except Exception:
            pass

        # Get status
        status = "unknown"
        try:
            porcelain = subprocess.run(
                ["git", "-C", str(d), "status", "--porcelain"],
                capture_output=True, text=True,
            )
            if porcelain.stdout.strip():
                status = "uncommitted"
            else:
                ahead = subprocess.run(
                    ["git", "-C", str(d), "log", "@{u}..", "--oneline"],
                    capture_output=True, text=True,
                )
                if ahead.returncode == 0 and ahead.stdout.strip():
                    status = "ahead"
                else:
                    status = "clean"
        except Exception:
            status = "unknown"

        results.append(AttachedEntityInfo(
            name=d.name,
            remote_url=remote_url,
            specialization=specialization,
            status=status,
        ))

    return results
