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

import yaml
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


# Chunk: docs/chunks/entity_fork_merge - Fork result dataclass
@dataclass
class ForkResult:
    """Result of a fork_entity operation."""
    source_name: str
    new_name: str
    dest_path: Path


# Chunk: docs/chunks/entity_fork_merge - Merge result dataclass
@dataclass
class MergeResult:
    """Result of a clean merge_entity operation."""
    source: str
    commits_merged: int
    new_pages: int
    updated_pages: int


# Chunk: docs/chunks/entity_fork_merge - Conflict resolution dataclass
@dataclass
class ConflictResolution:
    """A single LLM-resolved conflict, pending operator approval."""
    relative_path: str
    synthesized: str
    is_wiki: bool


# Chunk: docs/chunks/entity_fork_merge - Merge conflicts pending dataclass
@dataclass
class MergeConflictsPending:
    """Merge halted at conflicts; operator must approve before committing."""
    source: str
    resolutions: list[ConflictResolution]
    unresolvable: list[str]

# Chunk: docs/chunks/wiki_lint_command - Wiki integrity lint result types
@dataclass
class WikiLintIssue:
    """A single wiki integrity issue found during linting."""
    file: str       # relative to wiki root, e.g. "domain/foo.md"
    issue_type: str  # "dead_wikilink" | "frontmatter_error" | "missing_from_index" | "orphan_page"
    detail: str     # human-readable description


@dataclass
class WikiLintResult:
    """Aggregated result of a wiki lint run."""
    issues: list[WikiLintIssue]

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


# Chunk: docs/chunks/wiki_rename_command - Result of a wiki page rename operation
@dataclass
class WikiRenameResult:
    """Result of a wiki_rename operation."""
    files_updated: int  # Number of wiki files that had wikilinks rewritten
    old_path: str
    new_path: str


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
    # Chunk: docs/chunks/entity_sop_file - SOP file for role-specific startup procedures
    (wiki_dir / "SOP.md").write_text(
        render_template("entity", "wiki/SOP.md.jinja2", created=created)
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

    # Resolve relative local paths to absolute so git doesn't interpret them
    # relative to the project's remote URL.
    repo_url_resolved = repo_url
    candidate = Path(repo_url).expanduser()
    if candidate.exists() and candidate.is_dir():
        repo_url_resolved = str(candidate.resolve())

    # Run git submodule add
    # Allow local file:// protocol (needed when repo_url is a local path)
    submodule_path = f".entities/{name}"
    try:
        _run_git(
            project_dir,
            "submodule", "add", repo_url_resolved, submodule_path,
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


# Chunk: docs/chunks/entity_worktree_support - Initialize entity submodules in orchestrator worktree
def init_entity_submodules_in_worktree(worktree_path: Path, chunk: str) -> None:
    """Initialize entity submodules in an orchestrator worktree.

    After `git worktree add`, the worktree directory exists but entity
    submodules have not been initialized. This function:
    1. Runs `git submodule update --init` in the worktree to populate
       .entities/<name>/ directories.
    2. For each entity, checks out a working branch `ve-worktree-<chunk>`
       from the detached HEAD state left by submodule init.

    This ensures agents running in the worktree can commit entity changes
    without affecting the main checkout or other worktrees.

    No-op if .entities/ doesn't exist or contains no submodule-based entities.

    Args:
        worktree_path: Absolute path to the orchestrator-created worktree.
        chunk: Chunk name used to derive the entity working branch name.
    """
    import logging
    logger = logging.getLogger(__name__)

    entities_dir = worktree_path / ".entities"
    if not entities_dir.exists():
        return

    # Initialize all submodules in the worktree
    result = subprocess.run(
        ["git", "submodule", "update", "--init"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        env={**__import__("os").environ,
             "GIT_CONFIG_COUNT": "1",
             "GIT_CONFIG_KEY_0": "protocol.file.allow",
             "GIT_CONFIG_VALUE_0": "always"},
    )
    if result.returncode != 0:
        logger.warning(
            "git submodule update --init failed in worktree %s: %s",
            worktree_path, result.stderr,
        )
        return

    # For each entity submodule, check out a working branch
    branch_name = f"ve-worktree-{chunk}"
    for entity_dir in sorted(entities_dir.iterdir()):
        if not entity_dir.is_dir():
            continue
        # Submodule marker: .git is a file (not a directory)
        if not (entity_dir / ".git").is_file():
            continue

        # Try to create and checkout the working branch
        result = subprocess.run(
            ["git", "-C", str(entity_dir), "checkout", "-b", branch_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Branch may already exist — just check it out
            result = subprocess.run(
                ["git", "-C", str(entity_dir), "checkout", branch_name],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.warning(
                    "Could not checkout branch %s in entity %s: %s",
                    branch_name, entity_dir.name, result.stderr,
                )


# Chunk: docs/chunks/entity_worktree_support - Merge entity worktree branches to main after chunk merge
def merge_entity_worktree_branches(
    project_dir: Path, chunk: str, worktree_path: Optional[Path] = None
) -> None:
    """Merge entity worktree branches to entity main after chunk merges to base.

    After the orchestrator merges orch/<chunk> to main (which includes the
    updated entity submodule pointer), this function merges each entity's
    `ve-worktree-<chunk>` branch into the entity's `main` branch and deletes
    the worktree branch. This keeps the entity's main branch current.

    When `git submodule update --init` runs inside an orchestrator worktree,
    git creates a separate git module for the submodule at a worktree-specific
    path. The entity in the worktree and the entity in the main checkout do NOT
    share the same git module/ref namespace. To bridge them, this function
    fetches the worktree entity branch into the project entity module, then
    merges using git plumbing commands (merge-base, merge-tree, commit-tree,
    update-ref). This avoids disturbing the working directory.

    If a merge conflict occurs (e.g., two worktrees modified the same entity),
    logs a warning and skips that entity — it is not a fatal error.

    No-op if .entities/ doesn't exist, the worktree path doesn't exist, or no
    entities have a ve-worktree-<chunk> branch.

    Args:
        project_dir: Root project directory where .entities/ lives.
        chunk: Chunk name matching the ve-worktree-<chunk> branch.
        worktree_path: Path to the chunk's orchestrator worktree. Defaults to
            project_dir/.ve/chunks/<chunk>/worktree (single-repo mode).
    """
    import logging
    import os
    logger = logging.getLogger(__name__)

    entities_dir = project_dir / ".entities"
    if not entities_dir.exists():
        return

    if worktree_path is None:
        worktree_path = project_dir / ".ve" / "chunks" / chunk / "worktree"

    if not worktree_path.exists():
        return

    worktree_branch = f"ve-worktree-{chunk}"
    target_branch = "main"
    _file_protocol_env = {
        **os.environ,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
    }

    for entity_dir in sorted(entities_dir.iterdir()):
        if not entity_dir.is_dir():
            continue
        # Submodule marker: .git is a file (not a directory)
        if not (entity_dir / ".git").is_file():
            continue

        name = entity_dir.name
        worktree_entity = worktree_path / ".entities" / name

        if not worktree_entity.exists():
            continue

        # Check if the worktree branch exists in the worktree entity.
        # Note: the worktree entity lives in a separate git module path from
        # the project entity (git creates a per-worktree module path for
        # submodules). We must fetch from the worktree entity into the project
        # entity to bridge the two separate module repos.
        verify = subprocess.run(
            ["git", "-C", str(worktree_entity), "rev-parse", "--verify", worktree_branch],
            capture_output=True, text=True,
        )
        if verify.returncode != 0:
            # No worktree branch — skip silently
            continue

        # Fetch the worktree entity branch into the project entity so we can
        # operate on both branches within a single repo.
        fetch = subprocess.run(
            ["git", "-C", str(entity_dir), "fetch",
             str(worktree_entity), f"{worktree_branch}:{worktree_branch}"],
            capture_output=True, text=True,
            env=_file_protocol_env,
        )
        if fetch.returncode != 0:
            logger.warning(
                "Failed to fetch worktree entity branch for %s: %s",
                name, fetch.stderr,
            )
            continue

        # Get SHAs for both branches (now both visible in project entity)
        source_result = subprocess.run(
            ["git", "-C", str(entity_dir), "rev-parse", worktree_branch],
            capture_output=True, text=True,
        )
        target_result = subprocess.run(
            ["git", "-C", str(entity_dir), "rev-parse", target_branch],
            capture_output=True, text=True,
        )
        if source_result.returncode != 0 or target_result.returncode != 0:
            logger.warning(
                "Could not resolve branches for entity %s: source=%s target=%s",
                name, source_result.stderr, target_result.stderr,
            )
            # Clean up fetched branch
            subprocess.run(
                ["git", "-C", str(entity_dir), "branch", "-D", worktree_branch],
                capture_output=True,
            )
            continue

        source_sha = source_result.stdout.strip()
        target_sha = target_result.stdout.strip()

        # Check if already merged (source is ancestor of target)
        ancestor_check = subprocess.run(
            ["git", "-C", str(entity_dir), "merge-base", "--is-ancestor",
             source_sha, target_sha],
            capture_output=True,
        )
        if ancestor_check.returncode == 0:
            # Already merged — just clean up the local branch
            subprocess.run(
                ["git", "-C", str(entity_dir), "branch", "-d", worktree_branch],
                capture_output=True,
            )
            continue

        # Check if fast-forward is possible (target is ancestor of source)
        ff_check = subprocess.run(
            ["git", "-C", str(entity_dir), "merge-base", "--is-ancestor",
             target_sha, source_sha],
            capture_output=True,
        )
        if ff_check.returncode == 0:
            # Fast-forward: update main ref to source_sha
            update = subprocess.run(
                ["git", "-C", str(entity_dir), "update-ref",
                 f"refs/heads/{target_branch}", source_sha],
                capture_output=True, text=True,
            )
            if update.returncode != 0:
                logger.warning(
                    "Fast-forward update failed for entity %s: %s",
                    name, update.stderr,
                )
                subprocess.run(
                    ["git", "-C", str(entity_dir), "branch", "-D", worktree_branch],
                    capture_output=True,
                )
                continue
        else:
            # Need a real merge — use git merge-tree (Git 2.38+)
            merge_tree = subprocess.run(
                ["git", "-C", str(entity_dir), "merge-tree",
                 "--write-tree", target_sha, source_sha],
                capture_output=True, text=True,
            )
            if merge_tree.returncode != 0:
                logger.warning(
                    "Merge conflict in entity %s (worktree branch %s vs main): %s",
                    name, worktree_branch, merge_tree.stderr,
                )
                subprocess.run(
                    ["git", "-C", str(entity_dir), "branch", "-D", worktree_branch],
                    capture_output=True,
                )
                continue

            new_tree = merge_tree.stdout.splitlines()[0].strip()

            # Create a merge commit
            commit_result = subprocess.run(
                ["git", "-C", str(entity_dir), "commit-tree", new_tree,
                 "-p", target_sha, "-p", source_sha,
                 "-m", f"Merge entity worktree branch {worktree_branch} into main"],
                capture_output=True, text=True,
                env={**os.environ, **_GIT_ENV},
            )
            if commit_result.returncode != 0:
                logger.warning(
                    "commit-tree failed for entity %s: %s",
                    name, commit_result.stderr,
                )
                subprocess.run(
                    ["git", "-C", str(entity_dir), "branch", "-D", worktree_branch],
                    capture_output=True,
                )
                continue

            new_commit = commit_result.stdout.strip()

            # Update the main branch ref
            update = subprocess.run(
                ["git", "-C", str(entity_dir), "update-ref",
                 f"refs/heads/{target_branch}", new_commit],
                capture_output=True, text=True,
            )
            if update.returncode != 0:
                logger.warning(
                    "update-ref failed for entity %s: %s",
                    name, update.stderr,
                )
                subprocess.run(
                    ["git", "-C", str(entity_dir), "branch", "-D", worktree_branch],
                    capture_output=True,
                )
                continue

        # Delete the fetched worktree branch from the project entity
        subprocess.run(
            ["git", "-C", str(entity_dir), "branch", "-d", worktree_branch],
            capture_output=True,
        )


def fork_entity(
    source_path: Path,
    dest_dir: Path,
    new_name: str,
) -> ForkResult:
    """Clone an entity repo to a new location with an updated name and lineage.

    Creates a full (non-shallow) clone of source_path at dest_dir/new_name,
    updates ENTITY.md with the new name and fork origin, and makes an initial
    commit recording the fork.

    Args:
        source_path: Path to the source entity repo directory.
        dest_dir: Parent directory where the fork will be created.
        new_name: Name for the new fork (must match ENTITY_REPO_NAME_PATTERN).

    Returns:
        ForkResult with source_name, new_name, and dest_path.

    Raises:
        ValueError: If source_path is not an entity repo, new_name is invalid,
                    or dest_dir/new_name already exists.
    """
    from frontmatter import update_frontmatter_field

    if not is_entity_repo(source_path):
        raise ValueError(
            f"'{source_path}' is not a valid entity repo (missing ENTITY.md)."
        )
    if not ENTITY_REPO_NAME_PATTERN.match(new_name):
        raise ValueError(
            f"Invalid entity name '{new_name}'. "
            "Name must start with a lowercase letter and contain only "
            "lowercase letters, digits, underscores, or hyphens."
        )
    dest_path = dest_dir / new_name
    if dest_path.exists():
        raise ValueError(
            f"Destination '{dest_path}' already exists. "
            "Choose a different name or remove the existing directory."
        )

    source_metadata = read_entity_metadata(source_path)

    # Ensure dest_dir exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clone with full history
    _run_git(
        dest_dir,
        "clone", str(source_path), new_name,
        extra_env={
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "protocol.file.allow",
            "GIT_CONFIG_VALUE_0": "always",
        },
    )

    # Update ENTITY.md in the clone
    entity_md = dest_path / "ENTITY.md"
    update_frontmatter_field(entity_md, "name", new_name)
    update_frontmatter_field(entity_md, "forked_from", source_metadata.name)

    # Commit the metadata update
    _git_commit_all(dest_path, f"Forked from {source_metadata.name}")

    return ForkResult(
        source_name=source_metadata.name,
        new_name=new_name,
        dest_path=dest_path,
    )


# Chunk: docs/chunks/entity_fork_merge - Merge entity repo implementation
def merge_entity(
    entity_path: Path,
    source: str,
    resolve_conflicts: bool = True,
) -> "MergeResult | MergeConflictsPending":
    """Fetch and merge learnings from a source entity into entity_path.

    Adds source as a temporary remote 've-merge-source', fetches it, and
    attempts a merge with --no-commit --no-ff. On clean merge, commits
    automatically. On conflicts in wiki markdown files, uses LLM-assisted
    synthesis. Non-wiki conflicts go to unresolvable list.

    Args:
        entity_path: Path to the target entity repo directory.
        source: URL or local path to the source entity repo.
        resolve_conflicts: If False, abort and raise on conflicts.

    Returns:
        MergeResult for a clean merge, or MergeConflictsPending if conflicts
        remain and need operator approval.

    Raises:
        ValueError: If entity_path is not a valid entity repo.
        RuntimeError: If entity has uncommitted changes, or merge fails for a
                      non-conflict reason, or resolve_conflicts=False with conflicts.
    """
    import os
    import entity_merge as _entity_merge

    if not is_entity_repo(entity_path):
        raise ValueError(
            f"'{entity_path}' is not a valid entity repo (missing ENTITY.md)."
        )

    # Require clean working tree
    status_out = _run_git_output(entity_path, "status", "--porcelain")
    if status_out.strip():
        raise RuntimeError(
            f"Entity '{entity_path.name}' has uncommitted changes. "
            "Commit or stash changes before merging."
        )

    _file_protocol_env = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
    }

    # Add temp remote
    _run_git(entity_path, "remote", "add", "ve-merge-source", source,
             extra_env=_file_protocol_env)

    try:
        # Fetch source
        _run_git(entity_path, "fetch", "ve-merge-source",
                 extra_env=_file_protocol_env)

        # Count commits to merge before the merge changes HEAD
        commits_out = _run_git_output(
            entity_path, "rev-list", "HEAD..ve-merge-source/main"
        )
        commits_merged = len([l for l in commits_out.splitlines() if l.strip()])

        # Attempt merge (don't use _run_git — conflicts return exit code 1)
        env = {**os.environ, **_GIT_ENV}
        merge_proc = subprocess.run(
            ["git", "-C", str(entity_path), "merge",
             "ve-merge-source/main", "--no-commit", "--no-ff",
             "--allow-unrelated-histories"],
            capture_output=True, text=True, env=env,
        )

        # Inspect staged status for conflicts or clean changes
        status_out = _run_git_output(entity_path, "status", "--porcelain")

        # Detect conflict lines
        _CONFLICT_XY = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
        conflict_files: list[str] = []
        for line in status_out.splitlines():
            if len(line) >= 2 and line[:2] in _CONFLICT_XY:
                conflict_files.append(line[3:])

        if not conflict_files and merge_proc.returncode != 0:
            # Unexpected failure
            raise RuntimeError(
                f"git merge failed (non-conflict): {merge_proc.stderr.strip()}"
            )

        if not conflict_files:
            # Clean merge (or already up to date)
            new_pages = 0
            updated_pages = 0
            for line in status_out.splitlines():
                if len(line) >= 3:
                    x = line[0]
                    filepath = line[3:]
                    if filepath.startswith("wiki/") and filepath.endswith(".md"):
                        if x == "A":
                            new_pages += 1
                        elif x == "M":
                            updated_pages += 1

            if commits_merged > 0:
                _run_git(entity_path, "add", "-A")
                _run_git(
                    entity_path, "commit",
                    "-m", f"Merge learnings from {source}"
                )

            return MergeResult(
                source=source,
                commits_merged=commits_merged,
                new_pages=new_pages,
                updated_pages=updated_pages,
            )

        # Conflicts present
        if not resolve_conflicts:
            try:
                _run_git(entity_path, "merge", "--abort")
            except RuntimeError:
                pass
            raise RuntimeError(
                f"Merge conflicts in: {', '.join(conflict_files)}"
            )

        resolutions: list[ConflictResolution] = []
        unresolvable: list[str] = []

        for filepath in conflict_files:
            full_path = entity_path / filepath
            is_wiki = filepath.startswith("wiki/") and filepath.endswith(".md")
            if full_path.exists() and is_wiki:
                content = full_path.read_text()
                try:
                    synthesized = _entity_merge.resolve_wiki_conflict(
                        filepath, content, entity_path.name
                    )
                    resolutions.append(ConflictResolution(
                        relative_path=filepath,
                        synthesized=synthesized,
                        is_wiki=True,
                    ))
                except RuntimeError:
                    unresolvable.append(filepath)
            else:
                unresolvable.append(filepath)

        return MergeConflictsPending(
            source=source,
            resolutions=resolutions,
            unresolvable=unresolvable,
        )

    finally:
        # Always remove temp remote to avoid state leakage
        try:
            _run_git(entity_path, "remote", "remove", "ve-merge-source")
        except RuntimeError:
            pass


# Chunk: docs/chunks/entity_fork_merge - Commit resolved merge
def commit_resolved_merge(
    entity_path: Path,
    resolutions: list[ConflictResolution],
    source_name: str,
) -> None:
    """Write resolved conflict content, stage all files, and complete the merge commit.

    Args:
        entity_path: Path to the entity repo directory.
        resolutions: List of resolved conflicts (each with synthesized content).
        source_name: Source identifier to use in the commit message.
    """
    for resolution in resolutions:
        dest = entity_path / resolution.relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(resolution.synthesized)

    _run_git(entity_path, "add", "-A")
    _run_git(entity_path, "commit", "-m", f"Merge learnings from {source_name}")


# Chunk: docs/chunks/entity_fork_merge - Abort in-progress merge
def abort_merge(entity_path: Path) -> None:
    """Abort an in-progress merge, restoring the entity to pre-merge state.

    Args:
        entity_path: Path to the entity repo directory.
    """
    _run_git(entity_path, "merge", "--abort")


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


# ---------------------------------------------------------------------------
# Wiki rename
# ---------------------------------------------------------------------------

# Chunk: docs/chunks/wiki_rename_command - Wikilink pattern for rewriting references
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(\|[^\]]+?)?\]\]")


def _rewrite_wikilinks(
    filepath: Path,
    old_path: str,
    new_path: str,
    old_stem: str,
    new_stem: str,
) -> bool:
    """Rewrite wikilinks in a markdown file. Returns True if the file was modified.

    Matches [[old_path]] and [[old_stem]] (bare filename without directory),
    replacing with [[new_path]] and [[new_stem]] respectively.
    Display text (e.g., [[target|Display]]) is preserved.
    """
    content = filepath.read_text(encoding="utf-8")

    def _replace(m: re.Match) -> str:
        target = m.group(1).strip()
        display = m.group(2) or ""  # includes the leading "|" if present
        if target == old_path:
            return f"[[{new_path}{display}]]"
        if target == old_stem and old_stem != new_stem:
            return f"[[{new_stem}{display}]]"
        return m.group(0)

    new_content = _WIKILINK_RE.sub(_replace, content)
    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return True
    return False


# Chunk: docs/chunks/wiki_rename_command - Rename a wiki page and rewrite inbound wikilinks
def wiki_rename(entity_path: Path, old_path: str, new_path: str) -> WikiRenameResult:
    """Rename a wiki page and update all inbound wikilinks.

    Moves the page from old_path to new_path within the entity's wiki
    directory, then rewrites all [[wikilinks]] across every wiki .md file
    that referenced the old path or its bare filename stem.

    Args:
        entity_path: Root of the entity repo (must contain a wiki/ directory).
        old_path: Relative path to the current page within wiki/, without the
                  .md extension (e.g., "domain/world-model").
        new_path: Relative path for the renamed page within wiki/, without the
                  .md extension (e.g., "domain/world-model-v2").

    Returns:
        WikiRenameResult with count of wiki files that had wikilinks rewritten.

    Raises:
        ValueError: If wiki/ doesn't exist, old_path doesn't exist, or
                    new_path already exists.
    """
    wiki_dir = entity_path / "wiki"
    if not wiki_dir.is_dir():
        raise ValueError(f"Entity at '{entity_path}' has no wiki/ directory")

    old_file = wiki_dir / f"{old_path}.md"
    new_file = wiki_dir / f"{new_path}.md"

    if not old_file.exists():
        raise ValueError(f"Wiki page '{old_path}' not found")

    if new_file.exists():
        raise ValueError(f"Wiki page '{new_path}' already exists")

    # Create parent directory for the destination if needed
    new_file.parent.mkdir(parents=True, exist_ok=True)

    # Move the file
    old_file.rename(new_file)

    # Derive stems for matching bare-stem wikilinks (e.g., [[world-model]])
    old_stem = Path(old_path).name
    new_stem = Path(new_path).name

    # Rewrite wikilinks across all wiki .md files (including the renamed file)
    files_updated = 0
    for md_file in sorted(wiki_dir.rglob("*.md")):
        if _rewrite_wikilinks(md_file, old_path, new_path, old_stem, new_stem):
            files_updated += 1

    return WikiRenameResult(
        files_updated=files_updated,
        old_path=old_path,
        new_path=new_path,
    )


# ---------------------------------------------------------------------------
# Wiki reindex
# ---------------------------------------------------------------------------

# Chunk: docs/chunks/wiki_reindex_command - Result of wiki reindex operation
@dataclass
class WikiReindexResult:
    pages_total: int          # total pages written to index
    directories_scanned: int  # number of subdirectories scanned


def _parse_existing_summaries(index_path: Path) -> dict[str, str]:
    """Extract page→summary mapping from existing index.md.

    Parses markdown table rows of the form:
        | [[page_stem]] | summary text |
    Returns a dict mapping page stem to summary string.
    Returns empty dict if index doesn't exist or has no table rows.
    """
    if not index_path.exists():
        return {}
    summaries: dict[str, str] = {}
    pattern = re.compile(r"\|\s*\[\[([^\]]+)\]\]\s*\|\s*(.*?)\s*\|")
    for line in index_path.read_text().splitlines():
        m = pattern.search(line)
        if m:
            stem, summary = m.group(1), m.group(2)
            summaries[stem] = summary
    return summaries


def _scan_wiki_pages(wiki_dir: Path) -> dict[str, list[dict]]:
    """Scan wiki directory and return pages grouped by section.

    Returns:
        {
            "core": [{"stem": ..., "title": ..., "path": ...}, ...],
            "domain": [...],
            "techniques": [...],
            "projects": [...],
            "relationships": [...],
        }
    Keys always present; values are lists (may be empty).
    """
    import yaml as _yaml

    _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
    _EXCLUDE_CORE = {"index.md", "wiki_schema.md", "SOP.md"}

    def _get_title(md_path: Path) -> str:
        try:
            content = md_path.read_text()
            m = _FRONTMATTER_RE.match(content)
            if m:
                data = _yaml.safe_load(m.group(1)) or {}
                if isinstance(data, dict) and data.get("title"):
                    return str(data["title"])
        except Exception:
            pass
        return md_path.stem.replace("_", " ").title()

    def _pages_in(directory: Path) -> list[dict]:
        if not directory.is_dir():
            return []
        pages = []
        for f in directory.glob("*.md"):
            pages.append({"stem": f.stem, "title": _get_title(f), "path": f})
        pages.sort(key=lambda p: p["title"].lower())
        return pages

    # Core pages: root-level .md files, excluding reserved names
    core_pages = []
    for f in wiki_dir.glob("*.md"):
        if f.name not in _EXCLUDE_CORE:
            core_pages.append({"stem": f.stem, "title": _get_title(f), "path": f})
    core_pages.sort(key=lambda p: p["title"].lower())

    return {
        "core": core_pages,
        "domain": _pages_in(wiki_dir / "domain"),
        "techniques": _pages_in(wiki_dir / "techniques"),
        "projects": _pages_in(wiki_dir / "projects"),
        "relationships": _pages_in(wiki_dir / "relationships"),
    }


def _generate_index_md(
    sections: dict[str, list[dict]],
    summaries: dict[str, str],
    entity_name: str,
    created: str | None = None,
) -> str:
    """Render the full index.md content from scanned pages."""
    now_iso = datetime.now(timezone.utc).isoformat()

    fm_lines = [f"title: Wiki Index — {entity_name}", f"updated: {now_iso}"]
    if created:
        fm_lines.insert(1, f"created: {created}")
    frontmatter = "---\n" + "\n".join(fm_lines) + "\n---"

    def _table(pages: list[dict]) -> str:
        lines = ["| Page | Summary |", "|------|---------|"]
        for page in pages:
            summary = summaries.get(page["stem"], "")
            lines.append(f"| [[{page['stem']}]] | {summary} |")
        return "\n".join(lines)

    section_map = [
        ("Core", sections["core"]),
        ("Domain Knowledge", sections["domain"]),
        ("Projects", sections["projects"]),
        ("Techniques", sections["techniques"]),
        ("Relationships", sections["relationships"]),
    ]

    parts = [
        frontmatter,
        "",
        "# Wiki Index",
        "",
        f"Personal knowledge base for `{entity_name}`.",
        "",
        "<!-- Keep this index current. Every page you create should appear here. One-line summaries only. -->",
        "",
    ]

    for heading, pages in section_map:
        parts.append(f"## {heading}")
        parts.append("")
        parts.append(_table(pages))
        parts.append("")

    return "\n".join(parts)


# Chunk: docs/chunks/wiki_reindex_command - Regenerate index.md from page frontmatter
def reindex_wiki(wiki_dir: Path, entity_name: str | None = None) -> WikiReindexResult:
    """Regenerate wiki/index.md from page frontmatter.

    Scans all wiki pages, reads their frontmatter, and overwrites
    index.md with a fresh table grouped by directory. Existing
    summaries are preserved for pages that still exist.

    Args:
        wiki_dir: Path to the entity's wiki/ directory.
        entity_name: Optional entity name for the index title.
                     Falls back to wiki_dir.parent.name.

    Raises:
        FileNotFoundError: If wiki_dir does not exist.
    """
    import yaml as _yaml

    if not wiki_dir.exists():
        raise FileNotFoundError(f"Wiki directory not found: {wiki_dir}")

    if entity_name is None:
        entity_name = wiki_dir.parent.name

    index_path = wiki_dir / "index.md"

    # Preserve summaries and created date from existing index
    summaries = _parse_existing_summaries(index_path)
    created: str | None = None
    if index_path.exists():
        _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
        m = _FRONTMATTER_RE.match(index_path.read_text())
        if m:
            try:
                data = _yaml.safe_load(m.group(1)) or {}
                if isinstance(data, dict):
                    created = data.get("created")
                    if created is not None:
                        created = str(created)
            except Exception:
                pass

    sections = _scan_wiki_pages(wiki_dir)
    content = _generate_index_md(sections, summaries, entity_name, created=created)
    index_path.write_text(content)

    pages_total = sum(len(v) for v in sections.values())
    # Count subdirectories that exist (not counting core)
    directories_scanned = sum(
        1 for key in ("domain", "techniques", "projects", "relationships")
        if (wiki_dir / key).is_dir()
    )

    return WikiReindexResult(pages_total=pages_total, directories_scanned=directories_scanned)


# ---------------------------------------------------------------------------
# Wiki lint helpers and main function
# ---------------------------------------------------------------------------

_LINT_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_wikilinks(content: str) -> list[str]:
    """Return all [[target]] link targets found in content."""
    return _LINT_WIKILINK_RE.findall(content)


def _resolve_wikilink(wiki_dir: Path, target: str) -> Path | None:
    """Resolve a wikilink target to an absolute Path, or None if not found.

    Resolution rules:
    - If target contains '/' → look for wiki_dir / target (with .md appended if needed)
    - If no '/' → Obsidian shortest-path: search all .md files recursively for <target>.md
    """
    if not target.endswith(".md"):
        target_with_ext = target + ".md"
    else:
        target_with_ext = target

    if "/" in target:
        candidate = wiki_dir / target_with_ext
        return candidate if candidate.exists() else None
    else:
        # Obsidian shortest-path: find any file named <target>.md in the wiki tree
        for candidate in wiki_dir.rglob(target_with_ext):
            return candidate  # return first match
        return None


def _get_index_references(index_content: str) -> set[str]:
    """Return the set of bare stem names referenced via wikilinks in index.md."""
    targets = _extract_wikilinks(index_content)
    return {t.split("/")[-1] for t in targets}  # bare name only (no dir prefix)


# Chunk: docs/chunks/wiki_lint_command - Wiki integrity linting
def lint_wiki(wiki_dir: Path) -> WikiLintResult:
    """Lint a wiki directory for integrity issues.

    Checks dead wikilinks, frontmatter errors, pages missing from the index,
    and orphan pages (no inbound wikilinks from any page).

    Args:
        wiki_dir: Path to the entity's wiki/ directory.

    Returns:
        WikiLintResult with zero or more issues.
    """
    from frontmatter import _FRONTMATTER_PATTERN  # reuse existing regex

    issues: list[WikiLintIssue] = []

    # Structural pages that live at the wiki root and are exempt from content checks.
    STRUCTURAL_NAMES = {"index.md", "wiki_schema.md", "identity.md", "log.md", "SOP.md"}
    # Pages exempt from the frontmatter check (no frontmatter by design)
    NO_FRONTMATTER = {"wiki_schema.md"}

    all_pages = list(wiki_dir.rglob("*.md"))

    # Build inbound link map: rel_path_str -> set of source rel_path_strs
    inbound: dict[str, set[str]] = {
        str(p.relative_to(wiki_dir)): set() for p in all_pages
    }

    # --- Pass 1: per-page checks + populate inbound map ---
    for page in all_pages:
        rel = str(page.relative_to(wiki_dir))
        content = page.read_text(encoding="utf-8", errors="replace")

        # 1. Frontmatter check
        if page.name not in NO_FRONTMATTER:
            fm_match = _FRONTMATTER_PATTERN.search(content)
            if not fm_match:
                issues.append(WikiLintIssue(rel, "frontmatter_error", "missing frontmatter"))
            else:
                try:
                    yaml.safe_load(fm_match.group(1))
                except yaml.YAMLError as exc:
                    issues.append(
                        WikiLintIssue(rel, "frontmatter_error", f"invalid YAML: {exc}")
                    )

        # 2. Wikilink extraction → dead link check + inbound map population
        for target in _extract_wikilinks(content):
            resolved = _resolve_wikilink(wiki_dir, target)
            if resolved is None:
                issues.append(WikiLintIssue(rel, "dead_wikilink", f"[[{target}]] not found"))
            else:
                target_rel = str(resolved.relative_to(wiki_dir))
                if target_rel in inbound:
                    inbound[target_rel].add(rel)

    # --- Pass 2: index coverage check ---
    index_path = wiki_dir / "index.md"
    if index_path.exists():
        index_refs = _get_index_references(
            index_path.read_text(encoding="utf-8", errors="replace")
        )
        for page in all_pages:
            if page.name in STRUCTURAL_NAMES:
                continue
            if page.parent == wiki_dir:
                # Root-level non-structural files (unusual) — skip silently
                continue
            # Content pages are those in subdirectories (domain/, projects/, etc.)
            rel = str(page.relative_to(wiki_dir))
            if page.stem not in index_refs:
                issues.append(
                    WikiLintIssue(rel, "missing_from_index", "no entry in index.md")
                )

    # --- Pass 3: orphan check ---
    for page in all_pages:
        if page.name in STRUCTURAL_NAMES or page.parent == wiki_dir:
            continue  # exempt structural + root-level pages
        rel = str(page.relative_to(wiki_dir))
        if not inbound.get(rel):
            issues.append(WikiLintIssue(rel, "orphan_page", "no inbound wikilinks"))

    return WikiLintResult(issues=issues)
