"""Tests for the 've narrative create' CLI command."""

from ve import cli


# Chunk: docs/chunks/0044-remove_sequence_prefix - Updated for short_name only format
class TestNarrativeCreateCommand:
    """Tests for the 've narrative create' command."""

    def test_create_command_exists(self, runner):
        """Verify the create command is registered."""
        result = runner.invoke(cli, ["narrative", "create", "--help"])
        assert result.exit_code == 0
        assert "Create a new narrative" in result.output

    def test_create_accepts_short_name(self, runner, temp_project):
        """Command accepts short_name argument."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"


class TestNarrativeShortNameValidation:
    """Tests for short_name validation in narrative create."""

    def test_rejects_spaces(self, runner, temp_project):
        """short_name with spaces is rejected."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "my narrative", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "invalid characters" in result.output.lower()

    def test_rejects_invalid_characters(self, runner, temp_project):
        """short_name with invalid characters is rejected."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "my@narrative!", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "character" in result.output.lower()

    def test_rejects_length_32_or_more(self, runner, temp_project):
        """short_name with 32+ characters is rejected."""
        long_name = "a" * 32
        result = runner.invoke(
            cli,
            ["narrative", "create", long_name, "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "32" in result.output or "length" in result.output.lower()

    def test_accepts_valid_short_name(self, runner, temp_project):
        """Valid short_name with alphanumeric, underscore, hyphen is accepted."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative-v2", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"

    def test_collects_all_errors(self, runner, temp_project):
        """Multiple validation errors are collected and shown together."""
        # 33 chars with a space and invalid char
        bad_name = "a" * 30 + " @!"
        result = runner.invoke(
            cli,
            ["narrative", "create", bad_name, "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should mention multiple issues
        output_lower = result.output.lower()
        assert "invalid characters" in output_lower
        assert "32" in result.output or "less than" in output_lower


class TestNarrativeLowercaseNormalization:
    """Tests for lowercase normalization of inputs."""

    def test_short_name_normalized_to_lowercase(self, runner, temp_project):
        """short_name is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "My_Narrative", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"
        # Check the created directory uses lowercase
        narratives_dir = temp_project / "docs" / "narratives"
        created_dirs = list(narratives_dir.iterdir())
        assert len(created_dirs) == 1
        assert "my_narrative" in created_dirs[0].name
        assert "My_Narrative" not in created_dirs[0].name


class TestNarrativePathFormat:
    """Tests for narrative path format."""

    def test_path_format(self, runner, temp_project):
        """Path format is {short_name}."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        narratives_dir = temp_project / "docs" / "narratives"
        created_dirs = list(narratives_dir.iterdir())
        assert len(created_dirs) == 1
        assert created_dirs[0].name == "feature"

    def test_multiple_narratives_created(self, runner, temp_project):
        """Multiple narratives can be created."""
        runner.invoke(
            cli,
            ["narrative", "create", "first", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["narrative", "create", "second", "--project-dir", str(temp_project)]
        )

        narratives_dir = temp_project / "docs" / "narratives"
        created_dirs = sorted(narratives_dir.iterdir())
        assert len(created_dirs) == 2
        assert created_dirs[0].name == "first"
        assert created_dirs[1].name == "second"


class TestNarrativeSuccessOutput:
    """Tests for success output."""

    def test_prints_created_path(self, runner, temp_project):
        """Success message shows the created path."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "docs/narratives/feature" in result.output

    def test_creates_overview_file(self, runner, temp_project):
        """Creates OVERVIEW.md in narrative directory."""
        result = runner.invoke(
            cli,
            ["narrative", "create", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        overview_path = temp_project / "docs" / "narratives" / "feature" / "OVERVIEW.md"
        assert overview_path.exists()
