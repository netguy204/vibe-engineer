"""Tests for the 've init' CLI command."""
# Chunk: docs/chunks/project_init_command - CLI integration tests for 've init'
# Chunk: docs/chunks/plugin_init_slimdown - Init renders no skills or command symlinks

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
        assert (temp_project / "AGENTS.md").exists()
        # Backwards compatibility: CLAUDE.md symlink
        assert (temp_project / "CLAUDE.md").is_symlink()
        # Commands are distributed via the Claude Code plugin, not rendered
        assert not (temp_project / ".agents").exists()
        assert not (temp_project / ".claude").exists()

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
                assert pathlib.Path("AGENTS.md").exists()
                assert pathlib.Path("CLAUDE.md").is_symlink()
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

    # Chunk: docs/chunks/init_chunks_md_template - Adds CHUNKS.md to ve init trunk set
    def test_init_creates_chunks_md(self, runner, temp_project):
        """ve init creates docs/trunk/CHUNKS.md from template."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunks_md_path = temp_project / "docs" / "trunk" / "CHUNKS.md"
        assert chunks_md_path.exists()

        content = chunks_md_path.read_text()
        # Verify key phrases from each of the four principles
        assert "Code owns implementation" in content
        assert "Chunks exist only for intent-bearing work" in content
        assert "present tense" in content
        assert "Status answers a single question" in content

    # Subsystem: docs/subsystems/friction_tracking - Friction log management
    def test_init_creates_friction_log(self, runner, temp_project):
        """ve init creates docs/trunk/FRICTION.md from template."""
        result = runner.invoke(
            cli,
            ["init", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        friction_path = temp_project / "docs" / "trunk" / "FRICTION.md"
        assert friction_path.exists()

        content = friction_path.read_text()
        # Verify expected structure
        assert "themes: []" in content
        assert "proposed_chunks: []" in content
        assert "# Friction Log" in content
        assert "GUIDANCE FOR AGENTS" in content
        assert "## Entries" in content


# Chunk: docs/chunks/plugin_legacy_migration - Legacy-layout migration on re-init
AUTO_GENERATED_HEADER = """<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

Run `ve init` to regenerate.
-->
"""

LEGACY_SKILLS = ["chunk-create", "chunk-plan", "chunk-implement"]


def make_legacy_layout(project_dir: pathlib.Path) -> None:
    """Build a legacy render-channel layout in project_dir.

    Reproduces what pre-plugin `ve init` left behind:
    - .agents/skills/<name>/SKILL.md files with the AUTO-GENERATED header
    - .claude/commands/<name>.md relative symlinks into .agents/skills/
    - AGENTS.md with a marker-managed block carrying old command docs
    - CLAUDE.md symlink to AGENTS.md
    """
    skills_dir = project_dir / ".agents" / "skills"
    commands_dir = project_dir / ".claude" / "commands"
    skills_dir.mkdir(parents=True)
    commands_dir.mkdir(parents=True)

    for name in LEGACY_SKILLS:
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n{AUTO_GENERATED_HEADER}\n## Instructions\n"
        )
        (commands_dir / f"{name}.md").symlink_to(
            pathlib.Path("..") / ".." / ".agents" / "skills" / name / "SKILL.md"
        )

    agents_md = (
        "# My project notes\n\n"
        "<!-- VE:MANAGED:START -->\n"
        "OLD COMMAND DOCS: run /chunk-create from .claude/commands\n"
        "<!-- VE:MANAGED:END -->\n\n"
        "User content after the managed block.\n"
    )
    (project_dir / "AGENTS.md").write_text(agents_md)
    (project_dir / "CLAUDE.md").symlink_to("AGENTS.md")


class TestLegacyMigration:
    """ve init migrates projects off the legacy rendered layout."""

    def test_removes_ve_generated_skills_and_symlinks(self, runner, temp_project):
        make_legacy_layout(temp_project)

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0

        # Legacy content is gone, empty dirs pruned
        assert not (temp_project / ".agents").exists()
        assert not (temp_project / ".claude").exists()

    def test_reports_removed_paths(self, runner, temp_project):
        make_legacy_layout(temp_project)

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "Removed .claude/commands/chunk-create.md" in result.output
        assert "Removed .agents/skills/chunk-create/SKILL.md" in result.output

    def test_prints_plugin_install_pointer(self, runner, temp_project):
        make_legacy_layout(temp_project)

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "/plugin marketplace add netguy204/vibe-engineer" in result.output
        assert "/plugin install vibe-engineer" in result.output

    def test_rewrites_managed_block_to_slimmed_form(self, runner, temp_project):
        make_legacy_layout(temp_project)

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0

        content = (temp_project / "AGENTS.md").read_text()
        # Old managed content replaced by the slimmed block
        assert "OLD COMMAND DOCS" not in content
        assert "Claude Code plugin" in content
        # User content outside the markers preserved
        assert "# My project notes" in content
        assert "User content after the managed block." in content

    def test_preserves_user_authored_command_file_with_warning(
        self, runner, temp_project
    ):
        make_legacy_layout(temp_project)
        custom = temp_project / ".claude" / "commands" / "custom.md"
        custom.write_text("# My custom command\nDo my thing.\n")

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0

        # User file survives; its parent dirs are therefore not pruned
        assert custom.exists()
        assert "custom.md" in result.output
        assert "Warning" in result.output
        # ve-generated content is still removed
        assert not (temp_project / ".agents").exists()

    def test_preserves_user_authored_skill_with_warning(self, runner, temp_project):
        make_legacy_layout(temp_project)
        user_skill = temp_project / ".agents" / "skills" / "my-skill"
        user_skill.mkdir()
        (user_skill / "SKILL.md").write_text("---\nname: my-skill\n---\nMine.\n")

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0

        assert (user_skill / "SKILL.md").exists()
        assert "my-skill" in result.output
        assert "Warning" in result.output
        # ve-generated skills are still removed
        assert not (temp_project / ".agents" / "skills" / "chunk-create").exists()
        # .claude symlinks (all ve-generated) are removed and pruned
        assert not (temp_project / ".claude").exists()

    def test_preserves_foreign_symlink_with_warning(self, runner, temp_project):
        make_legacy_layout(temp_project)
        target = temp_project / "somewhere-else.md"
        target.write_text("# Not a ve file\n")
        foreign = temp_project / ".claude" / "commands" / "foreign.md"
        foreign.symlink_to(pathlib.Path("..") / ".." / "somewhere-else.md")

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0

        assert foreign.is_symlink()
        assert "foreign.md" in result.output
        assert "Warning" in result.output

    def test_removes_broken_symlink_into_agents_skills(self, runner, temp_project):
        make_legacy_layout(temp_project)
        # A symlink whose .agents/skills target is already gone
        broken = temp_project / ".claude" / "commands" / "chunk-review.md"
        broken.symlink_to(
            pathlib.Path("..") / ".." / ".agents" / "skills" / "chunk-review" / "SKILL.md"
        )

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert not broken.exists() and not broken.is_symlink()

    def test_removes_ve_generated_regular_command_file(self, runner, temp_project):
        """Windows-era legacy installs copied command files instead of symlinking."""
        make_legacy_layout(temp_project)
        copied = temp_project / ".claude" / "commands" / "chunk-copy.md"
        copied.write_text(f"---\nname: chunk-copy\n---\n{AUTO_GENERATED_HEADER}\nBody.\n")

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert not copied.exists()

    def test_second_run_is_noop(self, runner, temp_project):
        make_legacy_layout(temp_project)

        first = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert first.exit_code == 0
        assert "Removed" in first.output

        second = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert second.exit_code == 0
        assert "Removed" not in second.output
        assert "/plugin install" not in second.output
        assert "Skipped" in second.output

    def test_fresh_project_has_no_migration_output(self, runner, temp_project):
        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "Removed" not in result.output
        assert "/plugin install" not in result.output


class TestLegacyMigrationProjectLevel:
    """Project.init() level assertions for the migration result channels."""

    def test_init_result_removed_channel(self, temp_project):
        from project import Project

        make_legacy_layout(temp_project)
        result = Project(temp_project).init()

        assert ".claude/commands/chunk-create.md" in result.removed
        assert ".agents/skills/chunk-create/SKILL.md" in result.removed
        # Warnings channel untouched by a clean migration
        assert not any("custom" in w for w in result.warnings)

    def test_init_result_removed_empty_on_second_run(self, temp_project):
        from project import Project

        make_legacy_layout(temp_project)
        Project(temp_project).init()
        result = Project(temp_project).init()

        assert result.removed == []
        assert result.warnings == []

    def test_user_only_layout_produces_no_warnings(self, runner, temp_project):
        """A project whose .claude/commands holds only user files is left in peace.

        No ve-generated content means no migration is happening, so ve init
        has no business warning about the user's own files — on this run or
        any later one.
        """
        commands_dir = temp_project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "mine.md").write_text("# My own command\n")

        result = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert result.exit_code == 0
        assert "Removed" not in result.output
        assert "mine.md" not in result.output
        assert (commands_dir / "mine.md").exists()

    def test_second_run_does_not_rewarn_about_preserved_files(
        self, runner, temp_project
    ):
        make_legacy_layout(temp_project)
        custom = temp_project / ".claude" / "commands" / "custom.md"
        custom.write_text("# My custom command\n")

        first = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert "custom.md" in first.output

        second = runner.invoke(cli, ["init", "--project-dir", str(temp_project)])
        assert second.exit_code == 0
        assert "custom.md" not in second.output
        assert custom.exists()
