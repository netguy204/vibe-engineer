"""Tests for language-agnostic source file enumeration.

# Chunk: docs/chunks/backref_language_agnostic - Tests for source file enumeration utility
"""

import pathlib
import subprocess

import pytest

from conftest import make_ve_initialized_git_repo
from source_files import enumerate_source_files, SOURCE_EXTENSIONS, FALLBACK_EXCLUDE_DIRS


class TestEnumerateSourceFilesGit:
    """Tests for source file enumeration in git repositories."""

    def test_enumerate_in_git_repo_returns_source_files(self, temp_project):
        """In a git repo, function returns files with supported extensions."""
        make_ve_initialized_git_repo(temp_project)
        # Resolve to handle symlinks (e.g., /var -> /private/var on macOS)
        temp_project = temp_project.resolve()

        # Create some Python source files
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("# Main module\n")
        (src_dir / "utils.py").write_text("# Utils module\n")

        # Add files to git
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        result = enumerate_source_files(temp_project)

        # Should find the Python files
        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/main.py" in rel_paths
        assert "src/utils.py" in rel_paths

    def test_enumerate_respects_gitignore(self, temp_project):
        """Files in .gitignore-excluded directories are not returned."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a gitignore
        (temp_project / ".gitignore").write_text("node_modules/\n")

        # Create source files in regular and ignored directories
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# App\n")

        ignored_dir = temp_project / "node_modules" / "lib"
        ignored_dir.mkdir(parents=True)
        (ignored_dir / "module.js").write_text("// module\n")

        # Add files to git (node_modules should be ignored)
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        result = enumerate_source_files(temp_project)

        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/app.py" in rel_paths
        assert "node_modules/lib/module.js" not in rel_paths

    def test_enumerate_returns_multiple_languages(self, temp_project):
        """Returns files with various language extensions in a git repo."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)

        # Create files of different languages
        (src_dir / "app.py").write_text("# Python\n")
        (src_dir / "app.js").write_text("// JavaScript\n")
        (src_dir / "app.ts").write_text("// TypeScript\n")
        (src_dir / "app.go").write_text("// Go\n")
        (src_dir / "app.rs").write_text("// Rust\n")

        # Add files to git
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        result = enumerate_source_files(temp_project)

        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/app.py" in rel_paths
        assert "src/app.js" in rel_paths
        assert "src/app.ts" in rel_paths
        assert "src/app.go" in rel_paths
        assert "src/app.rs" in rel_paths

    def test_enumerate_excludes_non_source_files(self, temp_project):
        """Non-source files (like .txt, .md, .json) are not returned."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")
        (src_dir / "readme.txt").write_text("README\n")
        (src_dir / "config.json").write_text("{}\n")
        (temp_project / "README.md").write_text("# README\n")

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        result = enumerate_source_files(temp_project)

        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/app.py" in rel_paths
        assert "src/readme.txt" not in rel_paths
        assert "src/config.json" not in rel_paths
        assert "README.md" not in rel_paths

    def test_enumerate_includes_untracked_source_files(self, temp_project):
        """Untracked source files (not ignored) are included."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create and commit one file
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "committed.py").write_text("# Committed\n")
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=temp_project, check=True)

        # Create an untracked file (not ignored)
        (src_dir / "untracked.py").write_text("# Untracked\n")

        result = enumerate_source_files(temp_project)

        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/committed.py" in rel_paths
        assert "src/untracked.py" in rel_paths

    def test_enumerate_custom_extensions(self, temp_project):
        """Can specify custom set of extensions to include."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")
        (src_dir / "app.js").write_text("// JavaScript\n")
        (src_dir / "data.csv").write_text("a,b,c\n")

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        # Only include CSV files (custom extension set)
        result = enumerate_source_files(temp_project, extensions={"csv"})

        rel_paths = {str(p.relative_to(temp_project)) for p in result}
        assert "src/data.csv" in rel_paths
        assert "src/app.py" not in rel_paths
        assert "src/app.js" not in rel_paths


class TestEnumerateSourceFilesNonGit:
    """Tests for source file enumeration in non-git directories."""

    def test_enumerate_in_non_git_dir_falls_back_to_glob(self, tmp_path):
        """In a non-git directory, function returns source files via glob."""
        # Don't initialize git - just a plain directory
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")
        (src_dir / "utils.py").write_text("# Utils\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "src/app.py" in rel_paths
        assert "src/utils.py" in rel_paths

    def test_enumerate_non_git_excludes_pycache(self, tmp_path):
        """The fallback glob excludes __pycache__/ directories."""
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")

        pycache_dir = src_dir / "__pycache__"
        pycache_dir.mkdir(parents=True)
        (pycache_dir / "app.cpython-311.pyc").write_text("bytecode\n")
        # Some projects also have .py files in __pycache__ (edge case)
        (pycache_dir / "cache.py").write_text("# Cache\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "src/app.py" in rel_paths
        assert "src/__pycache__/cache.py" not in rel_paths

    def test_enumerate_non_git_excludes_node_modules(self, tmp_path):
        """The fallback glob excludes node_modules/ directories."""
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.js").write_text("// App\n")

        node_modules = tmp_path / "node_modules" / "lodash"
        node_modules.mkdir(parents=True)
        (node_modules / "lodash.js").write_text("// Lodash\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "src/app.js" in rel_paths
        assert "node_modules/lodash/lodash.js" not in rel_paths

    def test_enumerate_non_git_excludes_venv(self, tmp_path):
        """The fallback glob excludes .venv/ and venv/ directories."""
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")

        venv_dir = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        venv_dir.mkdir(parents=True)
        (venv_dir / "requests.py").write_text("# Requests\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "src/app.py" in rel_paths
        # Should not include any files from .venv
        assert not any(".venv" in p for p in rel_paths)

    def test_enumerate_non_git_multiple_languages(self, tmp_path):
        """Non-git fallback also supports multiple languages."""
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)

        (src_dir / "app.py").write_text("# Python\n")
        (src_dir / "app.js").write_text("// JavaScript\n")
        (src_dir / "app.go").write_text("// Go\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "src/app.py" in rel_paths
        assert "src/app.js" in rel_paths
        assert "src/app.go" in rel_paths


class TestEnumerateSourceFilesEdgeCases:
    """Edge case tests for source file enumeration."""

    def test_empty_directory_returns_empty_list(self, tmp_path):
        """Empty directory returns empty list."""
        result = enumerate_source_files(tmp_path)
        assert result == []

    def test_directory_with_only_non_source_files(self, tmp_path):
        """Directory with only non-source files returns empty list."""
        (tmp_path / "readme.txt").write_text("README\n")
        (tmp_path / "config.json").write_text("{}\n")

        result = enumerate_source_files(tmp_path)
        assert result == []

    def test_nested_directories(self, tmp_path):
        """Finds source files in nested directory structure."""
        nested = tmp_path / "a" / "b" / "c" / "d"
        nested.mkdir(parents=True)
        (nested / "deep.py").write_text("# Deep\n")

        result = enumerate_source_files(tmp_path)

        rel_paths = {str(p.relative_to(tmp_path)) for p in result}
        assert "a/b/c/d/deep.py" in rel_paths

    def test_returns_absolute_paths(self, tmp_path):
        """Returned paths are absolute."""
        src_dir = tmp_path / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.py").write_text("# Python\n")

        result = enumerate_source_files(tmp_path)

        assert len(result) > 0
        for path in result:
            assert path.is_absolute()


class TestSourceExtensionsConstant:
    """Tests for the SOURCE_EXTENSIONS constant."""

    def test_common_languages_included(self):
        """Common programming language extensions are included."""
        # Python
        assert "py" in SOURCE_EXTENSIONS
        # JavaScript/TypeScript
        assert "js" in SOURCE_EXTENSIONS
        assert "ts" in SOURCE_EXTENSIONS
        assert "jsx" in SOURCE_EXTENSIONS
        assert "tsx" in SOURCE_EXTENSIONS
        # Go
        assert "go" in SOURCE_EXTENSIONS
        # Rust
        assert "rs" in SOURCE_EXTENSIONS
        # Ruby
        assert "rb" in SOURCE_EXTENSIONS
        # Java
        assert "java" in SOURCE_EXTENSIONS
        # Kotlin
        assert "kt" in SOURCE_EXTENSIONS
        # Swift
        assert "swift" in SOURCE_EXTENSIONS
        # C/C++
        assert "c" in SOURCE_EXTENSIONS
        assert "cpp" in SOURCE_EXTENSIONS
        assert "h" in SOURCE_EXTENSIONS
        # C#
        assert "cs" in SOURCE_EXTENSIONS

    def test_extensions_are_lowercase_without_dot(self):
        """All extensions are lowercase and without leading dot."""
        for ext in SOURCE_EXTENSIONS:
            assert ext == ext.lower()
            assert not ext.startswith(".")


class TestFallbackExcludeDirsConstant:
    """Tests for the FALLBACK_EXCLUDE_DIRS constant."""

    def test_common_exclude_dirs_included(self):
        """Common directories to exclude are included."""
        assert ".git" in FALLBACK_EXCLUDE_DIRS
        assert "__pycache__" in FALLBACK_EXCLUDE_DIRS
        assert "node_modules" in FALLBACK_EXCLUDE_DIRS
        assert ".venv" in FALLBACK_EXCLUDE_DIRS
        assert "venv" in FALLBACK_EXCLUDE_DIRS
