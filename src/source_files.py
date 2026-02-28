"""Language-agnostic source file enumeration for backreference scanning.

# Chunk: docs/chunks/backref_language_agnostic - Language-agnostic source file enumeration

This module provides utilities for discovering source files in a project
directory, supporting any programming language. It uses git to enumerate
files (respecting .gitignore) when available, falling back to recursive
glob with a minimal exclusion set for non-git projects.
"""

from __future__ import annotations

import pathlib
import subprocess


# Default set of source file extensions (lowercase, without leading dot)
SOURCE_EXTENSIONS: set[str] = {
    # Python
    "py",
    # JavaScript/TypeScript
    "js", "ts", "jsx", "tsx", "mjs", "cjs",
    # Ruby
    "rb",
    # Go
    "go",
    # Rust
    "rs",
    # Java, Kotlin
    "java", "kt", "kts",
    # Swift
    "swift",
    # C/C++
    "c", "cpp", "cc", "cxx", "h", "hpp", "hxx",
    # C#
    "cs",
    # PHP
    "php",
    # Scala
    "scala",
    # Elixir
    "ex", "exs",
    # Erlang
    "erl", "hrl",
    # Clojure
    "clj", "cljs", "cljc",
    # Lua
    "lua",
    # Perl
    "pl", "pm",
    # Shell
    "sh", "bash", "zsh",
}

# Directories to exclude in non-git fallback
FALLBACK_EXCLUDE_DIRS: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "vendor",
    "dist",
    "build",
    ".tox",
    ".pytest_cache",
}


def _is_git_repository(project_dir: pathlib.Path) -> bool:
    """Check if the given directory is inside a git repository.

    Args:
        project_dir: Path to the project directory.

    Returns:
        True if the directory is inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        # git not installed
        return False


def _enumerate_git_files(project_dir: pathlib.Path) -> list[str]:
    """Enumerate files using git ls-files.

    Uses --cached --others --exclude-standard to get all tracked files
    plus untracked files that aren't ignored by .gitignore.

    Args:
        project_dir: Path to the project directory.

    Returns:
        List of relative file paths from the project directory.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _enumerate_fallback_files(
    project_dir: pathlib.Path,
    exclude_dirs: set[str],
) -> list[pathlib.Path]:
    """Enumerate files using recursive glob with exclusions.

    Used when git is not available or the project is not a git repository.

    Args:
        project_dir: Path to the project directory.
        exclude_dirs: Set of directory names to exclude.

    Returns:
        List of absolute paths to files.
    """
    result: list[pathlib.Path] = []

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue

        # Check if any parent directory is in the exclusion set
        should_exclude = False
        for part in path.relative_to(project_dir).parts[:-1]:
            if part in exclude_dirs:
                should_exclude = True
                break

        if not should_exclude:
            result.append(path)

    return result


def _filter_by_extension(
    paths: list[pathlib.Path],
    extensions: set[str],
) -> list[pathlib.Path]:
    """Filter paths to only include files with matching extensions.

    Args:
        paths: List of file paths.
        extensions: Set of extensions to include (lowercase, without dot).

    Returns:
        Filtered list of paths.
    """
    result: list[pathlib.Path] = []

    for path in paths:
        # Get extension without the leading dot, lowercase
        ext = path.suffix.lower().lstrip(".")
        if ext in extensions:
            result.append(path)

    return result


def enumerate_source_files(
    project_dir: pathlib.Path,
    extensions: set[str] | None = None,
) -> list[pathlib.Path]:
    """Enumerate source files in a project directory.

    In git repositories, uses `git ls-files --cached --others --exclude-standard`
    to enumerate files, automatically respecting .gitignore.

    In non-git directories, falls back to recursive glob with a minimal
    exclusion set.

    Args:
        project_dir: Path to the project root.
        extensions: Set of file extensions to include (without leading dot).
                   Defaults to SOURCE_EXTENSIONS.

    Returns:
        List of absolute paths to source files.
    """
    if extensions is None:
        extensions = SOURCE_EXTENSIONS

    project_dir = pathlib.Path(project_dir).resolve()

    if _is_git_repository(project_dir):
        # Use git to enumerate files
        relative_paths = _enumerate_git_files(project_dir)
        paths = [project_dir / p for p in relative_paths]
    else:
        # Fall back to recursive glob with exclusions
        paths = _enumerate_fallback_files(project_dir, FALLBACK_EXCLUDE_DIRS)

    # Filter by extension
    return _filter_by_extension(paths, extensions)
