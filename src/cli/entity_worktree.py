"""Worktree-based entity attach/detach.

# Chunk: docs/chunks/entity_worktree_attach - Replace submodule-based attach with worktree-based attach

This module owns the worktree-based implementation of ``ve entity attach``
and ``ve entity detach``. It is the seam through which both the Click CLI
(``cli.entity``) and the downstream ``ve entity claude`` auto-attach pathway
(``entity_claude_autoattach``) materialize an entity into ``.entities/<name>``.

The implementation composes two pieces from earlier chunks:

- ``cli.config.load_config`` resolves the operator config
  (``~/.ve-config.toml``) to discover where canonical clones live.
- ``cli.canonical_clone.ensure_canonical_clone`` guarantees the canonical
  clone at ``<entities_dir>/<name>`` exists before we ``git worktree add``
  from it.

The on-disk shape of an attached entity matches the pre-1.0 submodule
shape — ``.entities/<name>/`` with the same directory layout — so every
downstream command that reads from ``.entities/<name>/identity.md``,
``memories/``, ``wiki/``, or ``touch_log.jsonl`` keeps working without
modification.

Per the narrative's "clean break" decision, this module never touches
``.gitmodules`` or invokes ``git submodule``. The pre-1.0 submodule
machinery has been deleted in the same chunk.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
from dataclasses import dataclass

from cli.canonical_clone import ensure_canonical_clone
from cli.config import ConfigError, load_config


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WorktreeAttachError(Exception):
    """Raised for worktree-based attach/detach failures that are not config
    or canonical-clone errors.

    Examples: the project directory isn't a git repo, ``.entities/<name>``
    already exists as a non-worktree directory, ``git worktree add``
    failed, the worktree has uncommitted changes and ``--force`` was not
    passed.
    """


# ---------------------------------------------------------------------------
# Public result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttachResult:
    """Outcome of a successful ``do_attach`` call.

    Attributes:
        name: Entity identifier (as passed in).
        entity_path: Absolute path to ``<project_dir>/.entities/<name>``.
        canonical_clone: Absolute path to the canonical clone in
            ``<entities_dir>/<name>``. Useful for the auto-attach pathway
            to display "where the clone lives" in its onboarding output.
        branch: Project-scoped branch the worktree was checked out on.
        already_attached: True iff the entity was already attached to this
            project — ``do_attach`` is idempotent and treats this as a
            no-op rather than an error.
    """

    name: str
    entity_path: pathlib.Path
    canonical_clone: pathlib.Path
    branch: str
    already_attached: bool


# ---------------------------------------------------------------------------
# Project-scoped branch naming
# ---------------------------------------------------------------------------


_SLUG_NON_ALPHANUM = re.compile(r"[^a-z0-9]+")


def project_slug(project_dir: pathlib.Path) -> str:
    """Return a deterministic, branch-safe slug for ``project_dir``.

    The slug is derived from the directory basename: lowercased, with each
    run of non-``[a-z0-9]`` characters collapsed to a single ``-``, and
    leading/trailing ``-`` stripped.

    Used to scope the canonical clone's worktree branch so two projects on
    the same machine can attach the same entity simultaneously without
    colliding on git's "one worktree per branch" constraint.

    Examples:
        ``/Users/x/Projects/vibe-engineer`` → ``vibe-engineer``
        ``/var/tmp/Foo Bar 1.2`` → ``foo-bar-1-2``
        ``/tmp/_internal_`` → ``internal``

    Args:
        project_dir: Project directory whose basename feeds the slug.

    Returns:
        The slug string.

    Raises:
        ValueError: If the slug is empty after normalization (pathological
            path basenames such as ``///`` or all-punctuation).
    """
    name = project_dir.name.lower()
    slug = _SLUG_NON_ALPHANUM.sub("-", name).strip("-")
    if not slug:
        raise ValueError(
            f"Cannot derive project slug from directory name "
            f"{project_dir.name!r}"
        )
    return slug


def attach_branch_name(project_dir: pathlib.Path) -> str:
    """Return the project-scoped branch the canonical clone's worktree
    should be checked out on for ``project_dir``.

    Format: ``ve-attach/<project_slug>``. The ``ve-attach/`` prefix
    namespaces these branches under the canonical clone's ref hierarchy
    so they're easy to identify and delete during detach.

    Args:
        project_dir: Project directory whose attachment we're naming.

    Returns:
        Branch name suitable for ``git worktree add -b <branch>``.
    """
    return f"ve-attach/{project_slug(project_dir)}"


# ---------------------------------------------------------------------------
# Worktree-of-canonical detection
# ---------------------------------------------------------------------------


def _is_worktree_of(
    entity_path: pathlib.Path,
    canonical_clone: pathlib.Path,
) -> bool:
    """Return True iff ``entity_path`` is a git worktree backed by
    ``canonical_clone``.

    A linked git worktree has a ``.git`` file (not a directory) whose
    first non-empty line is ``gitdir: <abs-path-into-canonical>/.git/worktrees/<wt-name>``.
    We resolve both paths before comparing to handle symlinks in the
    entities_dir path.
    """
    git_marker = entity_path / ".git"
    if not git_marker.is_file():
        return False
    try:
        content = git_marker.read_text(encoding="utf-8")
    except OSError:
        return False
    gitdir: pathlib.Path | None = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("gitdir:"):
            gitdir = pathlib.Path(line[len("gitdir:"):].strip())
            break
    if gitdir is None:
        return False
    try:
        gitdir_resolved = gitdir.resolve()
        canonical_resolved = canonical_clone.resolve()
    except OSError:
        return False
    worktrees_root = canonical_resolved / ".git" / "worktrees"
    try:
        gitdir_resolved.relative_to(worktrees_root)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# Internal git helpers
# ---------------------------------------------------------------------------


def _run_git(
    cwd: pathlib.Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a ``git`` invocation in ``cwd`` and return the completed proc.

    When ``check=True`` (the default), a non-zero exit raises
    ``WorktreeAttachError`` with the stderr appended.
    """
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise WorktreeAttachError(
            f"git {' '.join(args)} failed in {cwd}: {proc.stderr.strip()}"
        )
    return proc


def _resolve_default_branch(canonical: pathlib.Path) -> str:
    """Return the canonical clone's default branch name (e.g. ``main``).

    Prefers ``refs/remotes/origin/HEAD`` because the canonical clone is
    almost always created by ``ensure_canonical_clone`` via ``git clone``,
    which sets that ref. Falls back to ``main`` so local-only test setups
    (bare repos cloned without a remote) still work.
    """
    proc = _run_git(
        canonical, "symbolic-ref", "refs/remotes/origin/HEAD", check=False,
    )
    if proc.returncode == 0:
        ref = proc.stdout.strip()
        prefix = "refs/remotes/origin/"
        if ref.startswith(prefix):
            return ref[len(prefix):]
    # Fallback: probe for a branch literally named "main" or "master".
    for candidate in ("main", "master"):
        if _run_git(
            canonical, "show-ref", "--verify", "--quiet",
            f"refs/heads/{candidate}", check=False,
        ).returncode == 0:
            return candidate
    return "main"


def _branch_exists(canonical: pathlib.Path, branch: str) -> bool:
    """Return True iff ``branch`` exists as a local branch in ``canonical``."""
    return _run_git(
        canonical, "show-ref", "--verify", "--quiet",
        f"refs/heads/{branch}", check=False,
    ).returncode == 0


def _is_git_repo(project_dir: pathlib.Path) -> bool:
    """Return True iff ``project_dir`` is inside a git work tree."""
    proc = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "--git-dir"],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Public attach / detach
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/entity_claude_autoattach - Public predicate for the
# auto-attach pathway: lets `ve entity claude` short-circuit progress output
# when the entity is already attached without invoking git or the network.
def is_attached(
    name: str,
    project_dir: pathlib.Path,
    *,
    config_path: pathlib.Path | None = None,
) -> bool:
    """Return True iff ``name`` is attached to ``project_dir`` as a
    worktree of ``<entities_dir>/<name>``.

    Cheap: reads the operator config and probes the ``.git`` marker
    file. Never invokes git, never touches the network. When the
    operator config is missing or malformed, returns ``False`` rather
    than raising — the caller will hit the same ``ConfigError`` path
    when it proceeds to ``do_attach``.

    Args:
        name: Entity identifier.
        project_dir: Project to probe.
        config_path: Override the operator config file. Primarily for
            tests.

    Returns:
        ``True`` iff ``<project_dir>/.entities/<name>`` is a worktree
        whose gitdir points into ``<entities_dir>/<name>/.git/worktrees``.
    """
    try:
        cfg = load_config(config_path)
    except ConfigError:
        return False
    entity_path = project_dir / ".entities" / name
    if not entity_path.exists():
        return False
    canonical = cfg.entities_dir / name
    return _is_worktree_of(entity_path, canonical)


def do_attach(
    name: str,
    project_dir: pathlib.Path,
    *,
    config_path: pathlib.Path | None = None,
) -> AttachResult:
    """Attach entity ``name`` to ``project_dir`` as a git worktree.

    Composes :func:`cli.canonical_clone.ensure_canonical_clone` to make
    sure ``<entities_dir>/<name>`` is on disk, then runs ``git worktree
    add`` to materialize ``<project_dir>/.entities/<name>`` on a
    project-scoped branch (``ve-attach/<project_slug>``).

    Idempotent: if ``.entities/<name>`` already exists and is a worktree
    backed by the canonical clone, returns ``AttachResult(..., already_attached=True)``
    without touching anything on disk.

    Args:
        name: Entity identifier (same value the canonical-clone helper
            expects).
        project_dir: Project the entity will be attached to. Must be a
            git work tree.
        config_path: Override the operator config file (forwarded to
            ``ensure_canonical_clone`` and ``load_config``). Primarily
            for tests.

    Returns:
        :class:`AttachResult` describing the resulting attachment.

    Raises:
        ValueError: If ``name`` is structurally invalid (propagated from
            ``ensure_canonical_clone``).
        cli.config.ConfigError: If the operator config is missing or
            malformed.
        cli.canonical_clone.CanonicalCloneError: Any clone-time failure
            (auth, missing remote, network, or other).
        WorktreeAttachError: If ``project_dir`` isn't a git repo, if
            ``.entities/<name>`` already exists as a non-worktree
            directory, or if ``git worktree add`` failed.
    """
    if not _is_git_repo(project_dir):
        raise WorktreeAttachError(
            f"'{project_dir}' is not a git repository"
        )

    canonical = ensure_canonical_clone(name, config_path=config_path)

    entity_path = project_dir / ".entities" / name
    branch = attach_branch_name(project_dir)

    if entity_path.exists():
        if _is_worktree_of(entity_path, canonical):
            return AttachResult(
                name=name,
                entity_path=entity_path,
                canonical_clone=canonical,
                branch=branch,
                already_attached=True,
            )
        raise WorktreeAttachError(
            f"'{entity_path}' already exists but is not an attached "
            f"worktree of {canonical}. Remove or rename it and retry."
        )

    entity_path.parent.mkdir(parents=True, exist_ok=True)

    if _branch_exists(canonical, branch):
        # Reuse an existing project-scoped branch (e.g. a previous detach
        # didn't run, or a parallel project shares this slug — rare).
        _run_git(
            canonical, "worktree", "add", str(entity_path), branch,
        )
    else:
        base_ref = _resolve_default_branch(canonical)
        _run_git(
            canonical, "worktree", "add", "-b", branch,
            str(entity_path), base_ref,
        )

    return AttachResult(
        name=name,
        entity_path=entity_path,
        canonical_clone=canonical,
        branch=branch,
        already_attached=False,
    )


def do_detach(
    name: str,
    project_dir: pathlib.Path,
    *,
    config_path: pathlib.Path | None = None,
    force: bool = False,
) -> None:
    """Detach entity ``name`` from ``project_dir``.

    Removes the worktree at ``<project_dir>/.entities/<name>`` via
    ``git worktree remove`` and deletes the project-scoped branch from
    the canonical clone. The canonical clone itself
    (``<entities_dir>/<name>``) is left untouched and reusable by future
    attaches.

    Args:
        name: Entity identifier.
        project_dir: Project the entity is currently attached to.
        config_path: Override the operator config file. Primarily for tests.
        force: When True, detach even if the worktree has uncommitted
            changes. Defaults to False.

    Raises:
        WorktreeAttachError: If the entity is not attached, if
            ``.entities/<name>`` isn't a worktree, or if it has
            uncommitted changes and ``force=False``.
        cli.config.ConfigError: If the operator config is missing or
            malformed (we still need it to locate the canonical clone).
    """
    entity_path = project_dir / ".entities" / name
    if not entity_path.exists():
        raise WorktreeAttachError(
            f"Entity '{name}' is not attached at '{entity_path}'"
        )

    cfg = load_config(config_path)
    canonical = cfg.entities_dir / name

    if not _is_worktree_of(entity_path, canonical):
        raise WorktreeAttachError(
            f"'{entity_path}' is not an attached worktree of "
            f"'{canonical}'. Refusing to detach an unrecognized directory."
        )

    status = _run_git(
        entity_path, "status", "--porcelain", check=False,
    )
    if status.returncode == 0 and status.stdout.strip() and not force:
        raise WorktreeAttachError(
            f"Entity '{name}' has uncommitted changes. "
            "Use --force to detach anyway."
        )

    branch = attach_branch_name(project_dir)

    remove_args = ["worktree", "remove"]
    if force:
        remove_args.append("--force")
    remove_args.append(str(entity_path))
    _run_git(canonical, *remove_args)

    # Delete the project-scoped branch. Use -D to be tolerant of branches
    # whose tip isn't merged upstream — a worktree-side detach should not
    # require a clean push history. Ignore "branch not found" so a
    # second detach (e.g. after a half-failed first attempt) succeeds.
    _run_git(
        canonical, "branch", "-D", branch, check=False,
    )
