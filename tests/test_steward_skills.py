"""Tests for steward skill template rendering via 've init'."""
# Chunk: docs/chunks/leader_board_steward_skills - Steward skill rendering tests


from ve import cli


STEWARD_COMMANDS = [
    "steward-setup",
    "steward-watch",
    "steward-send",
    "steward-changelog",
]


class TestStewardSkillsRendered:
    """Verify that ve init renders all four steward skill templates."""

    def test_steward_commands_created(self, runner, temp_project):
        """ve init creates all steward command files."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)],
        )
        assert result.exit_code == 0

        for cmd_name in STEWARD_COMMANDS:
            cmd_file = temp_project / ".claude" / "commands" / f"{cmd_name}.md"
            assert cmd_file.exists(), f"{cmd_name}.md was not created by ve init"

    def test_steward_commands_contain_auto_generated_header(self, runner, temp_project):
        """Each steward command file contains the auto-generated header."""
        runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)],
        )

        for cmd_name in STEWARD_COMMANDS:
            cmd_file = temp_project / ".claude" / "commands" / f"{cmd_name}.md"
            content = cmd_file.read_text()
            assert "AUTO-GENERATED FILE" in content, (
                f"{cmd_name}.md missing auto-generated header"
            )
