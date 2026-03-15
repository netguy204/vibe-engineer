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
