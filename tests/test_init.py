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
        assert "Created" in result1.output

        # Second run
        result2 = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0
        assert "Skipped" in result2.output
        assert "existing" in result2.output.lower()

    def test_init_creates_narratives_directory(self, runner, temp_project):
        """ve init creates docs/narratives/ directory."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert (temp_project / "docs" / "narratives").exists()
        assert (temp_project / "docs" / "narratives").is_dir()

    def test_init_narratives_idempotent(self, runner, temp_project):
        """ve init skips narratives directory if it already exists."""
        # Create narratives dir before init
        (temp_project / "docs" / "narratives").mkdir(parents=True)

        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert (temp_project / "docs" / "narratives").exists()

    def test_init_command_default_project_dir(self, runner):
        """ve init uses current directory by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use isolated filesystem to set cwd
            with runner.isolated_filesystem(temp_dir=tmpdir):
                result = runner.invoke(cli, ["init"])
                assert result.exit_code == 0
                assert pathlib.Path("CLAUDE.md").exists()
                assert pathlib.Path("docs/trunk/GOAL.md").exists()

    def test_init_creates_chunks_directory(self, runner, temp_project):
        """ve init creates docs/chunks/ directory."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert (temp_project / "docs" / "chunks").exists()
        assert (temp_project / "docs" / "chunks").is_dir()

    def test_init_chunks_in_created_output(self, runner, temp_project):
        """ve init includes docs/chunks/ in its Created output."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/" in result.output

    def test_init_chunks_idempotent(self, runner, temp_project):
        """ve init skips chunks directory if it already exists."""
        # Create chunks dir before init
        (temp_project / "docs" / "chunks").mkdir(parents=True)

        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert (temp_project / "docs" / "chunks").exists()

    def test_init_creates_gitignore_with_artifact_cache(self, runner, temp_project):
        """ve init creates .gitignore with .artifact-order.json entry."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        gitignore = temp_project / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".artifact-order.json" in content

    def test_init_appends_to_existing_gitignore(self, runner, temp_project):
        """ve init appends to existing .gitignore without duplicating."""
        # Create existing .gitignore with some content
        gitignore = temp_project / ".gitignore"
        gitignore.write_text("node_modules/\n.env\n")

        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        content = gitignore.read_text()
        # Original content preserved
        assert "node_modules/" in content
        assert ".env" in content
        # New entry added
        assert ".artifact-order.json" in content

    def test_init_gitignore_idempotent(self, runner, temp_project):
        """ve init doesn't duplicate .artifact-order.json entry."""
        # Create .gitignore with the entry already present
        gitignore = temp_project / ".gitignore"
        gitignore.write_text(".artifact-order.json\n")

        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        content = gitignore.read_text()
        # Entry should appear exactly once
        assert content.count(".artifact-order.json") == 1
