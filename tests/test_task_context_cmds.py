"""Integration tests for task-aware chunk commands (activate, overlap)."""
# Chunk: docs/chunks/taskdir_context_cmds - Tests for task context support

import pytest
from click.testing import CliRunner

from ve import cli
from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestChunkActivateInTaskContext:
    """Tests for ve chunk activate in task directory context."""

    def test_activates_chunk_in_external_repo(self, tmp_path):
        """Activates FUTURE chunk found in external repo."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create a FUTURE chunk in external repo
        chunk_dir = external_path / "docs" / "chunks" / "auth_token"
        chunk_dir.mkdir(parents=True)
        goal_content = """---
status: FUTURE
created_after: []
---

# auth_token

Goal content.
"""
        (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Activated acme/ext:docs/chunks/auth_token" in result.output

        # Verify status was changed
        updated_content = (chunk_dir / "GOAL.md").read_text()
        assert "status: IMPLEMENTING" in updated_content

    def test_activates_chunk_in_project_repo(self, tmp_path):
        """Activates FUTURE chunk found in a project repo."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create a FUTURE chunk in project repo (not external)
        chunk_dir = project_paths[0] / "docs" / "chunks" / "local_feature"
        chunk_dir.mkdir(parents=True)
        goal_content = """---
status: FUTURE
created_after: []
---

# local_feature

Goal content.
"""
        (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "local_feature", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Activated acme/proj1:docs/chunks/local_feature" in result.output

    def test_prefers_external_repo_over_project(self, tmp_path):
        """External repo chunk is activated when same name exists in both."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create same-named chunk in both repos
        for repo_path in [external_path, project_paths[0]]:
            chunk_dir = repo_path / "docs" / "chunks" / "shared_name"
            chunk_dir.mkdir(parents=True)
            goal_content = """---
status: FUTURE
created_after: []
---

# shared_name

Goal content.
"""
            (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "shared_name", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Should prefer external repo
        assert "Activated acme/ext:docs/chunks/shared_name" in result.output

    def test_error_when_chunk_not_found(self, tmp_path):
        """Reports error when chunk doesn't exist in any repo."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "nonexistent", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_error_when_chunk_already_implementing(self, tmp_path):
        """Reports error when trying to activate non-FUTURE chunk."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create an IMPLEMENTING chunk
        chunk_dir = external_path / "docs" / "chunks" / "active_chunk"
        chunk_dir.mkdir(parents=True)
        goal_content = """---
status: IMPLEMENTING
created_after: []
---

# active_chunk

Goal content.
"""
        (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "active_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "Cannot activate" in result.output or "not FUTURE" in result.output

    def test_skips_external_references_in_projects(self, tmp_path):
        """Skips external.yaml references when searching project repos."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create a FUTURE chunk in external repo
        ext_chunk_dir = external_path / "docs" / "chunks" / "auth_token"
        ext_chunk_dir.mkdir(parents=True)
        goal_content = """---
status: FUTURE
created_after: []
---

# auth_token

Goal content.
"""
        (ext_chunk_dir / "GOAL.md").write_text(goal_content)

        # Create external.yaml reference in project (should be skipped)
        proj_chunk_dir = project_paths[0] / "docs" / "chunks" / "auth_token"
        proj_chunk_dir.mkdir(parents=True)
        external_yaml = """repo: acme/ext
artifact_type: chunk
artifact_id: auth_token
track: main
pinned: abc123
"""
        (proj_chunk_dir / "external.yaml").write_text(external_yaml)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "auth_token", "--project-dir", str(task_dir)]
        )

        # Should activate the external repo's chunk, not error on the reference
        assert result.exit_code == 0
        assert "Activated acme/ext:docs/chunks/auth_token" in result.output


class TestChunkActivateOutsideTaskContext:
    """Tests for ve chunk activate outside task directory context."""

    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create a FUTURE chunk
        chunk_dir = project_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        goal_content = """---
status: FUTURE
created_after: []
---

# my_feature

Goal content.
"""
        (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "activate", "my_feature", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "Activated docs/chunks/my_feature" in result.output


class TestChunkOverlapInTaskContext:
    """Tests for ve chunk overlap in task directory context."""

    def test_finds_overlap_in_external_repo(self, tmp_path):
        """Finds overlapping chunks within external repo."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create first ACTIVE chunk with code reference
        chunk1_dir = external_path / "docs" / "chunks" / "chunk1"
        chunk1_dir.mkdir(parents=True)
        chunk1_goal = """---
status: ACTIVE
created_after: []
code_references:
- ref: src/foo.py#Bar
  implements: Bar class
---

# chunk1

First chunk.
"""
        (chunk1_dir / "GOAL.md").write_text(chunk1_goal)

        # Create second IMPLEMENTING chunk with overlapping code reference
        chunk2_dir = external_path / "docs" / "chunks" / "chunk2"
        chunk2_dir.mkdir(parents=True)
        chunk2_goal = """---
status: IMPLEMENTING
created_after:
- chunk1
code_references:
- ref: src/foo.py#Bar
  implements: Bar class update
---

# chunk2

Second chunk overlapping with first.
"""
        (chunk2_dir / "GOAL.md").write_text(chunk2_goal)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "chunk2", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "acme/ext:docs/chunks/chunk1" in result.output

    def test_finds_overlap_across_repos(self, tmp_path):
        """Finds overlapping chunks across external and project repos."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create ACTIVE chunk in project repo
        proj_chunk_dir = project_paths[0] / "docs" / "chunks" / "proj_chunk"
        proj_chunk_dir.mkdir(parents=True)
        proj_chunk_goal = """---
status: ACTIVE
created_after: []
code_references:
- ref: src/service.py#handle_request
  implements: Request handler
---

# proj_chunk

Project chunk.
"""
        (proj_chunk_dir / "GOAL.md").write_text(proj_chunk_goal)

        # Create IMPLEMENTING chunk in external repo with cross-project reference
        ext_chunk_dir = external_path / "docs" / "chunks" / "ext_chunk"
        ext_chunk_dir.mkdir(parents=True)
        ext_chunk_goal = """---
status: IMPLEMENTING
created_after: []
code_references:
- ref: proj1::src/service.py#handle_request
  implements: Request handler update
---

# ext_chunk

External chunk with cross-project reference.
"""
        (ext_chunk_dir / "GOAL.md").write_text(ext_chunk_goal)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "ext_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "acme/proj1:docs/chunks/proj_chunk" in result.output

    def test_no_overlap_different_files(self, tmp_path):
        """No overlap when chunks reference different files."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create first ACTIVE chunk
        chunk1_dir = external_path / "docs" / "chunks" / "chunk1"
        chunk1_dir.mkdir(parents=True)
        chunk1_goal = """---
status: ACTIVE
created_after: []
code_references:
- ref: src/foo.py#Foo
  implements: Foo class
---

# chunk1

First chunk.
"""
        (chunk1_dir / "GOAL.md").write_text(chunk1_goal)

        # Create second IMPLEMENTING chunk with different file
        chunk2_dir = external_path / "docs" / "chunks" / "chunk2"
        chunk2_dir.mkdir(parents=True)
        chunk2_goal = """---
status: IMPLEMENTING
created_after:
- chunk1
code_references:
- ref: src/bar.py#Bar
  implements: Bar class
---

# chunk2

Second chunk with different file.
"""
        (chunk2_dir / "GOAL.md").write_text(chunk2_goal)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "chunk2", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # No output means no overlap
        assert "chunk1" not in result.output

    def test_no_overlap_with_non_active_chunks(self, tmp_path):
        """Ignores FUTURE and SUPERSEDED chunks in overlap detection."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create FUTURE chunk (should be ignored)
        chunk1_dir = external_path / "docs" / "chunks" / "future_chunk"
        chunk1_dir.mkdir(parents=True)
        chunk1_goal = """---
status: FUTURE
created_after: []
code_references:
- ref: src/foo.py#Bar
  implements: Bar class
---

# future_chunk

Future chunk.
"""
        (chunk1_dir / "GOAL.md").write_text(chunk1_goal)

        # Create IMPLEMENTING chunk with same reference
        chunk2_dir = external_path / "docs" / "chunks" / "impl_chunk"
        chunk2_dir.mkdir(parents=True)
        chunk2_goal = """---
status: IMPLEMENTING
created_after:
- future_chunk
code_references:
- ref: src/foo.py#Bar
  implements: Bar class update
---

# impl_chunk

Implementing chunk.
"""
        (chunk2_dir / "GOAL.md").write_text(chunk2_goal)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "impl_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # FUTURE chunk should not appear in overlap
        assert "future_chunk" not in result.output

    def test_error_when_chunk_not_found(self, tmp_path):
        """Reports error when target chunk doesn't exist."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "nonexistent", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output


class TestChunkOverlapOutsideTaskContext:
    """Tests for ve chunk overlap outside task directory context."""

    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create ACTIVE chunk
        chunk1_dir = project_path / "docs" / "chunks" / "chunk1"
        chunk1_dir.mkdir(parents=True)
        chunk1_goal = """---
status: ACTIVE
created_after: []
code_references:
- ref: src/foo.py#Bar
  implements: Bar class
---

# chunk1

First chunk.
"""
        (chunk1_dir / "GOAL.md").write_text(chunk1_goal)

        # Create IMPLEMENTING chunk with overlap
        chunk2_dir = project_path / "docs" / "chunks" / "chunk2"
        chunk2_dir.mkdir(parents=True)
        chunk2_goal = """---
status: IMPLEMENTING
created_after:
- chunk1
code_references:
- ref: src/foo.py#Bar
  implements: Bar class update
---

# chunk2

Second chunk.
"""
        (chunk2_dir / "GOAL.md").write_text(chunk2_goal)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "overlap", "chunk2", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/chunks/chunk1" in result.output
        # Should NOT have repo prefix in single-repo mode
        assert "acme/" not in result.output


class TestResolveProjectQualifiedRef:
    """Unit tests for resolve_project_qualified_ref helper."""

    def test_parses_project_qualified_ref(self, tmp_path):
        """Parses project::file#symbol format correctly."""
        from task_utils import resolve_project_qualified_ref

        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        project_path, file_path, symbol_path = resolve_project_qualified_ref(
            "proj1::src/foo.py#Bar",
            task_dir,
            ["acme/proj1"],
        )

        assert project_path == project_paths[0]
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_parses_ref_without_symbol(self, tmp_path):
        """Parses project::file format (no symbol)."""
        from task_utils import resolve_project_qualified_ref

        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        project_path, file_path, symbol_path = resolve_project_qualified_ref(
            "proj1::src/foo.py",
            task_dir,
            ["acme/proj1"],
        )

        assert project_path == project_paths[0]
        assert file_path == "src/foo.py"
        assert symbol_path is None

    def test_uses_default_for_non_qualified_ref(self, tmp_path):
        """Uses default_project for refs without :: prefix."""
        from task_utils import resolve_project_qualified_ref

        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        project_path, file_path, symbol_path = resolve_project_qualified_ref(
            "src/foo.py#Bar",
            task_dir,
            ["acme/proj1"],
            default_project=project_paths[0],
        )

        assert project_path == project_paths[0]
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"

    def test_error_without_default_for_non_qualified(self, tmp_path):
        """Raises error when non-qualified ref has no default_project."""
        from task_utils import resolve_project_qualified_ref

        task_dir, _, _ = setup_task_directory(tmp_path, project_names=["proj1"])

        with pytest.raises(ValueError) as exc_info:
            resolve_project_qualified_ref(
                "src/foo.py#Bar",
                task_dir,
                ["acme/proj1"],
                default_project=None,
            )

        assert "without a default project" in str(exc_info.value)

    def test_handles_short_project_name(self, tmp_path):
        """Resolves short project name (without org prefix)."""
        from task_utils import resolve_project_qualified_ref

        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Use short name "proj1" instead of "acme/proj1"
        project_path, file_path, symbol_path = resolve_project_qualified_ref(
            "proj1::src/foo.py#Bar",
            task_dir,
            ["acme/proj1"],
        )

        assert project_path == project_paths[0]
        assert file_path == "src/foo.py"
        assert symbol_path == "Bar"
