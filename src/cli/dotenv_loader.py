# Chunk: docs/chunks/cli_dotenv_loading
# Chunk: docs/chunks/cli_dotenv_walk_parents - Walk parent dirs for .env
"""Load .env files from the project root into os.environ."""

from __future__ import annotations

import os
from pathlib import Path


def _collect_dotenv_files(start: Path) -> list[Path]:
    """Walk from start up to filesystem root, return all .env files found.

    Returns them in order from closest (project root) to farthest (home/root).
    """
    result: list[Path] = []
    current = start.resolve()
    while True:
        candidate = current / ".env"
        if candidate.is_file():
            result.append(candidate)
        parent = current.parent
        if parent == current:  # filesystem root
            break
        current = parent
    return result


def load_dotenv_from_project_root() -> None:
    """Load variables from all .env files at or above the resolved project root.

    Uses resolve_project_root() to find the project root via the
    .ve-task.yaml → .git → CWD resolution chain, then walks up parent
    directories collecting ALL .env files.  Files are loaded farthest-first
    (e.g., ~/.env before ~/Projects/myproject/.env) so that closer files
    override farther ones.  Variables are only set if they are NOT already
    present in os.environ (existing env vars always win).

    Silently returns on any error (missing file, parse errors, resolution
    failure) so CLI startup is never broken by dotenv issues.
    """
    try:
        from dotenv import dotenv_values

        # Start from project root if resolvable, otherwise CWD
        try:
            from board.storage import resolve_project_root
            root = Path(resolve_project_root())
        except Exception:
            root = Path.cwd()

        dotenv_files = _collect_dotenv_files(root)

        if not dotenv_files:
            return

        # Load closest first — closer .env files take precedence
        for dotenv_path in dotenv_files:
            values = dotenv_values(dotenv_path)
            for key, value in values.items():
                if key not in os.environ and value is not None:
                    os.environ[key] = value
    except Exception:
        # Never break CLI startup due to dotenv issues
        pass
