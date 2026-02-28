"""Tests for backreference scanning and management.

# Chunk: docs/chunks/backref_language_agnostic - Tests for backreference filter bug fix
"""

import pathlib
import subprocess

import pytest

from conftest import make_ve_initialized_git_repo
from backreferences import count_backreferences, BackreferenceInfo


class TestCountBackreferencesFilterBugFix:
    """Tests for the filter bug fix where files with only subsystem/narrative refs were excluded."""

    def test_count_backreferences_includes_subsystem_only_files(self, temp_project):
        """File with only # Subsystem: comments is included in results."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only a subsystem backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "subsystem_only.py").write_text(
            '"""Module with only subsystem ref."""\n'
            "# Subsystem: docs/subsystems/test_subsystem - Test subsystem\n"
            "\n"
            "def foo():\n"
            "    pass\n"
        )

        # Add to git so it's discoverable
        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only subsystem ref
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("subsystem_only.py")
        assert len(info.chunk_refs) == 0
        assert len(info.subsystem_refs) == 1
        assert info.subsystem_refs[0] == "test_subsystem"

    def test_count_backreferences_includes_narrative_only_files(self, temp_project):
        """File with only # Narrative: comments is included in results."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only a narrative backreference
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "narrative_only.py").write_text(
            '"""Module with only narrative ref."""\n'
            "# Narrative: docs/narratives/test_narrative - Test narrative\n"
            "\n"
            "class Bar:\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only narrative ref
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("narrative_only.py")
        assert len(info.chunk_refs) == 0
        assert len(info.narrative_refs) == 1
        assert info.narrative_refs[0] == "test_narrative"

    def test_count_backreferences_includes_mixed_refs(self, temp_project):
        """File with subsystem and narrative refs (but no chunk refs) is included."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with subsystem and narrative refs but no chunk refs
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "mixed_no_chunk.py").write_text(
            '"""Module with subsystem and narrative refs but no chunk ref."""\n'
            "# Subsystem: docs/subsystems/auth_system - Auth system\n"
            "# Narrative: docs/narratives/login_flow - Login flow narrative\n"
            "\n"
            "def authenticate():\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with mixed refs
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("mixed_no_chunk.py")
        assert len(info.chunk_refs) == 0
        assert len(info.subsystem_refs) == 1
        assert len(info.narrative_refs) == 1

    def test_count_backreferences_still_includes_chunk_only_files(self, temp_project):
        """File with only # Chunk: comments is still included (regression test)."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with only chunk refs
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "chunk_only.py").write_text(
            '"""Module with only chunk refs."""\n'
            "# Chunk: docs/chunks/test_chunk - Test chunk implementation\n"
            "\n"
            "def process():\n"
            "    pass\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should find the file with only chunk refs
        assert len(results) == 1
        info = results[0]
        assert str(info.file_path).endswith("chunk_only.py")
        assert len(info.chunk_refs) == 1
        assert info.chunk_refs[0] == "test_chunk"

    def test_count_backreferences_excludes_files_with_no_refs(self, temp_project):
        """File with no backreference comments is excluded."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create a file with no backreferences
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "no_refs.py").write_text(
            '"""Module with no backreferences."""\n'
            "\n"
            "def helper():\n"
            "    return 42\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should not find any files
        assert len(results) == 0


class TestCountBackreferencesLanguageAgnostic:
    """Tests for language-agnostic source file scanning."""

    def test_count_backreferences_finds_js_files(self, temp_project):
        """Backreferences in JavaScript files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "app.js").write_text(
            "// Main application\n"
            "# Chunk: docs/chunks/js_feature - JavaScript feature\n"
            "\n"
            "function main() {\n"
            "    console.log('Hello');\n"
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].chunk_refs == ["js_feature"]

    def test_count_backreferences_finds_ts_files(self, temp_project):
        """Backreferences in TypeScript files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "utils.ts").write_text(
            "// TypeScript utilities\n"
            "# Subsystem: docs/subsystems/type_system - Type system\n"
            "\n"
            "export function helper(): string {\n"
            "    return 'test';\n"
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].subsystem_refs == ["type_system"]

    def test_count_backreferences_finds_go_files(self, temp_project):
        """Backreferences in Go files are found."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "main.go").write_text(
            "package main\n"
            "\n"
            "# Chunk: docs/chunks/go_service - Go service implementation\n"
            "\n"
            "func main() {\n"
            '    fmt.Println("Hello")\n'
            "}\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        assert len(results) == 1
        assert results[0].chunk_refs == ["go_service"]

    def test_count_backreferences_with_explicit_patterns_still_works(self, temp_project):
        """Explicit source_patterns argument still works for backward compatibility."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        # Create files in different directories
        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "included.py").write_text(
            "# Chunk: docs/chunks/included - Included\n"
        )

        lib_dir = temp_project / "lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "excluded.py").write_text(
            "# Chunk: docs/chunks/excluded - Excluded\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        # Use explicit pattern to only scan src/
        results = count_backreferences(temp_project, source_patterns=["src/**/*.py"])

        # Should only find the src file
        assert len(results) == 1
        assert results[0].chunk_refs == ["included"]


class TestBackreferenceInfoProperties:
    """Tests for BackreferenceInfo dataclass."""

    def test_unique_chunk_count(self):
        """unique_chunk_count property returns count of unique chunk refs."""
        info = BackreferenceInfo(
            file_path=pathlib.Path("/test/file.py"),
            chunk_refs=["chunk_a", "chunk_a", "chunk_b"],  # 2 unique
            narrative_refs=[],
            subsystem_refs=[],
        )

        assert info.unique_chunk_count == 2

    def test_total_chunk_count(self):
        """total_chunk_count property returns total count including duplicates."""
        info = BackreferenceInfo(
            file_path=pathlib.Path("/test/file.py"),
            chunk_refs=["chunk_a", "chunk_a", "chunk_b"],  # 3 total
            narrative_refs=[],
            subsystem_refs=[],
        )

        assert info.total_chunk_count == 3

    def test_sorting_by_unique_chunk_count(self, temp_project):
        """Results are sorted by unique chunk count descending."""
        make_ve_initialized_git_repo(temp_project)
        temp_project = temp_project.resolve()

        src_dir = temp_project / "src"
        src_dir.mkdir(parents=True)

        # File with many chunk refs
        (src_dir / "many_refs.py").write_text(
            "# Chunk: docs/chunks/a - A\n"
            "# Chunk: docs/chunks/b - B\n"
            "# Chunk: docs/chunks/c - C\n"
        )

        # File with one chunk ref
        (src_dir / "one_ref.py").write_text(
            "# Chunk: docs/chunks/single - Single\n"
        )

        # File with two chunk refs
        (src_dir / "two_refs.py").write_text(
            "# Chunk: docs/chunks/first - First\n"
            "# Chunk: docs/chunks/second - Second\n"
        )

        subprocess.run(["git", "add", "."], cwd=temp_project, check=True)

        results = count_backreferences(temp_project)

        # Should be sorted: many_refs (3), two_refs (2), one_ref (1)
        assert len(results) == 3
        assert results[0].unique_chunk_count == 3
        assert results[1].unique_chunk_count == 2
        assert results[2].unique_chunk_count == 1
