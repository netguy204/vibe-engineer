"""Tests for the 've init' CLI command."""

import pathlib
import tempfile

from ve import cli


class TestInitCommand:
    """Tests for 've init' CLI command."""

    def test_init_command_exists(self, runner):
        """Verify the init command is registered."""
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output

    def test_init_command_creates_files(self, runner, temp_project):
        """ve init creates expected files."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output

        # Verify files exist
        assert (temp_project / "docs" / "trunk" / "GOAL.md").exists()
        assert (temp_project / ".claude" / "commands" / "chunk-create.md").exists()
        assert (temp_project / "CLAUDE.md").exists()

    def test_init_command_reports_created_files(self, runner, temp_project):
        """ve init reports each created file."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/trunk/GOAL.md" in result.output or "Created" in result.output

    def test_init_command_idempotent(self, runner, temp_project):
        """ve init is idempotent - second run skips existing files."""
        # First run
        result1 = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Second run
        result2 = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0
        assert "Skipped" in result2.output
        assert "9" in result2.output  # 9 files skipped

    def test_init_command_default_project_dir(self, runner):
        """ve init uses current directory by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use isolated filesystem to set cwd
            with runner.isolated_filesystem(temp_dir=tmpdir):
                result = runner.invoke(cli, ["init"])
                assert result.exit_code == 0
                assert pathlib.Path("CLAUDE.md").exists()
                assert pathlib.Path("docs/trunk/GOAL.md").exists()
