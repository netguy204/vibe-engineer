"""Tests for cluster rename functionality."""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from cluster_rename import (
    find_chunks_by_prefix,
    check_rename_collisions,
    is_git_clean,
    find_created_after_references,
    find_subsystem_chunk_references,
    find_narrative_chunk_references,
    find_investigation_chunk_references,
    find_code_backreferences,
    find_prose_references,
    cluster_rename,
    format_dry_run_output,
    RenamePreview,
    ClusterRenameResult,
)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def git_project(tmp_path):
    """Create a temporary project with git repo and VE structure."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create VE directory structure
    (tmp_path / "docs" / "chunks").mkdir(parents=True)
    (tmp_path / "docs" / "narratives").mkdir(parents=True)
    (tmp_path / "docs" / "investigations").mkdir(parents=True)
    (tmp_path / "docs" / "subsystems").mkdir(parents=True)
    (tmp_path / "src").mkdir(parents=True)

    # Create initial commit
    (tmp_path / "README.md").write_text("# Test Project\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path


def create_chunk(project_dir, name, created_after=None):
    """Helper to create a chunk with GOAL.md."""
    chunk_dir = project_dir / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    created_after_yaml = ""
    if created_after:
        created_after_yaml = "created_after:\n" + "\n".join(f"- {ca}" for ca in created_after)

    (chunk_dir / "GOAL.md").write_text(f"""---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems: []
{created_after_yaml}
---

# Chunk Goal

Test chunk {name}
""")
    return chunk_dir


def create_subsystem(project_dir, name, chunks=None):
    """Helper to create a subsystem with OVERVIEW.md."""
    subsystem_dir = project_dir / "docs" / "subsystems" / name
    subsystem_dir.mkdir(parents=True, exist_ok=True)

    chunks_yaml = ""
    if chunks:
        chunks_yaml = "chunks:\n" + "\n".join(
            f'- chunk_id: "{c[0]}"\n  relationship: {c[1]}' for c in chunks
        )

    (subsystem_dir / "OVERVIEW.md").write_text(f"""---
status: DISCOVERING
{chunks_yaml}
code_references: []
proposed_chunks: []
created_after: []
dependents: []
---

# Subsystem Overview

Test subsystem {name}
""")
    return subsystem_dir


def create_narrative(project_dir, name, proposed_chunks=None):
    """Helper to create a narrative with OVERVIEW.md."""
    narrative_dir = project_dir / "docs" / "narratives" / name
    narrative_dir.mkdir(parents=True, exist_ok=True)

    proposed_yaml = ""
    if proposed_chunks:
        proposed_yaml = "proposed_chunks:\n" + "\n".join(
            f'- prompt: "Implement {pc}"\n  chunk_directory: {pc}' if pc else f'- prompt: "Future work"\n  chunk_directory: null'
            for pc in proposed_chunks
        )

    (narrative_dir / "OVERVIEW.md").write_text(f"""---
status: DRAFTING
advances_trunk_goal: null
{proposed_yaml}
created_after: []
dependents: []
---

# Narrative Overview

Test narrative {name}
""")
    return narrative_dir


def create_investigation(project_dir, name, proposed_chunks=None):
    """Helper to create an investigation with OVERVIEW.md."""
    investigation_dir = project_dir / "docs" / "investigations" / name
    investigation_dir.mkdir(parents=True, exist_ok=True)

    proposed_yaml = ""
    if proposed_chunks:
        proposed_yaml = "proposed_chunks:\n" + "\n".join(
            f'- prompt: "Implement {pc}"\n  chunk_directory: {pc}' if pc else f'- prompt: "Future work"\n  chunk_directory: null'
            for pc in proposed_chunks
        )

    (investigation_dir / "OVERVIEW.md").write_text(f"""---
status: ONGOING
trigger: null
{proposed_yaml}
created_after: []
dependents: []
---

# Investigation Overview

Test investigation {name}
""")
    return investigation_dir


class TestFindChunksByPrefix:
    """Tests for find_chunks_by_prefix function."""

    def test_matches_underscore_separated_prefix(self, git_project):
        """Finds chunks starting with {prefix}_."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "task_config")
        create_chunk(git_project, "other_feature")

        result = find_chunks_by_prefix(git_project, "task")

        assert "task_init" in result
        assert "task_config" in result
        assert "other_feature" not in result

    def test_no_match_returns_empty_list(self, git_project):
        """Returns empty list when no chunks match."""
        create_chunk(git_project, "feature_one")

        result = find_chunks_by_prefix(git_project, "task")

        assert result == []

    def test_partial_prefix_not_matched(self, git_project):
        """Does not match 'task' when only 'taskforce' exists."""
        create_chunk(git_project, "taskforce")  # No underscore after task
        create_chunk(git_project, "task_init")

        result = find_chunks_by_prefix(git_project, "task")

        assert "task_init" in result
        assert "taskforce" not in result

    def test_handles_legacy_numbered_format(self, git_project):
        """Matches chunks in legacy {NNNN}-{short_name} format."""
        create_chunk(git_project, "0001-task_init")
        create_chunk(git_project, "0002-task_config")
        create_chunk(git_project, "0003-other_feature")

        result = find_chunks_by_prefix(git_project, "task")

        assert "0001-task_init" in result
        assert "0002-task_config" in result
        assert "0003-other_feature" not in result


class TestCheckRenameCollisions:
    """Tests for check_rename_collisions function."""

    def test_detects_collision(self, git_project):
        """Detects when target name already exists."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "chunk_init")  # Would collide

        matching = ["task_init"]
        errors = check_rename_collisions(git_project, "task", "chunk", matching)

        assert len(errors) == 1
        assert "chunk_init" in errors[0]
        assert "already exists" in errors[0]

    def test_no_collision_returns_empty(self, git_project):
        """Returns empty list when no collisions."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "task_config")

        matching = ["task_init", "task_config"]
        errors = check_rename_collisions(git_project, "task", "chunk", matching)

        assert errors == []

    def test_preserves_legacy_sequence_number(self, git_project):
        """Legacy format chunks preserve sequence number in collision check."""
        create_chunk(git_project, "0001-task_init")
        create_chunk(git_project, "0001-chunk_init")  # Same sequence, would collide

        matching = ["0001-task_init"]
        errors = check_rename_collisions(git_project, "task", "chunk", matching)

        assert len(errors) == 1
        assert "0001-chunk_init" in errors[0]


class TestIsGitClean:
    """Tests for is_git_clean function."""

    def test_clean_repo_returns_true(self, git_project):
        """Returns True for clean working tree."""
        result = is_git_clean(git_project)
        assert result is True

    def test_uncommitted_changes_returns_false(self, git_project):
        """Returns False when uncommitted changes exist."""
        (git_project / "new_file.txt").write_text("uncommitted content")

        result = is_git_clean(git_project)
        assert result is False

    def test_staged_changes_returns_false(self, git_project):
        """Returns False when staged changes exist."""
        (git_project / "staged_file.txt").write_text("staged content")
        subprocess.run(
            ["git", "add", "staged_file.txt"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )

        result = is_git_clean(git_project)
        assert result is False


class TestFindCreatedAfterReferences:
    """Tests for find_created_after_references function."""

    def test_finds_created_after_references(self, git_project):
        """Finds references in chunk GOAL.md created_after fields."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "other_chunk", created_after=["task_init"])

        updates = find_created_after_references(git_project, "task", "chunk")

        assert len(updates) == 1
        assert updates[0].old_value == "task_init"
        assert updates[0].new_value == "chunk_init"
        assert updates[0].field == "created_after"

    def test_ignores_non_matching_references(self, git_project):
        """Ignores created_after references that don't match prefix."""
        create_chunk(git_project, "feature_one")
        create_chunk(git_project, "other_chunk", created_after=["feature_one"])

        updates = find_created_after_references(git_project, "task", "chunk")

        assert updates == []


class TestFindSubsystemChunkReferences:
    """Tests for find_subsystem_chunk_references function."""

    def test_finds_subsystem_chunk_references(self, git_project):
        """Finds references in subsystem chunks[].chunk_id fields."""
        create_chunk(git_project, "task_init")
        create_subsystem(
            git_project, "my_subsystem",
            chunks=[("task_init", "implements")]
        )

        updates = find_subsystem_chunk_references(git_project, "task", "chunk")

        assert len(updates) == 1
        assert updates[0].old_value == "task_init"
        assert updates[0].new_value == "chunk_init"
        assert "chunk_id" in updates[0].field


class TestFindNarrativeChunkReferences:
    """Tests for find_narrative_chunk_references function."""

    def test_finds_narrative_references(self, git_project):
        """Finds references in narrative proposed_chunks."""
        create_chunk(git_project, "task_init")
        create_narrative(
            git_project, "my_narrative",
            proposed_chunks=["task_init"]
        )

        updates = find_narrative_chunk_references(git_project, "task", "chunk")

        assert len(updates) == 1
        assert updates[0].old_value == "task_init"
        assert updates[0].new_value == "chunk_init"


class TestFindInvestigationChunkReferences:
    """Tests for find_investigation_chunk_references function."""

    def test_finds_investigation_references(self, git_project):
        """Finds references in investigation proposed_chunks."""
        create_chunk(git_project, "task_init")
        create_investigation(
            git_project, "my_investigation",
            proposed_chunks=["task_init"]
        )

        updates = find_investigation_chunk_references(git_project, "task", "chunk")

        assert len(updates) == 1
        assert updates[0].old_value == "task_init"
        assert updates[0].new_value == "chunk_init"


class TestFindCodeBackreferences:
    """Tests for find_code_backreferences function."""

    def test_finds_code_backreferences(self, git_project):
        """Finds # Chunk: comments in source files."""
        create_chunk(git_project, "task_init")

        # Create a source file with backreference
        (git_project / "src" / "example.py").write_text(
            '# Chunk: docs/chunks/task_init - Test backreference\n'
            'def foo():\n'
            '    pass\n'
        )

        matching_chunks = ["task_init"]
        updates = find_code_backreferences(git_project, "task", "chunk", matching_chunks)

        assert len(updates) == 1
        assert "task_init" in updates[0].old_line
        assert "chunk_init" in updates[0].new_line
        assert updates[0].line_number == 1


class TestFindProseReferences:
    """Tests for find_prose_references function."""

    def test_finds_prose_references(self, git_project):
        """Finds potential prose references in markdown."""
        create_chunk(git_project, "task_init")

        # Create a markdown file with prose reference
        (git_project / "docs" / "NOTES.md").write_text(
            '# Notes\n\n'
            'See task_init for implementation details.\n'
        )

        matching_chunks = ["task_init"]
        refs = find_prose_references(git_project, matching_chunks)

        # Should find at least the NOTES.md reference
        # (may also find references in the chunk's own GOAL.md)
        notes_refs = [r for r in refs if "NOTES.md" in str(r[0])]
        assert len(notes_refs) == 1
        assert "task_init" in notes_refs[0][2]

    def test_excludes_frontmatter_fields(self, git_project):
        """Excludes references in frontmatter fields we auto-update."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "other", created_after=["task_init"])

        matching_chunks = ["task_init"]
        refs = find_prose_references(git_project, matching_chunks)

        # Should not include the created_after reference
        for ref in refs:
            assert "created_after:" not in ref[2]


class TestClusterRenameCLI:
    """Tests for ve chunk cluster-rename CLI command."""

    def test_dry_run_shows_changes_without_applying(self, runner, git_project):
        """Default dry-run shows what would change."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "task_config")

        # Commit the chunks
        subprocess.run(["git", "add", "."], cwd=git_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add chunks"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--project-dir", str(git_project)],
        )

        assert result.exit_code == 0
        assert "task_init" in result.output
        assert "chunk_init" in result.output
        assert "Would rename" in result.output

        # Verify no actual changes
        assert (git_project / "docs" / "chunks" / "task_init").exists()
        assert not (git_project / "docs" / "chunks" / "chunk_init").exists()

    def test_execute_applies_changes(self, runner, git_project):
        """--execute flag applies all changes."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "task_config")

        # Commit the chunks
        subprocess.run(["git", "add", "."], cwd=git_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add chunks"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--execute", "--project-dir", str(git_project)],
        )

        assert result.exit_code == 0
        assert "Renamed 2 directories" in result.output

        # Verify actual changes
        assert not (git_project / "docs" / "chunks" / "task_init").exists()
        assert not (git_project / "docs" / "chunks" / "task_config").exists()
        assert (git_project / "docs" / "chunks" / "chunk_init").exists()
        assert (git_project / "docs" / "chunks" / "chunk_config").exists()

    def test_fails_on_no_matching_chunks(self, runner, git_project):
        """Exits with error if no chunks match prefix."""
        create_chunk(git_project, "feature_one")

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--project-dir", str(git_project)],
        )

        assert result.exit_code != 0
        assert "No chunks found" in result.output

    def test_fails_on_collision(self, runner, git_project):
        """Exits with error if rename would cause collision."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "chunk_init")  # Collision target

        # Commit
        subprocess.run(["git", "add", "."], cwd=git_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add chunks"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--execute", "--project-dir", str(git_project)],
        )

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_warns_on_dirty_git_but_proceeds(self, runner, git_project):
        """Shows warning if git working tree is dirty but proceeds with operation."""
        create_chunk(git_project, "task_init")

        # Don't commit - leave dirty

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--execute", "--project-dir", str(git_project)],
        )

        # Should succeed but show warning
        assert result.exit_code == 0
        assert "uncommitted changes" in result.output.lower()
        # Verify rename still happened
        assert not (git_project / "docs" / "chunks" / "task_init").exists()
        assert (git_project / "docs" / "chunks" / "chunk_init").exists()

    def test_updates_created_after_references(self, runner, git_project):
        """Updates created_after references in other chunks."""
        create_chunk(git_project, "task_init")
        create_chunk(git_project, "dependent", created_after=["task_init"])

        # Commit
        subprocess.run(["git", "add", "."], cwd=git_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add chunks"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )

        result = runner.invoke(
            cli,
            ["chunk", "cluster-rename", "task", "chunk", "--execute", "--project-dir", str(git_project)],
        )

        assert result.exit_code == 0

        # Verify created_after was updated
        dependent_goal = (git_project / "docs" / "chunks" / "dependent" / "GOAL.md").read_text()
        assert "chunk_init" in dependent_goal
        assert "task_init" not in dependent_goal


class TestFormatDryRunOutput:
    """Tests for format_dry_run_output function."""

    def test_formats_all_sections(self, tmp_path):
        """Formats all sections of the preview."""
        from cluster_rename import FrontmatterUpdate, BackreferenceUpdate

        preview = RenamePreview(
            directories=[("task_init", "chunk_init")],
            frontmatter_updates=[
                FrontmatterUpdate(
                    file_path=tmp_path / "docs" / "chunks" / "other" / "GOAL.md",
                    field="created_after",
                    old_value="task_init",
                    new_value="chunk_init",
                )
            ],
            backreference_updates=[
                BackreferenceUpdate(
                    file_path=tmp_path / "src" / "example.py",
                    line_number=5,
                    old_line="# Chunk: docs/chunks/task_init",
                    new_line="# Chunk: docs/chunks/chunk_init",
                )
            ],
            prose_references=[
                (tmp_path / "docs" / "NOTES.md", 10, "See task_init for details"),
            ],
        )

        output = format_dry_run_output(preview, tmp_path)

        assert "Directories to be renamed" in output
        assert "task_init -> docs/chunks/chunk_init" in output
        assert "Frontmatter references" in output
        assert "created_after" in output
        assert "Code backreferences" in output
        assert "example.py:5" in output
        assert "Prose references" in output
        assert "NOTES.md:10" in output
