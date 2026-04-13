# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Key and cursor storage for Leader Board.

- Operator-global key storage: ~/.ve/keys/{swarm_id}.key and .pub
- Project-local cursor storage: .ve/board/cursors/{channel}.cursor

Spec reference: docs/trunk/SPEC.md §Swarm Model, §Cursor-Based At-Least-Once Delivery
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Operator-global key storage (~/.ve/keys/)
# ---------------------------------------------------------------------------

_DEFAULT_KEYS_DIR = Path.home() / ".ve" / "keys"


def save_keypair(
    swarm_id: str,
    seed: bytes,
    public_key: bytes,
    keys_dir: Path | None = None,
) -> None:
    """Persist a key pair to disk.

    Files created:
        {keys_dir}/{swarm_id}.key  — 32-byte private seed
        {keys_dir}/{swarm_id}.pub  — 32-byte public key
    """
    d = keys_dir or _DEFAULT_KEYS_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{swarm_id}.key").write_bytes(seed)
    (d / f"{swarm_id}.pub").write_bytes(public_key)


def load_keypair(
    swarm_id: str,
    keys_dir: Path | None = None,
) -> tuple[bytes, bytes] | None:
    """Load a key pair from disk.

    Returns (seed, public_key) or None if not found.
    """
    d = keys_dir or _DEFAULT_KEYS_DIR
    key_file = d / f"{swarm_id}.key"
    pub_file = d / f"{swarm_id}.pub"
    if not key_file.exists() or not pub_file.exists():
        return None
    return key_file.read_bytes(), pub_file.read_bytes()


def list_swarms(keys_dir: Path | None = None) -> list[str]:
    """List all swarm IDs that have stored key pairs."""
    d = keys_dir or _DEFAULT_KEYS_DIR
    if not d.exists():
        return []
    return sorted(
        p.stem for p in d.glob("*.key") if (d / f"{p.stem}.pub").exists()
    )


# Chunk: docs/chunks/board_scp_command - Board SCP command
def collect_board_files(
    config_path: Path | None = None,
    keys_dir: Path | None = None,
) -> list[Path]:
    """Collect all board-related files for SCP transfer.

    Returns a list of absolute paths to:
    - ~/.ve/board.toml (if it exists)
    - ~/.ve/keys/*.key and *.pub files

    Raises FileNotFoundError if board.toml does not exist.
    """
    from board.config import DEFAULT_CONFIG_PATH

    cfg = config_path or DEFAULT_CONFIG_PATH
    if not cfg.exists():
        raise FileNotFoundError(f"{cfg} does not exist")

    files: list[Path] = [cfg]

    kd = keys_dir or _DEFAULT_KEYS_DIR
    if kd.exists():
        for p in sorted(kd.iterdir()):
            if p.suffix in (".key", ".pub"):
                files.append(p)

    return files


# ---------------------------------------------------------------------------
# Project root resolution
# Chunk: docs/chunks/board_cursor_root_resolution
# ---------------------------------------------------------------------------


# Chunk: docs/chunks/board_cursor_root_resolution - Walk parent dirs to find .git root
def find_git_root(start_path: Path) -> Path | None:
    """Walk up from start_path to find directory containing .git.

    Works with both regular git repos (.git directory) and worktrees (.git file).

    Args:
        start_path: Starting path to search from.

    Returns:
        Path to the git root, or None if not found.
    """
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    # Check root as well
    if (current / ".git").exists():
        return current
    return None


# Chunk: docs/chunks/orch_daemon_root_resolution - Shared project root resolution
def resolve_project_root(explicit_root: Path | None = None) -> Path:
    """Resolve the project root for daemon/state file lookup.

    Priority chain:
    1. Explicit root (operator override) — returned as-is
    2. Walk up for .ve-task.yaml — task directory is the root
    3. Walk up for .git — git root is the project root
    4. Fall back to CWD (preserves DEC-002: git not assumed)

    Args:
        explicit_root: If provided, used as-is.

    Returns:
        Resolved project root path.
    """
    if explicit_root is not None:
        return explicit_root

    from task.config import find_task_directory

    cwd = Path.cwd()

    # Try task directory first
    task_dir = find_task_directory(cwd)
    if task_dir is not None:
        return task_dir

    # Try git root
    git_root = find_git_root(cwd)
    if git_root is not None:
        return git_root

    # Fall back to CWD
    return cwd


# Chunk: docs/chunks/board_cursor_root_resolution
def resolve_board_root(explicit_root: Path | None = None) -> Path:
    """Resolve the project root for board cursor storage.

    Delegates to resolve_project_root — see its docstring for the
    full priority chain.
    """
    return resolve_project_root(explicit_root)


# ---------------------------------------------------------------------------
# Project-local cursor storage (.ve/board/cursors/)
# ---------------------------------------------------------------------------


def save_cursor(channel: str, position: int, project_root: Path) -> None:
    """Write the cursor position for a channel.

    File: {project_root}/.ve/board/cursors/{channel}.cursor
    """
    cursor_dir = project_root / ".ve" / "board" / "cursors"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    (cursor_dir / f"{channel}.cursor").write_text(str(position))


def load_cursor(channel: str, project_root: Path) -> int:
    """Read the cursor position for a channel.

    Returns 0 if the cursor file does not exist.
    """
    cursor_file = project_root / ".ve" / "board" / "cursors" / f"{channel}.cursor"
    if not cursor_file.exists():
        return 0
    return int(cursor_file.read_text().strip())


# ---------------------------------------------------------------------------
# Watch PID file management (.ve/board/cursors/{channel}.watch.pid)
# Chunk: docs/chunks/board_watch_safety
# ---------------------------------------------------------------------------


def watch_pid_path(channel: str, project_root: Path) -> Path:
    """Return the path to the PID file for a channel watch process.

    File: {project_root}/.ve/board/cursors/{channel}.watch.pid
    """
    return project_root / ".ve" / "board" / "cursors" / f"{channel}.watch.pid"


def read_watch_pid(channel: str, project_root: Path) -> int | None:
    """Read the PID from the watch PID file for a channel.

    Returns None if the file is missing or contains unparseable content.
    """
    pid_file = watch_pid_path(channel, project_root)
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return None


def write_watch_pid(channel: str, pid: int, project_root: Path) -> None:
    """Write the current process PID to the watch PID file for a channel."""
    pid_file = watch_pid_path(channel, project_root)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))


def remove_watch_pid(channel: str, project_root: Path) -> None:
    """Remove the watch PID file for a channel. No-op if already gone."""
    pid_file = watch_pid_path(channel, project_root)
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


# Chunk: docs/chunks/ack_auto_increment - Auto-increment cursor on ack
# Chunk: docs/chunks/ack_cursor_head_guard - Head guard lives in CLI layer (ack_cmd);
#   this function stays pure-local intentionally.
def ack_and_advance(channel: str, project_root: Path) -> int:
    """Read the current cursor and advance it by 1.

    Returns the new cursor position.
    """
    current = load_cursor(channel, project_root)
    new_position = current + 1
    save_cursor(channel, new_position, project_root)
    return new_position
