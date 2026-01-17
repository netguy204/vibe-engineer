"""Tests for narrative commands with scratchpad storage.

# Chunk: docs/chunks/scratchpad_narrative_commands - Scratchpad narrative commands
# Narrative: docs/narratives/global_scratchpad - User-global scratchpad for flow artifacts
"""

import pathlib
import pytest

from ve import cli


class TestNarrativeCreateScratchpad:
    """Tests for 've narrative create' with scratchpad storage."""

    @pytest.fixture
    def scratchpad_setup(self, tmp_path, monkeypatch):
        """Set up scratchpad root and project directory.

        Returns:
            tuple: (scratchpad_root, project_dir)
        """
        # Create a fake project directory
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        # Create a fake scratchpad root
        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        # Patch the Scratchpad.DEFAULT_ROOT to use our test directory
        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        return scratchpad_root, project_dir

    def test_create_narrative_in_scratchpad(self, runner, scratchpad_setup):
        """ve narrative create creates OVERVIEW.md in scratchpad directory."""
        scratchpad_root, project_dir = scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0

        # Verify narrative was created in scratchpad
        expected_path = scratchpad_root / "my-project" / "narratives" / "my_narrative" / "OVERVIEW.md"
        assert expected_path.exists(), f"Expected {expected_path} to exist"

        # Verify output shows scratchpad path
        assert "my_narrative" in result.output
        # Should NOT show docs/narratives/ path anymore
        assert "docs/narratives/" not in result.output

    def test_create_narrative_frontmatter_has_drafting_status(self, runner, scratchpad_setup):
        """Created narrative has DRAFTING status in frontmatter."""
        scratchpad_root, project_dir = scratchpad_setup

        runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        overview_path = scratchpad_root / "my-project" / "narratives" / "my_narrative" / "OVERVIEW.md"
        content = overview_path.read_text()

        assert "status: DRAFTING" in content

    def test_create_narrative_frontmatter_has_created_at(self, runner, scratchpad_setup):
        """Created narrative has created_at timestamp in frontmatter."""
        scratchpad_root, project_dir = scratchpad_setup

        runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        overview_path = scratchpad_root / "my-project" / "narratives" / "my_narrative" / "OVERVIEW.md"
        content = overview_path.read_text()

        assert "created_at:" in content

    def test_create_narrative_output_shows_scratchpad_path(self, runner, scratchpad_setup):
        """Output message includes the scratchpad path."""
        scratchpad_root, project_dir = scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        # The output should mention the scratchpad location
        assert "my_narrative" in result.output

    def test_create_duplicate_narrative_fails(self, runner, scratchpad_setup):
        """Creating a duplicate narrative returns an error."""
        scratchpad_root, project_dir = scratchpad_setup

        # Create first
        runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        # Try to create duplicate
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_dir)]
        )

        assert result.exit_code != 0
        assert "already exists" in result.output.lower()

    def test_create_narrative_invalid_name_fails(self, runner, scratchpad_setup):
        """Creating a narrative with invalid name returns an error."""
        scratchpad_root, project_dir = scratchpad_setup

        # Names starting with numbers are invalid (even after lowercase normalization)
        result = runner.invoke(
            cli,
            ["narrative", "create", "123-invalid", "--project-dir", str(project_dir)]
        )

        assert result.exit_code != 0


class TestNarrativeListScratchpad:
    """Tests for 've narrative list' with scratchpad storage."""

    @pytest.fixture
    def scratchpad_setup(self, tmp_path, monkeypatch):
        """Set up scratchpad root and project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        return scratchpad_root, project_dir

    def test_list_empty_shows_no_narratives(self, runner, scratchpad_setup):
        """Empty scratchpad shows 'No narratives found'."""
        scratchpad_root, project_dir = scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 1
        assert "No narratives found" in result.output

    def test_list_shows_scratchpad_narratives(self, runner, scratchpad_setup):
        """List shows narratives from scratchpad."""
        scratchpad_root, project_dir = scratchpad_setup

        # Create a narrative
        runner.invoke(
            cli,
            ["narrative", "create", "test_feature", "--project-dir", str(project_dir)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        assert "test_feature" in result.output
        assert "[DRAFTING]" in result.output

    def test_list_multiple_narratives_newest_first(self, runner, scratchpad_setup):
        """Multiple narratives listed newest first."""
        scratchpad_root, project_dir = scratchpad_setup

        # Create narratives with specific order
        runner.invoke(
            cli,
            ["narrative", "create", "first", "--project-dir", str(project_dir)]
        )
        runner.invoke(
            cli,
            ["narrative", "create", "second", "--project-dir", str(project_dir)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) >= 2
        # Newest first
        assert "second" in lines[0]
        assert "first" in lines[1]

    def test_list_does_not_show_docs_narratives_path(self, runner, scratchpad_setup):
        """List output does not show docs/narratives/ paths."""
        scratchpad_root, project_dir = scratchpad_setup

        runner.invoke(
            cli,
            ["narrative", "create", "my_feature", "--project-dir", str(project_dir)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        # Should NOT show old-style paths
        assert "docs/narratives/" not in result.output


class TestNarrativeCreateTaskContext:
    """Tests for 've narrative create' in task context."""

    @pytest.fixture
    def task_scratchpad_setup(self, tmp_path, monkeypatch):
        """Set up scratchpad root and task directory.

        Returns:
            tuple: (scratchpad_root, task_dir, task_name)
        """
        # Create a task directory with .ve-task.yaml
        task_dir = tmp_path / "my-migration-task"
        task_dir.mkdir()

        # Create minimal .ve-task.yaml
        (task_dir / ".ve-task.yaml").write_text(
            "external_artifact_repo: acme/external\n"
            "projects:\n"
            "  - acme/project1\n"
        )

        # Create external repo structure (needed for legacy mode, but not for scratchpad)
        external_repo = task_dir / "external"
        external_repo.mkdir()
        (external_repo / "docs" / "narratives").mkdir(parents=True)

        # Create scratchpad root
        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        return scratchpad_root, task_dir, "my-migration-task"

    def test_create_in_task_context_uses_scratchpad(self, runner, task_scratchpad_setup):
        """In task context, narrative create uses scratchpad with task: prefix."""
        scratchpad_root, task_dir, task_name = task_scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify narrative was created in scratchpad with task: prefix
        expected_path = scratchpad_root / f"task:{task_name}" / "narratives" / "my_narrative" / "OVERVIEW.md"
        assert expected_path.exists(), f"Expected {expected_path} to exist"

    def test_create_in_task_context_output_shows_path(self, runner, task_scratchpad_setup):
        """In task context, output shows scratchpad path."""
        scratchpad_root, task_dir, task_name = task_scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "my_narrative" in result.output


class TestNarrativeListTaskContext:
    """Tests for 've narrative list' in task context."""

    @pytest.fixture
    def task_scratchpad_setup(self, tmp_path, monkeypatch):
        """Set up scratchpad root and task directory."""
        task_dir = tmp_path / "my-migration-task"
        task_dir.mkdir()

        (task_dir / ".ve-task.yaml").write_text(
            "external_artifact_repo: acme/external\n"
            "projects:\n"
            "  - acme/project1\n"
        )

        external_repo = task_dir / "external"
        external_repo.mkdir()
        (external_repo / "docs" / "narratives").mkdir(parents=True)

        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        return scratchpad_root, task_dir, "my-migration-task"

    def test_list_in_task_context_shows_scratchpad_narratives(self, runner, task_scratchpad_setup):
        """In task context, list shows narratives from task scratchpad."""
        scratchpad_root, task_dir, task_name = task_scratchpad_setup

        # Create a narrative in task context
        runner.invoke(
            cli,
            ["narrative", "create", "task_feature", "--project-dir", str(task_dir)]
        )

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "task_feature" in result.output

    def test_list_empty_task_context_shows_no_narratives(self, runner, task_scratchpad_setup):
        """Empty task scratchpad shows 'No narratives found'."""
        scratchpad_root, task_dir, task_name = task_scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No narratives found" in result.output


class TestNarrativeCompactScratchpad:
    """Tests for 've narrative compact' with scratchpad storage."""

    @pytest.fixture
    def scratchpad_with_chunks(self, tmp_path, monkeypatch):
        """Set up scratchpad with some chunks to consolidate."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        # Create some chunks using ScratchpadChunks directly
        from scratchpad import ScratchpadChunks
        scratchpad = Scratchpad(scratchpad_root=scratchpad_root)
        context_path = scratchpad.resolve_context(project_path=project_dir)
        chunks_manager = ScratchpadChunks(scratchpad, context_path)

        chunks_manager.create_chunk("chunk-a")
        chunks_manager.create_chunk("chunk-b")
        chunks_manager.create_chunk("chunk-c")

        return scratchpad_root, project_dir

    def test_compact_creates_narrative(self, runner, scratchpad_with_chunks):
        """Compact creates a narrative in scratchpad."""
        scratchpad_root, project_dir = scratchpad_with_chunks

        result = runner.invoke(
            cli,
            [
                "narrative", "compact",
                "chunk-a", "chunk-b",
                "--name", "my-consolidated",
                "--project-dir", str(project_dir)
            ]
        )

        assert result.exit_code == 0
        assert "my-consolidated" in result.output

        # Verify narrative was created
        expected_path = scratchpad_root / "my-project" / "narratives" / "my-consolidated" / "OVERVIEW.md"
        assert expected_path.exists()

    def test_compact_requires_minimum_two_chunks(self, runner, scratchpad_with_chunks):
        """Compact requires at least 2 chunks."""
        scratchpad_root, project_dir = scratchpad_with_chunks

        result = runner.invoke(
            cli,
            [
                "narrative", "compact",
                "chunk-a",
                "--name", "my-consolidated",
                "--project-dir", str(project_dir)
            ]
        )

        assert result.exit_code != 0
        assert "Need at least 2 chunks" in result.output

    def test_compact_fails_for_nonexistent_chunk(self, runner, scratchpad_with_chunks):
        """Compact fails if a chunk doesn't exist."""
        scratchpad_root, project_dir = scratchpad_with_chunks

        result = runner.invoke(
            cli,
            [
                "narrative", "compact",
                "chunk-a", "nonexistent",
                "--name", "my-consolidated",
                "--project-dir", str(project_dir)
            ]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_compact_lists_consolidated_chunks(self, runner, scratchpad_with_chunks):
        """Compact output lists the consolidated chunks."""
        scratchpad_root, project_dir = scratchpad_with_chunks

        result = runner.invoke(
            cli,
            [
                "narrative", "compact",
                "chunk-a", "chunk-b", "chunk-c",
                "--name", "my-consolidated",
                "--project-dir", str(project_dir)
            ]
        )

        assert result.exit_code == 0
        assert "chunk-a" in result.output
        assert "chunk-b" in result.output
        assert "chunk-c" in result.output
        assert "3 chunks" in result.output


class TestNarrativeStatusScratchpad:
    """Tests for 've narrative status' with scratchpad storage."""

    @pytest.fixture
    def scratchpad_with_narrative(self, tmp_path, monkeypatch):
        """Set up scratchpad with a narrative."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        # Create a narrative
        from scratchpad import ScratchpadNarratives
        scratchpad = Scratchpad(scratchpad_root=scratchpad_root)
        context_path = scratchpad.resolve_context(project_path=project_dir)
        narratives_manager = ScratchpadNarratives(scratchpad, context_path)
        narratives_manager.create_narrative("my-narrative")

        return scratchpad_root, project_dir

    def test_status_display_shows_current_status(self, runner, scratchpad_with_narrative):
        """Status command shows current status for scratchpad narrative."""
        scratchpad_root, project_dir = scratchpad_with_narrative

        result = runner.invoke(
            cli,
            ["narrative", "status", "my-narrative", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        assert "DRAFTING" in result.output

    def test_status_transition_works(self, runner, scratchpad_with_narrative):
        """Status command can transition scratchpad narrative status."""
        scratchpad_root, project_dir = scratchpad_with_narrative

        result = runner.invoke(
            cli,
            ["narrative", "status", "my-narrative", "ACTIVE", "--project-dir", str(project_dir)]
        )

        assert result.exit_code == 0
        assert "DRAFTING" in result.output
        assert "ACTIVE" in result.output

    def test_status_invalid_status_fails(self, runner, scratchpad_with_narrative):
        """Status command fails for invalid status value."""
        scratchpad_root, project_dir = scratchpad_with_narrative

        result = runner.invoke(
            cli,
            ["narrative", "status", "my-narrative", "INVALID", "--project-dir", str(project_dir)]
        )

        assert result.exit_code != 0
        assert "Invalid status" in result.output

    def test_status_nonexistent_narrative_fails(self, runner, scratchpad_with_narrative):
        """Status command fails for nonexistent narrative."""
        scratchpad_root, project_dir = scratchpad_with_narrative

        result = runner.invoke(
            cli,
            ["narrative", "status", "nonexistent", "--project-dir", str(project_dir)]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestNarrativeUpdateRefsScratchpad:
    """Tests for 've narrative update-refs' with scratchpad storage."""

    @pytest.fixture
    def scratchpad_setup(self, tmp_path, monkeypatch):
        """Set up scratchpad root and project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        scratchpad_root = tmp_path / "scratchpad"
        scratchpad_root.mkdir()

        from scratchpad import Scratchpad
        monkeypatch.setattr(Scratchpad, "DEFAULT_ROOT", scratchpad_root)

        return scratchpad_root, project_dir

    def test_update_refs_not_applicable_for_scratchpad(self, runner, scratchpad_setup):
        """Update-refs command returns error for scratchpad narratives."""
        scratchpad_root, project_dir = scratchpad_setup

        result = runner.invoke(
            cli,
            ["narrative", "update-refs", "my-narrative", "--project-dir", str(project_dir)]
        )

        assert result.exit_code != 0
        assert "not applicable" in result.output.lower()
