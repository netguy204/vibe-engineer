"""Canonical entity-clone helper.

# Chunk: docs/chunks/entity_canonical_clone - Ensure entities_dir/<name> is a clone of git_base/<name>.git

This module owns one job: given an entity name N, guarantee that
``<entities_dir>/<N>`` exists as a working git clone of
``<git_base>/<N>.git``. It is consumed in-process by the next chunks
(``entity_worktree_attach`` and ``entity_claude_autoattach``) and is the
single substrate that all "is this entity available on disk yet" questions
flow through.

The helper is **idempotent**: a second call is a fast existence check, not
a ``git pull``. Sync semantics belong to a hypothetical future
``ve entity sync`` command and are deliberately kept out of this module so
re-attach paths don't surprise users with unexpected network fetches.

The three real failure modes — authentication failure, missing remote
repository, and network failure — surface as distinguishable exception
subclasses so downstream callers can give the user actionable guidance
(check your auth vs. check your typo vs. check your network).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

from cli.config import VeConfig, load_config


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class CanonicalCloneError(Exception):
    """Base class for canonical-clone failures.

    Carries the entity name and the clone URL that was attempted so any
    surface that catches this can render a consistent error message
    without having to reconstruct the URL.

    Attributes:
        entity_name: The entity name that the helper was asked to ensure.
        clone_url: The full URL the helper tried to clone from.
    """

    def __init__(self, message: str, *, entity_name: str, clone_url: str) -> None:
        super().__init__(message)
        self.entity_name = entity_name
        self.clone_url = clone_url


class AuthFailure(CanonicalCloneError):
    """Git rejected our credentials.

    Surfaced separately so callers can say "check your SSH key / token"
    instead of conflating it with a typoed entity name or a dead network.
    """


class MissingRemoteRepo(CanonicalCloneError):
    """The git host says the repository does not exist.

    Almost always a typoed entity name or a misconfigured ``git_base``.
    The error message names both the entity and the full URL so the user
    can spot the mistake without reading a git stderr dump.
    """


class NetworkFailure(CanonicalCloneError):
    """We could not reach the git host at all.

    DNS failure, refused connection, timeout, or unreachable network.
    Distinct from auth and missing-repo so a retry-with-backoff hint is
    appropriate while "check your credentials" is not.
    """


# ---------------------------------------------------------------------------
# Stderr classification
# ---------------------------------------------------------------------------
#
# Git's exit code is always nonzero on failure, so we read stderr to figure
# out *why* it failed. The substrings below were picked from observed git
# stderr across versions 2.30+ on GitHub, GitLab, and Bitbucket (HTTPS and
# SSH). They are intentionally narrow: any unrecognized stderr falls
# through to a plain `CanonicalCloneError` rather than getting
# misclassified, so users see the raw git error and can act on it.
#
# Order matters in `_classify_clone_error`: auth is checked before missing-
# repo because auth-denied stderr is the most distinctive (it always
# includes "denied" or "authentication failed"), and missing-repo is
# checked before network because some hosts respond to a 404 with text
# that overlaps with generic network error wording.

_AUTH_PATTERNS: tuple[str, ...] = (
    "Permission denied",
    "authentication failed",
    "could not read Username",
    "fatal: Authentication failed",
    "Invalid username or password",
)

_MISSING_REPO_PATTERNS: tuple[str, ...] = (
    "Repository not found",
    "does not exist",
    "not found",
    "ERROR: Repository",
    "404",
)

_NETWORK_PATTERNS: tuple[str, ...] = (
    "Could not resolve host",
    "Connection refused",
    "Connection timed out",
    "Network is unreachable",
    "Operation timed out",
    "unable to access",
    "Failed to connect",
)


def _stderr_matches(stderr: str, patterns: tuple[str, ...]) -> bool:
    """Return True iff any pattern appears (case-insensitive) in stderr."""
    lower = stderr.lower()
    return any(p.lower() in lower for p in patterns)


def _classify_clone_error(
    stderr: str,
    *,
    name: str,
    clone_url: str,
) -> CanonicalCloneError:
    """Classify a failed ``git clone`` stderr into one of our exception types.

    Returns the constructed exception (the caller raises it). Order of
    checks: auth, then missing-repo, then network, then fallback. Any
    unrecognized stderr produces a plain :class:`CanonicalCloneError` with
    the raw stderr appended so unexpected failures still surface clearly.
    """
    stripped = stderr.strip()

    if _stderr_matches(stripped, _AUTH_PATTERNS):
        return AuthFailure(
            f"Authentication failed when cloning entity '{name}' from {clone_url}. "
            f"Check your git credentials (SSH key, token, or username) "
            f"for the host that serves {clone_url}.",
            entity_name=name,
            clone_url=clone_url,
        )

    if _stderr_matches(stripped, _MISSING_REPO_PATTERNS):
        return MissingRemoteRepo(
            f"No repository at {clone_url} (entity '{name}' not found). "
            f"Check that the entity name is spelled correctly and that "
            f"the repository exists under the configured git_base.",
            entity_name=name,
            clone_url=clone_url,
        )

    if _stderr_matches(stripped, _NETWORK_PATTERNS):
        return NetworkFailure(
            f"Network failure when cloning entity '{name}' from {clone_url}. "
            f"Check your network connection and DNS, then retry.",
            entity_name=name,
            clone_url=clone_url,
        )

    return CanonicalCloneError(
        f"Failed to clone entity '{name}' from {clone_url}.\n"
        f"git stderr:\n{stripped}",
        entity_name=name,
        clone_url=clone_url,
    )


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------


def _validate_entity_name(name: str) -> None:
    """Reject names that would escape ``entities_dir`` or be ambiguous.

    Path separators and leading dots are the two ways a caller could
    accidentally turn an entity name into a relative-path escape. Empty
    names are similarly nonsensical. These are programmer errors (the
    helper should never be handed a tainted name from a CLI prompt), so
    we raise plain ``ValueError`` rather than a CanonicalCloneError.
    """
    if not name:
        raise ValueError("entity name must not be empty")
    if "/" in name or "\\" in name:
        raise ValueError(
            f"entity name {name!r} must not contain path separators"
        )
    if name.startswith("."):
        raise ValueError(
            f"entity name {name!r} must not begin with '.'"
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _is_existing_clone(dest: pathlib.Path) -> bool:
    """Cheap probe for "this directory is a usable git clone."

    A standalone clone has a ``.git`` directory; a worktree-host repo has
    a ``.git`` file. Either counts as "already cloned" for our purposes.
    """
    return dest.is_dir() and (dest / ".git").exists()


def ensure_canonical_clone(
    name: str,
    *,
    config_path: pathlib.Path | None = None,
) -> pathlib.Path:
    """Ensure ``<entities_dir>/<name>`` exists as a clone of ``<git_base>/<name>.git``.

    Idempotent: when the destination already exists as a git clone, no
    network calls and no git invocations are made — just a fast existence
    check.

    Args:
        name: Entity identifier. Must not be empty, contain path
            separators, or start with ``.``.
        config_path: Override the operator config file location. Defaults
            to ``~/.ve-config.toml`` via :func:`cli.config.load_config`.
            Primarily used by tests.

    Returns:
        Absolute path to ``<entities_dir>/<name>``.

    Raises:
        ValueError: If ``name`` is empty or structurally invalid.
        cli.config.ConfigError: If the operator config is missing or
            malformed (propagated unchanged from :func:`load_config`).
        AuthFailure: Git rejected authentication during the clone.
        MissingRemoteRepo: The git host says the repository does not
            exist. Most commonly a typoed entity name.
        NetworkFailure: DNS / connection / timeout failure reaching the
            git host.
        CanonicalCloneError: Any other clone failure, with the raw git
            stderr included in the message. Also raised when
            ``<entities_dir>/<name>`` already exists as a non-git
            directory (we refuse to clobber pre-existing content).
    """
    _validate_entity_name(name)

    cfg: VeConfig = load_config(config_path)
    cfg.entities_dir.mkdir(parents=True, exist_ok=True)

    dest = cfg.entities_dir / name
    clone_url = f"{cfg.git_base}/{name}.git"

    # Fast path: already cloned. No git calls, no network.
    if _is_existing_clone(dest):
        return dest

    # If the destination exists but isn't a git clone, refuse rather than
    # clobber whatever the user has there. This is the canonical "stale
    # leftover directory" case — the user can clean it up by hand and
    # re-run. We do NOT touch it ourselves: if the user pointed
    # entities_dir at a populated tree, deleting their files would be
    # catastrophic.
    if dest.exists():
        raise CanonicalCloneError(
            f"Cannot clone entity '{name}': destination {dest} already "
            f"exists but is not a git clone. Remove it or rename it, "
            f"then retry.",
            entity_name=name,
            clone_url=clone_url,
        )

    # Remember pre-existence so we only clean up directories WE created.
    pre_existed = dest.exists()  # always False at this point; defensive

    try:
        result = subprocess.run(
            ["git", "clone", clone_url, str(dest)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        # `git` itself isn't on PATH. Extremely unusual on dev machines,
        # but surface it cleanly rather than as a stack trace.
        raise CanonicalCloneError(
            f"`git` executable not found while cloning entity '{name}' "
            f"from {clone_url}. Install git and retry.",
            entity_name=name,
            clone_url=clone_url,
        ) from exc

    if result.returncode == 0:
        return dest

    # Failure path: clean up any partial clone we created so the next
    # invocation can retry cleanly. Never delete a directory the caller
    # already had.
    if dest.exists() and not pre_existed:
        shutil.rmtree(dest, ignore_errors=True)

    raise _classify_clone_error(
        result.stderr,
        name=name,
        clone_url=clone_url,
    )
