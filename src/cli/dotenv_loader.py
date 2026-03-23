# Chunk: docs/chunks/cli_dotenv_loading
"""Load .env files from the project root into os.environ."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_from_project_root() -> None:
    """Load variables from a .env file at the resolved project root.

    Uses resolve_project_root() to find the project root via the
    .ve-task.yaml → .git → CWD resolution chain, then reads any .env
    file found there.  Variables are only set if they are NOT already
    present in os.environ (existing env vars always win).

    Silently returns on any error (missing file, parse errors, resolution
    failure) so CLI startup is never broken by dotenv issues.
    """
    try:
        from board.storage import resolve_project_root
        from dotenv import dotenv_values

        root = resolve_project_root()
        dotenv_path = Path(root) / ".env"

        if not dotenv_path.is_file():
            return

        values = dotenv_values(dotenv_path)
        for key, value in values.items():
            if key not in os.environ and value is not None:
                os.environ[key] = value
    except Exception:
        # Never break CLI startup due to dotenv issues
        pass
