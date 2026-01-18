"""Tests for scratchpad CLI commands."""

from pathlib import Path

import pytest


class TestScratchpadListCommand:
    """Tests for 've scratchpad list' command."""

    def test_scratchpad_list_help_exists(self, runner):
        """Help text available for scratchpad list command."""
        from ve import cli

        result = runner.invoke(cli, ["scratchpad", "list", "--help"])
        assert result.exit_code == 0
        assert "List scratchpad entries" in result.output
        assert "--all" in result.output
        assert "--tasks" in result.output
        assert "--projects" in result.output
        assert "--status" in result.output

    def test_scratchpad_list_empty(self, runner, tmp_path: Path):
        """Empty scratchpad returns success with message."""
        from ve import cli

        # Point to empty scratchpad root
        result = runner.invoke(
            cli,
            ["scratchpad", "list", "--scratchpad-root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "No scratchpad entries found" in result.output

    def test_scratchpad_list_current_project(self, runner, tmp_path: Path):
        """List shows entries for current project context."""
        from ve import cli

        # Setup: create scratchpad with entries
        scratchpad_root = tmp_path / "scratchpad"
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        # Create scratchpad entries for the project
        context_path = scratchpad_root / "my-project"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)
        chunk_path = chunks_dir / "test-chunk"
        chunk_path.mkdir()
        (chunk_path / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# test-chunk\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list",
                "--scratchpad-root", str(scratchpad_root),
                "--project-dir", str(project_dir),
            ],
        )
        assert result.exit_code == 0
        assert "test-chunk" in result.output
        assert "IMPLEMENTING" in result.output

    def test_scratchpad_list_all_contexts(self, runner, tmp_path: Path):
        """List --all shows entries from all contexts."""
        from ve import cli

        # Setup: create scratchpad with multiple contexts
        scratchpad_root = tmp_path / "scratchpad"

        # Create project-a context
        context_a = scratchpad_root / "project-a"
        chunks_a = context_a / "chunks"
        chunks_a.mkdir(parents=True)
        chunk_a = chunks_a / "chunk-a"
        chunk_a.mkdir()
        (chunk_a / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# chunk-a\n'
        )

        # Create project-b context
        context_b = scratchpad_root / "project-b"
        chunks_b = context_b / "chunks"
        chunks_b.mkdir(parents=True)
        chunk_b = chunks_b / "chunk-b"
        chunk_b.mkdir()
        (chunk_b / "GOAL.md").write_text(
            '---\nstatus: ACTIVE\ncreated_at: "2025-01-02T10:00:00"\n---\n# chunk-b\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all",
                "--scratchpad-root", str(scratchpad_root),
            ],
        )
        assert result.exit_code == 0
        assert "project-a" in result.output
        assert "project-b" in result.output
        assert "chunk-a" in result.output
        assert "chunk-b" in result.output

    def test_scratchpad_list_tasks_only(self, runner, tmp_path: Path):
        """List --tasks shows only task contexts."""
        from ve import cli

        # Setup: create scratchpad with both project and task contexts
        scratchpad_root = tmp_path / "scratchpad"

        # Create project context
        project_ctx = scratchpad_root / "my-project"
        project_chunks = project_ctx / "chunks"
        project_chunks.mkdir(parents=True)
        proj_chunk = project_chunks / "proj-chunk"
        proj_chunk.mkdir()
        (proj_chunk / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# proj-chunk\n'
        )

        # Create task context
        task_ctx = scratchpad_root / "task:my-task"
        task_chunks = task_ctx / "chunks"
        task_chunks.mkdir(parents=True)
        task_chunk = task_chunks / "task-chunk"
        task_chunk.mkdir()
        (task_chunk / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# task-chunk\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all", "--tasks",
                "--scratchpad-root", str(scratchpad_root),
            ],
        )
        assert result.exit_code == 0
        assert "task:my-task" in result.output
        assert "task-chunk" in result.output
        # Project context should NOT appear
        assert "my-project" not in result.output
        assert "proj-chunk" not in result.output

    def test_scratchpad_list_projects_only(self, runner, tmp_path: Path):
        """List --projects shows only project contexts."""
        from ve import cli

        # Setup: create scratchpad with both project and task contexts
        scratchpad_root = tmp_path / "scratchpad"

        # Create project context
        project_ctx = scratchpad_root / "my-project"
        project_chunks = project_ctx / "chunks"
        project_chunks.mkdir(parents=True)
        proj_chunk = project_chunks / "proj-chunk"
        proj_chunk.mkdir()
        (proj_chunk / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# proj-chunk\n'
        )

        # Create task context
        task_ctx = scratchpad_root / "task:my-task"
        task_chunks = task_ctx / "chunks"
        task_chunks.mkdir(parents=True)
        task_chunk = task_chunks / "task-chunk"
        task_chunk.mkdir()
        (task_chunk / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# task-chunk\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all", "--projects",
                "--scratchpad-root", str(scratchpad_root),
            ],
        )
        assert result.exit_code == 0
        assert "my-project" in result.output
        assert "proj-chunk" in result.output
        # Task context should NOT appear
        assert "task:my-task" not in result.output
        assert "task-chunk" not in result.output

    def test_scratchpad_list_filter_by_status(self, runner, tmp_path: Path):
        """List --status filters by status value."""
        from ve import cli

        # Setup: create scratchpad with mixed statuses
        scratchpad_root = tmp_path / "scratchpad"
        context_path = scratchpad_root / "test-project"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)

        # Create IMPLEMENTING chunk
        impl_chunk = chunks_dir / "implementing-chunk"
        impl_chunk.mkdir()
        (impl_chunk / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# impl\n'
        )

        # Create ACTIVE chunk
        active_chunk = chunks_dir / "active-chunk"
        active_chunk.mkdir()
        (active_chunk / "GOAL.md").write_text(
            '---\nstatus: ACTIVE\ncreated_at: "2025-01-02T10:00:00"\n---\n# active\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all",
                "--scratchpad-root", str(scratchpad_root),
                "--status", "IMPLEMENTING",
            ],
        )
        assert result.exit_code == 0
        assert "implementing-chunk" in result.output
        assert "active-chunk" not in result.output

    def test_scratchpad_list_includes_narratives(self, runner, tmp_path: Path):
        """List includes both chunks and narratives."""
        from ve import cli

        # Setup: create scratchpad with chunks and narratives
        scratchpad_root = tmp_path / "scratchpad"
        context_path = scratchpad_root / "test-project"

        # Create chunk
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)
        chunk_path = chunks_dir / "my-chunk"
        chunk_path.mkdir()
        (chunk_path / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# my-chunk\n'
        )

        # Create narrative
        narratives_dir = context_path / "narratives"
        narratives_dir.mkdir(parents=True)
        narrative_path = narratives_dir / "my-narrative"
        narrative_path.mkdir()
        (narrative_path / "OVERVIEW.md").write_text(
            '---\nstatus: DRAFTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# my-narrative\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all",
                "--scratchpad-root", str(scratchpad_root),
            ],
        )
        assert result.exit_code == 0
        assert "my-chunk" in result.output
        assert "my-narrative" in result.output
        assert "chunks:" in result.output
        assert "narratives:" in result.output

    def test_scratchpad_list_output_format(self, runner, tmp_path: Path):
        """List output has expected grouped format."""
        from ve import cli

        # Setup: create scratchpad with entries
        scratchpad_root = tmp_path / "scratchpad"
        context_path = scratchpad_root / "vibe-engineer"
        chunks_dir = context_path / "chunks"
        chunks_dir.mkdir(parents=True)
        chunk_path = chunks_dir / "test-chunk"
        chunk_path.mkdir()
        (chunk_path / "GOAL.md").write_text(
            '---\nstatus: IMPLEMENTING\ncreated_at: "2025-01-01T10:00:00"\n---\n# test-chunk\n'
        )

        result = runner.invoke(
            cli,
            [
                "scratchpad", "list", "--all",
                "--scratchpad-root", str(scratchpad_root),
            ],
        )
        assert result.exit_code == 0
        # Check for expected format: project header with slash
        assert "vibe-engineer/" in result.output
        # Check for chunks section
        assert "chunks:" in result.output
        # Check for entry with status
        assert "test-chunk" in result.output
        assert "IMPLEMENTING" in result.output


class TestScratchpadGroupHelp:
    """Tests for scratchpad command group."""

    def test_scratchpad_group_exists(self, runner):
        """Scratchpad command group exists."""
        from ve import cli

        result = runner.invoke(cli, ["scratchpad", "--help"])
        assert result.exit_code == 0
        assert "Scratchpad commands" in result.output
        assert "list" in result.output
