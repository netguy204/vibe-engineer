"""Tests for the canonical entity-clone helper.

# Chunk: docs/chunks/entity_canonical_clone - Ensure entities_dir/<name> is a clone of git_base/<name>.git
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

from cli.canonical_clone import (
    AuthFailure,
    CanonicalCloneError,
    MissingRemoteRepo,
    NetworkFailure,
    _classify_clone_error,
    ensure_canonical_clone,
)
from cli.config import ConfigError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bare_repo(parent: pathlib.Path, name: str) -> pathlib.Path:
    """Create a bare git repo at ``<parent>/<name>.git`` with one commit.

    The bare repo serves as a stand-in for the remote git host so the
    happy-path tests can exercise a full ``git clone`` end-to-end without
    touching the network.
    """
    # First make a working repo with a commit, then clone it bare.
    seed = parent / f"{name}-seed"
    seed.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=seed, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=seed, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=seed, check=True, capture_output=True,
    )
    (seed / "README.md").write_text("# seed\n")
    subprocess.run(["git", "add", "."], cwd=seed, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"],
        cwd=seed, check=True, capture_output=True,
    )

    bare = parent / f"{name}.git"
    subprocess.run(
        ["git", "clone", "--bare", str(seed), str(bare)],
        check=True, capture_output=True,
    )
    return bare


def _write_config(
    tmp_path: pathlib.Path,
    *,
    entities_dir: pathlib.Path,
    git_base: str,
) -> pathlib.Path:
    """Write a ve-config.toml file pointing at the given fields."""
    cfg = tmp_path / "ve-config.toml"
    cfg.write_text(
        f'entities_dir = "{entities_dir}"\n'
        f'git_base = "{git_base}"\n'
    )
    return cfg


# ---------------------------------------------------------------------------
# Happy path: first-time clone + idempotent re-call
# ---------------------------------------------------------------------------


def test_first_time_clone(tmp_path):
    """A missing entity is cloned from git_base/<name>.git into entities_dir/<name>."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_repo(origin, "foo")

    entities = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities, git_base=str(origin))

    result = ensure_canonical_clone("foo", config_path=cfg)

    assert result == entities / "foo"
    assert (entities / "foo" / ".git").exists()
    assert (entities / "foo" / "README.md").read_text() == "# seed\n"


def test_idempotent_recall_no_subprocess(tmp_path, monkeypatch):
    """A second call is a fast existence check — no subprocess invoked."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_repo(origin, "foo")
    entities = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities, git_base=str(origin))

    # First call: clones normally.
    first = ensure_canonical_clone("foo", config_path=cfg)

    # Trip subprocess so any git call blows up.
    def _explode(*args, **kwargs):
        raise AssertionError(
            "second call must not invoke subprocess: idempotent re-call "
            "should be a fast existence check"
        )
    monkeypatch.setattr(subprocess, "run", _explode)

    second = ensure_canonical_clone("foo", config_path=cfg)

    assert first == second
    assert second == entities / "foo"


def test_entities_dir_auto_created(tmp_path):
    """A nonexistent entities_dir is created before clone."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_repo(origin, "foo")

    entities = tmp_path / "does" / "not" / "exist" / "yet"
    assert not entities.exists()
    cfg = _write_config(tmp_path, entities_dir=entities, git_base=str(origin))

    ensure_canonical_clone("foo", config_path=cfg)

    assert entities.is_dir()
    assert (entities / "foo" / ".git").exists()


# ---------------------------------------------------------------------------
# Error classification: unit-test the classifier on representative stderrs
# ---------------------------------------------------------------------------


def test_classify_auth_failure_ssh():
    """SSH auth-denied stderr classifies as AuthFailure."""
    stderr = (
        "Cloning into 'foo'...\n"
        "git@github.com: Permission denied (publickey).\n"
        "fatal: Could not read from remote repository.\n"
    )
    exc = _classify_clone_error(
        stderr, name="foo", clone_url="git@github.com:org/foo.git"
    )
    assert isinstance(exc, AuthFailure)
    assert exc.entity_name == "foo"
    assert exc.clone_url == "git@github.com:org/foo.git"
    msg = str(exc)
    assert "auth" in msg.lower()
    assert "git@github.com:org/foo.git" in msg


def test_classify_auth_failure_https():
    """HTTPS auth-failed stderr classifies as AuthFailure."""
    stderr = (
        "Cloning into 'foo'...\n"
        "remote: Invalid username or password.\n"
        "fatal: Authentication failed for 'https://example.com/org/foo.git/'\n"
    )
    exc = _classify_clone_error(
        stderr, name="foo", clone_url="https://example.com/org/foo.git"
    )
    assert isinstance(exc, AuthFailure)


def test_classify_missing_repo():
    """'Repository not found' stderr classifies as MissingRemoteRepo."""
    stderr = (
        "Cloning into 'typoed'...\n"
        "remote: Repository not found.\n"
        "fatal: repository 'https://example.com/org/typoed.git/' not found\n"
    )
    exc = _classify_clone_error(
        stderr, name="typoed", clone_url="https://example.com/org/typoed.git"
    )
    assert isinstance(exc, MissingRemoteRepo)
    msg = str(exc)
    assert "typoed" in msg
    assert "https://example.com/org/typoed.git" in msg


def test_classify_network_failure_dns():
    """'Could not resolve host' stderr classifies as NetworkFailure."""
    stderr = (
        "Cloning into 'foo'...\n"
        "fatal: unable to access 'https://does-not-exist.invalid/foo.git/': "
        "Could not resolve host: does-not-exist.invalid\n"
    )
    exc = _classify_clone_error(
        stderr, name="foo", clone_url="https://does-not-exist.invalid/foo.git"
    )
    assert isinstance(exc, NetworkFailure)


def test_classify_network_failure_refused():
    """'Connection refused' stderr classifies as NetworkFailure."""
    stderr = (
        "Cloning into 'foo'...\n"
        "fatal: unable to access 'http://localhost:9/foo.git/': "
        "Failed to connect to localhost port 9: Connection refused\n"
    )
    exc = _classify_clone_error(
        stderr, name="foo", clone_url="http://localhost:9/foo.git"
    )
    assert isinstance(exc, NetworkFailure)


def test_classify_fallback_unrecognized_stderr():
    """Unrecognized stderr falls through to plain CanonicalCloneError."""
    stderr = "warning: something weird happened in a way git has never said before\n"
    exc = _classify_clone_error(
        stderr, name="foo", clone_url="git@github.com:org/foo.git"
    )
    assert type(exc) is CanonicalCloneError
    # Subclass checks are exclusive in CPython, but assert explicitly anyway.
    assert not isinstance(exc, AuthFailure)
    assert not isinstance(exc, MissingRemoteRepo)
    assert not isinstance(exc, NetworkFailure)
    # Raw stderr is included so the user can see what actually happened.
    assert "something weird happened" in str(exc)


# ---------------------------------------------------------------------------
# End-to-end failure path: partial-clone cleanup
# ---------------------------------------------------------------------------


def test_failed_clone_cleans_up_dest(tmp_path):
    """A failed clone removes the partial destination directory."""
    # Point git_base at a nonexistent local path so `git clone` definitely fails.
    nonexistent_origin = tmp_path / "no-such-origin"
    entities = tmp_path / "Entities"
    cfg = _write_config(
        tmp_path,
        entities_dir=entities,
        git_base=str(nonexistent_origin),
    )

    with pytest.raises(CanonicalCloneError):
        ensure_canonical_clone("ghost", config_path=cfg)

    # The dest must not exist after the failure so the next invocation can
    # retry cleanly without bumping into the "destination already exists
    # but is not a git clone" guard.
    assert not (entities / "ghost").exists()


# ---------------------------------------------------------------------------
# Clobber guard, name validation, config propagation
# ---------------------------------------------------------------------------


def test_refuses_to_clobber_non_git_directory(tmp_path):
    """A pre-existing non-git directory at <entities_dir>/<name> is not touched."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_repo(origin, "foo")
    entities = tmp_path / "Entities"
    entities.mkdir()
    pre_existing = entities / "foo"
    pre_existing.mkdir()
    sentinel = pre_existing / "user-data.txt"
    sentinel.write_text("important")

    cfg = _write_config(tmp_path, entities_dir=entities, git_base=str(origin))

    with pytest.raises(CanonicalCloneError) as excinfo:
        ensure_canonical_clone("foo", config_path=cfg)

    msg = str(excinfo.value)
    assert "foo" in msg
    assert "not a git clone" in msg or "already exists" in msg
    # Crucially: the user's file is still there.
    assert sentinel.read_text() == "important"


@pytest.mark.parametrize(
    "bad_name",
    ["", "../escape", "with/slash", "with\\backslash", ".hidden"],
)
def test_invalid_entity_name_rejected(bad_name, tmp_path):
    """Structurally invalid names raise ValueError before any config load."""
    # No config file written: if validation runs first, ConfigError never
    # gets a chance to fire.
    cfg_path = tmp_path / "ve-config.toml"  # deliberately missing
    with pytest.raises(ValueError):
        ensure_canonical_clone(bad_name, config_path=cfg_path)


def test_config_error_propagates_unwrapped(tmp_path):
    """Missing config file surfaces as ConfigError, not CanonicalCloneError.

    Downstream callers catch ConfigError separately to give a setup-time
    "fix your ~/.ve-config.toml" hint distinct from clone-time errors.
    """
    missing = tmp_path / "absent.toml"
    with pytest.raises(ConfigError):
        ensure_canonical_clone("foo", config_path=missing)


# ---------------------------------------------------------------------------
# Exception hierarchy sanity
# ---------------------------------------------------------------------------


def test_exception_hierarchy():
    """All three classified subclasses descend from CanonicalCloneError."""
    assert issubclass(AuthFailure, CanonicalCloneError)
    assert issubclass(MissingRemoteRepo, CanonicalCloneError)
    assert issubclass(NetworkFailure, CanonicalCloneError)
    # The three classified failures are mutually exclusive — none should
    # be a subclass of another.
    assert not issubclass(AuthFailure, MissingRemoteRepo)
    assert not issubclass(MissingRemoteRepo, NetworkFailure)
    assert not issubclass(NetworkFailure, AuthFailure)


def test_canonical_clone_error_carries_attributes():
    """Base class stores entity_name and clone_url for consistent rendering."""
    exc = CanonicalCloneError(
        "boom", entity_name="foo", clone_url="git@host:org/foo.git"
    )
    assert exc.entity_name == "foo"
    assert exc.clone_url == "git@host:org/foo.git"
    assert "boom" in str(exc)
