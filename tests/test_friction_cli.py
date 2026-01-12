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
                "--theme-name", "Test Theme Friction",
            ],
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
                "--theme-name", "Test Theme",
            ],
        )
        assert "Created friction entry: F001" in result1.output

        # Create second entry (theme already exists, no theme-name needed)
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

    def test_friction_log_new_theme_interactive(self, runner, initialized_project):
        """New theme added via interactive mode using 'new' keyword."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "New theme entry",
                "--description", "Description",
                "--impact", "medium",
            ],
            # Prompts: theme, theme ID, theme name
            input="new\nbrand-new\nBrand New Friction\n"
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
                "--theme-name", "Existing Theme",
            ],
        )

        # Read frontmatter before second entry
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content_before = friction_path.read_text()

        # Add second entry with same theme (no theme-name needed)
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
                "--theme-name", "Test Theme",
            ],
        )
        assert result.exit_code == 1
        assert "does not exist" in result.output


# Chunk: docs/chunks/friction_noninteractive - Non-interactive mode tests
class TestFrictionLogNonInteractive:
    """Tests for non-interactive friction log command."""

    def test_friction_log_noninteractive_new_theme(self, runner, initialized_project):
        """Non-interactive with new theme and theme-name succeeds without prompts."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Non-interactive entry",
                "--description", "Created without prompts",
                "--impact", "low",
                "--theme", "new-theme",
                "--theme-name", "New Theme Display Name",
            ],
        )
        assert result.exit_code == 0
        assert "Created friction entry: F001" in result.output

        # Verify entry and theme exist in file
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "F001" in content
        assert "Non-interactive entry" in content
        assert "new-theme" in content
        assert "New Theme Display Name" in content

    def test_friction_log_noninteractive_existing_theme(self, runner, initialized_project):
        """Non-interactive with existing theme succeeds without theme-name."""
        # First create an entry with a theme
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "First entry",
                "--description", "First",
                "--impact", "low",
                "--theme", "existing",
                "--theme-name", "Existing Theme",
            ],
        )

        # Second entry with same theme - no theme-name needed
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Second entry",
                "--description", "Second without theme-name",
                "--impact", "medium",
                "--theme", "existing",
            ],
        )
        assert result.exit_code == 0
        assert "Created friction entry: F002" in result.output

    def test_friction_log_noninteractive_missing_theme_name_fails(self, runner, initialized_project):
        """Non-interactive with new theme but no theme-name fails with clear error."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Entry",
                "--description", "Description",
                "--impact", "high",
                "--theme", "brand-new-theme",
                # Intentionally omitting --theme-name
            ],
        )
        assert result.exit_code == 1
        assert "brand-new-theme" in result.output
        assert "--theme-name" in result.output

    def test_friction_log_noninteractive_theme_new_keyword_fails(self, runner, initialized_project):
        """Non-interactive with --theme 'new' fails with clear error."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Entry",
                "--description", "Description",
                "--impact", "blocking",
                "--theme", "new",
            ],
        )
        assert result.exit_code == 1
        assert "'new'" in result.output
        assert "interactive" in result.output.lower()

    def test_friction_log_partial_options_prompts(self, runner, initialized_project):
        """Partial options provided triggers prompts for missing ones."""
        # Provide title and description, but not impact or theme
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Partial entry",
                "--description", "Has title and desc",
            ],
            input="low\ntest-theme\nTest Theme Name\n"  # Answers for impact, theme, theme-name
        )
        assert result.exit_code == 0
        assert "Created friction entry: F001" in result.output

    def test_friction_log_all_options_no_prompts(self, runner, initialized_project):
        """All options provided - no prompts at all, even without input."""
        # Create theme first
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Setup",
                "--description", "Setup",
                "--impact", "low",
                "--theme", "existing",
                "--theme-name", "Existing",
            ],
        )

        # This should succeed without any input (no prompts triggered)
        # If prompts were triggered, this would fail because there's no input
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Full options entry",
                "--description", "All options provided",
                "--impact", "high",
                "--theme", "existing",
            ],
            input=""  # Empty input - prompts would cause failure
        )
        assert result.exit_code == 0
        assert "Created friction entry: F002" in result.output


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
                "--theme-name", "Test Theme",
            ],
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
                "--theme-name", "Test Theme",
            ],
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
                "--theme-name", "Alpha Theme",
            ],
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
                "--theme-name", "Beta Theme",
            ],
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
                "--theme-name", "Code Reference Friction",
            ],
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
                "--theme-name", "Template Friction",
            ],
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
            args = [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", f"Entry {i+1}",
                "--description", "Desc",
                "--impact", "low",
                "--theme", "clustered",
            ]
            if i == 0:
                args.extend(["--theme-name", "Clustered Friction"])
            runner.invoke(cli, args)

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
                "--theme-name", "Alpha Theme",
            ],
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
                "--theme-name", "Beta Theme",
            ],
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


# Chunk: docs/chunks/friction_noninteractive - Non-interactive friction log tests
class TestFrictionLogNonInteractive:
    """Tests for non-interactive 've friction log' command usage."""

    def test_all_options_provided_succeeds_without_prompts(self, runner, initialized_project):
        """Invoke with all options - should succeed with exit code 0 without any input."""
        # First, create an existing theme using --theme-name for non-interactive creation
        setup_result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Setup entry",
                "--description", "Setup description",
                "--impact", "low",
                "--theme", "cli",
                "--theme-name", "CLI Friction",  # Required for new theme in non-interactive mode
            ],
        )
        assert setup_result.exit_code == 0, f"Setup failed: {setup_result.output}"

        # Now invoke fully non-interactively with existing theme (no --theme-name needed)
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Non-interactive entry",
                "--description", "This should work without prompts",
                "--impact", "medium",
                "--theme", "cli",
            ],
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created friction entry: F002" in result.output

    def test_new_theme_with_theme_name_succeeds_without_prompts(self, runner, initialized_project):
        """New theme with --theme-name succeeds non-interactively."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "New theme entry",
                "--description", "Testing new theme non-interactively",
                "--impact", "high",
                "--theme", "new-theme",
                "--theme-name", "New Theme Friction",
            ],
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created friction entry: F001" in result.output

        # Verify theme was added
        friction_path = initialized_project / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "new-theme" in content
        assert "New Theme Friction" in content

    def test_missing_title_fails_noninteractively(self, runner, initialized_project):
        """Missing --title fails with clear error in non-interactive mode."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                # --title missing
                "--description", "Some description",
                "--impact", "low",
                "--theme", "cli",
                "--theme-name", "CLI",
            ],
        )
        assert result.exit_code != 0
        assert "--title" in result.output or "title" in result.output.lower()

    def test_missing_description_fails_noninteractively(self, runner, initialized_project):
        """Missing --description fails with clear error in non-interactive mode."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Some title",
                # --description missing
                "--impact", "low",
                "--theme", "cli",
                "--theme-name", "CLI",
            ],
        )
        assert result.exit_code != 0
        assert "--description" in result.output or "description" in result.output.lower()

    def test_missing_impact_fails_noninteractively(self, runner, initialized_project):
        """Missing --impact fails with clear error in non-interactive mode."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Some title",
                "--description", "Some description",
                # --impact missing
                "--theme", "cli",
                "--theme-name", "CLI",
            ],
        )
        assert result.exit_code != 0
        assert "--impact" in result.output or "impact" in result.output.lower()

    def test_missing_theme_fails_noninteractively(self, runner, initialized_project):
        """Missing --theme fails with clear error in non-interactive mode."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Some title",
                "--description", "Some description",
                "--impact", "low",
                # --theme missing
            ],
        )
        assert result.exit_code != 0
        assert "--theme" in result.output or "theme" in result.output.lower()

    def test_new_theme_without_theme_name_fails_noninteractively(self, runner, initialized_project):
        """New theme without --theme-name fails in non-interactive mode."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "New theme entry",
                "--description", "Testing new theme",
                "--impact", "high",
                "--theme", "brand-new-theme",
                # --theme-name missing for new theme
            ],
        )
        assert result.exit_code != 0
        assert "--theme-name" in result.output or "new" in result.output.lower()

    def test_theme_new_without_options_fails_noninteractively(self, runner, initialized_project):
        """Using --theme 'new' fails in non-interactive mode (requires interactive prompts)."""
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "New theme entry",
                "--description", "Testing theme=new",
                "--impact", "high",
                "--theme", "new",  # 'new' requires interactive prompts for theme ID
            ],
        )
        assert result.exit_code != 0
        # Should fail because 'new' is a placeholder requiring interactive theme ID prompt

    def test_existing_theme_doesnt_require_theme_name(self, runner, initialized_project):
        """When --theme matches existing theme, --theme-name is not required."""
        # First create a theme with --theme-name
        runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "First",
                "--description", "First",
                "--impact", "low",
                "--theme", "existing-theme",
                "--theme-name", "Existing Theme",
            ],
        )

        # Now add another entry to the existing theme without --theme-name
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--project-dir", str(initialized_project),
                "--title", "Second",
                "--description", "Second",
                "--impact", "medium",
                "--theme", "existing-theme",
                # --theme-name NOT provided, but should work for existing theme
            ],
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created friction entry: F002" in result.output
