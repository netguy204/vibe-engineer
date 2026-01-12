"""Tests for friction CLI commands."""
# Chunk: docs/chunks/friction_template_and_cli - Friction CLI tests

import pytest
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def initialized_project(temp_project, runner):
    """Create a project with friction log initialized."""
    result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
    assert result.exit_code == 0
    return temp_project


class TestFrictionLogCommand:
    """Tests for 've friction log' command."""

    def test_friction_log_command_exists(self, runner):
        """Help text available for friction log command."""
        result = runner.invoke(cli, ["friction", "log", "--help"])
        assert result.exit_code == 0
        assert "Log a new friction entry" in result.output

    def test_friction_log_creates_entry(self, runner, initialized_project):
        """Entry appears in file after logging."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Test friction",
                "--description", "This is a test friction",
                "--impact", "high",
                "--theme", "test-theme",
            ],
            input="Test Theme Friction\n"  # Answer for new theme name prompt
        )
        assert result.exit_code == 0
        assert "Created friction entry: F001" in result.output

        # Verify entry exists in file
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "F001" in content
        assert "Test friction" in content

    def test_friction_log_increments_id(self, runner, initialized_project):
        """Sequential ID assignment works correctly."""
        # Create first entry
        result1 = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "First entry",
                "--description", "First description",
                "--impact", "low",
                "--theme", "test-theme",
            ],
            input="Test Theme\n"
        )
        assert "Created friction entry: F001" in result1.output

        # Create second entry
        result2 = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Second entry",
                "--description", "Second description",
                "--impact", "medium",
                "--theme", "test-theme",
            ],
        )
        assert result2.exit_code == 0
        assert "Created friction entry: F002" in result2.output

    def test_friction_log_new_theme(self, runner, initialized_project):
        """New theme added to frontmatter when using new theme ID."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "New theme entry",
                "--description", "Description",
                "--impact", "medium",
                "--theme", "new",
            ],
            input="brand-new\nBrand New Friction\n"  # theme ID, then theme name
        )
        assert result.exit_code == 0

        # Verify theme was added
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "brand-new" in content
        assert "Brand New Friction" in content

    def test_friction_log_existing_theme(self, runner, initialized_project):
        """No frontmatter change for existing theme."""
        # First create an entry with a theme
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "First",
                "--description", "First",
                "--impact", "low",
                "--theme", "existing",
            ],
            input="Existing Theme\n"
        )

        # Read frontmatter before second entry
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content_before = friction_path.read_text()

        # Add second entry with same theme
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Second",
                "--description", "Second",
                "--impact", "low",
                "--theme", "existing",
            ],
        )
        assert result.exit_code == 0

        # Theme should appear exactly once
        content_after = friction_path.read_text()
        assert content_after.count("id: existing") == 1

    def test_friction_log_missing_friction_file(self, runner, temp_project):
        """Error message when friction log doesn't exist."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(temp_project),
                "--title", "Test",
                "--description", "Test",
                "--impact", "low",
                "--theme", "test",
            ],
            input="Test\n"
        )
        assert result.exit_code == 1
        assert "does not exist" in result.output


class TestFrictionListCommand:
    """Tests for 've friction list' command."""

    def test_friction_list_command_exists(self, runner):
        """Help text available for friction list command."""
        result = runner.invoke(cli, ["friction", "list", "--help"])
        assert result.exit_code == 0
        assert "List friction entries" in result.output

    def test_friction_list_shows_all_entries(self, runner, initialized_project):
        """Default lists all entries."""
        # Create some entries
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "First entry",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "test",
            ],
            input="Test Theme\n"
        )
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Second entry",
                "--description", "Desc",
                "--impact", "high",
                "--theme", "test",
            ],
        )

        # List all
        result = runner.invoke(
            cli,
            ["friction", "list", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "F001" in result.output
        assert "F002" in result.output
        assert "First entry" in result.output
        assert "Second entry" in result.output

    def test_friction_list_open_filter(self, runner, initialized_project):
        """--open shows only OPEN entries."""
        # Create an entry
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Open entry",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "test",
            ],
            input="Test Theme\n"
        )

        result = runner.invoke(
            cli,
            ["friction", "list", "--open", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "F001" in result.output
        assert "[OPEN]" in result.output

    def test_friction_list_tags_filter(self, runner, initialized_project):
        """--tags filters by theme."""
        # Create entries with different themes
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Alpha entry",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "alpha",
            ],
            input="Alpha Theme\n"
        )
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Beta entry",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "beta",
            ],
            input="Beta Theme\n"
        )

        result = runner.invoke(
            cli,
            ["friction", "list", "--tags", "alpha", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "Alpha entry" in result.output
        assert "Beta entry" not in result.output

    def test_friction_list_empty(self, runner, initialized_project):
        """'No friction entries found' for empty log."""
        result = runner.invoke(
            cli,
            ["friction", "list", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "No friction entries found" in result.output


class TestFrictionAnalyzeCommand:
    """Tests for 've friction analyze' command."""

    def test_friction_analyze_command_exists(self, runner):
        """Help text available for friction analyze command."""
        result = runner.invoke(cli, ["friction", "analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze friction patterns" in result.output

    def test_friction_analyze_groups_by_theme(self, runner, initialized_project):
        """Entries grouped correctly by theme."""
        # Create entries in different themes
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Code ref 1",
                "--description", "Desc",
                "--impact", "high",
                "--theme", "code-refs",
            ],
            input="Code Reference Friction\n"
        )
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Template 1",
                "--description", "Desc",
                "--impact", "medium",
                "--theme", "templates",
            ],
            input="Template Friction\n"
        )
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Code ref 2",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "code-refs",
            ],
        )

        result = runner.invoke(
            cli,
            ["friction", "analyze", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "code-refs (2 entries)" in result.output
        assert "templates (1 entries)" in result.output

    def test_friction_analyze_highlights_clusters(self, runner, initialized_project):
        """3+ entries in theme get warning indicator."""
        # Create 3 entries in same theme
        for i in range(3):
            runner.invoke(
                cli,
                [
                    "friction", "log",
                    "--project-dir", str(initialized_project),
                    "--title", f"Entry {i+1}",
                    "--description", "Desc",
                    "--impact", "low",
                    "--theme", "clustered",
                ],
                input="Clustered Friction\n" if i == 0 else ""
            )

        result = runner.invoke(
            cli,
            ["friction", "analyze", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "⚠️ Pattern Detected" in result.output
        assert "Consider creating a chunk or investigation" in result.output

    def test_friction_analyze_tags_filter(self, runner, initialized_project):
        """--tags filters analysis."""
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Alpha",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "alpha",
            ],
            input="Alpha Theme\n"
        )
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Beta",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "beta",
            ],
            input="Beta Theme\n"
        )

        result = runner.invoke(
            cli,
            ["friction", "analyze", "--tags", "alpha", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" not in result.output

    def test_friction_analyze_empty(self, runner, initialized_project):
        """'No friction entries found' for empty log."""
        result = runner.invoke(
            cli,
            ["friction", "analyze", "--project-dir", str(initialized_project)]
        )
        assert result.exit_code == 0
        assert "No friction entries found" in result.output
