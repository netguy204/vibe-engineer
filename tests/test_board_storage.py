# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.storage — key and cursor persistence."""

import pytest
from board.crypto import generate_keypair, derive_swarm_id
from board.storage import (
    collect_board_files,
    find_git_root,
    load_cursor,
    load_keypair,
    list_swarms,
    read_watch_pid,
    remove_watch_pid,
    resolve_board_root,
    save_cursor,
    save_keypair,
    watch_pid_path,
    write_watch_pid,
)


def test_save_and_load_keypair(tmp_path):
    """Save key files to a directory, load them back, assert byte equality."""
    seed, public_key = generate_keypair()
    swarm_id = derive_swarm_id(public_key)
    save_keypair(swarm_id, seed, public_key, keys_dir=tmp_path)
    loaded = load_keypair(swarm_id, keys_dir=tmp_path)
    assert loaded is not None
    loaded_seed, loaded_pub = loaded
    assert loaded_seed == seed
    assert loaded_pub == public_key


def test_load_keypair_missing(tmp_path):
    """Loading a non-existent keypair returns None."""
    result = load_keypair("nonexistent", keys_dir=tmp_path)
    assert result is None


def test_save_and_load_cursor(tmp_path):
    """Write cursor 42, read it back, assert 42."""
    save_cursor("test-channel", 42, project_root=tmp_path)
    assert load_cursor("test-channel", project_root=tmp_path) == 42


def test_load_cursor_default(tmp_path):
    """Missing cursor file returns 0."""
    assert load_cursor("nonexistent", project_root=tmp_path) == 0


def test_cursor_overwrite(tmp_path):
    """Write 10, then 20, read back 20."""
    save_cursor("ch", 10, project_root=tmp_path)
    assert load_cursor("ch", project_root=tmp_path) == 10
    save_cursor("ch", 20, project_root=tmp_path)
    assert load_cursor("ch", project_root=tmp_path) == 20


def test_list_swarms(tmp_path):
    """Create two key pairs, list returns both swarm IDs."""
    seed1, pub1 = generate_keypair()
    seed2, pub2 = generate_keypair()
    id1 = derive_swarm_id(pub1)
    id2 = derive_swarm_id(pub2)
    save_keypair(id1, seed1, pub1, keys_dir=tmp_path)
    save_keypair(id2, seed2, pub2, keys_dir=tmp_path)
    swarms = list_swarms(keys_dir=tmp_path)
    assert set(swarms) == {id1, id2}


def test_list_swarms_empty(tmp_path):
    """Empty keys directory returns empty list."""
    assert list_swarms(keys_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# collect_board_files tests
# Chunk: docs/chunks/board_scp_command - Board SCP command
# ---------------------------------------------------------------------------


def test_collect_board_files_missing_config(tmp_path):
    """collect_board_files raises FileNotFoundError when board.toml missing."""
    with pytest.raises(FileNotFoundError, match="does not exist"):
        collect_board_files(config_path=tmp_path / "board.toml", keys_dir=tmp_path / "keys")


def test_collect_board_files_config_only(tmp_path):
    """collect_board_files returns only board.toml when no keys exist."""
    config = tmp_path / "board.toml"
    config.write_text("default_swarm = 'abc'\n")
    files = collect_board_files(config_path=config, keys_dir=tmp_path / "keys")
    assert files == [config]


def test_collect_board_files_with_keys(tmp_path):
    """collect_board_files returns board.toml and key files."""
    config = tmp_path / "board.toml"
    config.write_text("default_swarm = 'abc'\n")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    key_file = keys_dir / "abc.key"
    pub_file = keys_dir / "abc.pub"
    key_file.write_bytes(b"\x00" * 32)
    pub_file.write_bytes(b"\x00" * 32)

    files = collect_board_files(config_path=config, keys_dir=keys_dir)
    assert config in files
    assert key_file in files
    assert pub_file in files
    assert len(files) == 3


def test_collect_board_files_ignores_non_key_files(tmp_path):
    """collect_board_files ignores files without .key or .pub suffix."""
    config = tmp_path / "board.toml"
    config.write_text("")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "abc.key").write_bytes(b"\x00" * 32)
    (keys_dir / "abc.pub").write_bytes(b"\x00" * 32)
    (keys_dir / "notes.txt").write_text("random file")

    files = collect_board_files(config_path=config, keys_dir=keys_dir)
    assert len(files) == 3  # board.toml + .key + .pub
    assert not any(f.name == "notes.txt" for f in files)


# ---------------------------------------------------------------------------
# find_git_root tests
# Chunk: docs/chunks/board_cursor_root_resolution
# ---------------------------------------------------------------------------


def test_find_git_root_from_subdirectory(tmp_path):
    """find_git_root finds .git directory from a nested subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "a" / "b" / "c"
    subdir.mkdir(parents=True)
    assert find_git_root(subdir) == tmp_path


def test_find_git_root_with_git_file(tmp_path):
    """find_git_root finds .git file (worktree scenario) from a subdirectory."""
    # In a git worktree, .git is a file, not a directory
    (tmp_path / ".git").write_text("gitdir: /some/other/path")
    subdir = tmp_path / "src"
    subdir.mkdir()
    assert find_git_root(subdir) == tmp_path


def test_find_git_root_returns_none_when_absent(tmp_path):
    """find_git_root returns None when no .git exists in the tree."""
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    assert find_git_root(subdir) is None


# ---------------------------------------------------------------------------
# resolve_board_root tests
# Chunk: docs/chunks/board_cursor_root_resolution
# ---------------------------------------------------------------------------


def test_resolve_board_root_explicit_root(tmp_path):
    """resolve_board_root with explicit root returns the explicit root."""
    explicit = tmp_path / "my-project"
    explicit.mkdir()
    assert resolve_board_root(explicit) == explicit


def test_resolve_board_root_prefers_task_over_git(tmp_path, monkeypatch):
    """resolve_board_root prefers .ve-task.yaml over .git."""
    # Set up a directory tree with both markers at different levels
    task_root = tmp_path / "task"
    task_root.mkdir()
    (task_root / ".ve-task.yaml").write_text("projects: []\n")

    git_root = tmp_path
    (git_root / ".git").mkdir()

    subdir = task_root / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    assert resolve_board_root() == task_root


def test_resolve_board_root_falls_back_to_git(tmp_path, monkeypatch):
    """resolve_board_root falls back to .git root when no task yaml."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "src" / "lib"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    assert resolve_board_root() == tmp_path


def test_resolve_board_root_falls_back_to_cwd(tmp_path, monkeypatch):
    """resolve_board_root falls back to CWD when neither marker exists."""
    subdir = tmp_path / "somewhere"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    assert resolve_board_root() == subdir


# ---------------------------------------------------------------------------
# Watch PID file tests
# Chunk: docs/chunks/board_watch_safety
# ---------------------------------------------------------------------------


def test_watch_pid_path_returns_expected_path(tmp_path):
    """watch_pid_path returns {project_root}/.ve/board/cursors/{channel}.watch.pid."""
    result = watch_pid_path("my-channel", tmp_path)
    assert result == tmp_path / ".ve" / "board" / "cursors" / "my-channel.watch.pid"


def test_write_watch_pid_creates_file(tmp_path):
    """write_watch_pid creates the PID file with correct content."""
    write_watch_pid("test-ch", 12345, tmp_path)
    pid_file = tmp_path / ".ve" / "board" / "cursors" / "test-ch.watch.pid"
    assert pid_file.exists()
    assert pid_file.read_text() == "12345"


def test_read_watch_pid_returns_pid(tmp_path):
    """read_watch_pid returns the PID when the file exists."""
    write_watch_pid("test-ch", 99999, tmp_path)
    assert read_watch_pid("test-ch", tmp_path) == 99999


def test_read_watch_pid_returns_none_when_missing(tmp_path):
    """read_watch_pid returns None when the file does not exist."""
    assert read_watch_pid("nonexistent", tmp_path) is None


def test_read_watch_pid_returns_none_on_garbage(tmp_path):
    """read_watch_pid returns None when the file contains non-integer content."""
    pid_file = tmp_path / ".ve" / "board" / "cursors" / "garbage.watch.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text("not-a-number")
    assert read_watch_pid("garbage", tmp_path) is None


def test_remove_watch_pid_deletes_file(tmp_path):
    """remove_watch_pid deletes the PID file."""
    write_watch_pid("test-ch", 12345, tmp_path)
    pid_file = watch_pid_path("test-ch", tmp_path)
    assert pid_file.exists()
    remove_watch_pid("test-ch", tmp_path)
    assert not pid_file.exists()


def test_remove_watch_pid_noop_when_missing(tmp_path):
    """remove_watch_pid is a no-op when the file does not exist."""
    # Should not raise
    remove_watch_pid("nonexistent", tmp_path)
