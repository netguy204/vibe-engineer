# Chunk: docs/chunks/cli_dotenv_loading
# Chunk: docs/chunks/cli_dotenv_walk_parents - Walk parent dirs for .env
"""Load .env files from the project root into os.environ."""

from __future__ import annotations

import os
from pathlib import Path


def _find_dotenv_walking_parents(start: Path) -> Path | None:
    """Walk from start up to filesystem root, return first .env found."""
    current = start.resolve()
    while True:
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:  # filesystem root
            return None
        current = parent


def load_dotenv_from_project_root() -> None:
    """Load variables from a .env file at or above the resolved project root.

    Uses resolve_project_root() to find the project root via the
    .ve-task.yaml → .git → CWD resolution chain, then walks up parent
    directories until a .env file is found.  More specific .env files
    (closer to the project root) take precedence because they are found
    first.  Variables are only set if they are NOT already present in
    os.environ (existing env vars always win).

    Silently returns on any error (missing file, parse errors, resolution
    failure) so CLI startup is never broken by dotenv issues.
    """
    try:
        from board.storage import resolve_project_root
        from dotenv import dotenv_values

        root = resolve_project_root()
        dotenv_path = _find_dotenv_walking_parents(Path(root))

        if dotenv_path is None:
            return

        values = dotenv_values(dotenv_path)
        for key, value in values.items():
            if key not in os.environ and value is not None:
                os.environ[key] = value
    except Exception:
        # Never break CLI startup due to dotenv issues
        pass
