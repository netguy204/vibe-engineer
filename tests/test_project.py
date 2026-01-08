"""Tests for the Project class."""

from chunks import Chunks
from constants import template_dir
from project import Project, InitResult


class TestProjectClass:
    """Tests for the Project class."""

    def test_project_dir_stored(self, temp_project):
        """Project stores project_dir correctly."""
        project = Project(temp_project)
        assert project.project_dir == temp_project

    def test_chunks_property_returns_chunks_instance(self, temp_project):
        """Project.chunks returns a Chunks instance."""
        project = Project(temp_project)
        assert isinstance(project.chunks, Chunks)
        assert project.chunks.project_dir == temp_project

    def test_chunks_property_is_lazy(self, temp_project):
        """Project.chunks is lazily instantiated."""
        project = Project(temp_project)
        assert project._chunks is None
        _ = project.chunks
        assert project._chunks is not None

    def test_chunks_property_returns_same_instance(self, temp_project):
        """Project.chunks returns the same instance on repeated calls."""
        project = Project(temp_project)
        chunks1 = project.chunks
        chunks2 = project.chunks
        assert chunks1 is chunks2


class TestProjectInit:
    """Tests for Project.init() method."""

    def test_init_returns_init_result(self, temp_project):
        """init() returns an InitResult instance."""
        project = Project(temp_project)
        result = project.init()
        assert isinstance(result, InitResult)

    def test_init_creates_trunk_directory(self, temp_project):
        """init() creates docs/trunk/ directory."""
        project = Project(temp_project)
        project.init()
        trunk_dir = temp_project / "docs" / "trunk"
        assert trunk_dir.exists()
        assert trunk_dir.is_dir()

    def test_init_creates_trunk_documents(self, temp_project):
        """init() creates all trunk documents."""
        project = Project(temp_project)
        project.init()
        trunk_dir = temp_project / "docs" / "trunk"
        expected_files = ["GOAL.md", "SPEC.md", "DECISIONS.md", "TESTING_PHILOSOPHY.md"]
        for filename in expected_files:
            assert (trunk_dir / filename).exists(), f"Missing {filename}"

    def test_init_creates_claude_commands_directory(self, temp_project):
        """init() creates .claude/commands/ directory."""
        project = Project(temp_project)
        project.init()
        commands_dir = temp_project / ".claude" / "commands"
        assert commands_dir.exists()
        assert commands_dir.is_dir()

    def test_init_creates_command_symlinks(self, temp_project):
        """init() creates symlinks for all command templates."""
        project = Project(temp_project)
        project.init()
        commands_dir = temp_project / ".claude" / "commands"
        expected_commands = [
            "chunk-create.md",
            "chunk-plan.md",
            "chunk-complete.md",
            "chunk-update-references.md",
            "chunks-resolve-references.md",
        ]
        for cmd in expected_commands:
            cmd_path = commands_dir / cmd
            assert cmd_path.exists(), f"Missing {cmd}"
            assert cmd_path.is_symlink(), f"{cmd} should be a symlink"

    def test_init_symlinks_point_to_templates(self, temp_project):
        """init() symlinks point to the correct template files."""
        project = Project(temp_project)
        project.init()
        commands_dir = temp_project / ".claude" / "commands"

        expected_target_dir = template_dir / "commands"

        for cmd_path in commands_dir.iterdir():
            if cmd_path.is_symlink():
                target = cmd_path.resolve()
                assert target.parent == expected_target_dir.resolve()
                assert target.name == cmd_path.name

    def test_init_creates_claude_md(self, temp_project):
        """init() creates CLAUDE.md at project root."""
        project = Project(temp_project)
        project.init()
        claude_md = temp_project / "CLAUDE.md"
        assert claude_md.exists()
        assert claude_md.is_file()

    def test_init_claude_md_has_content(self, temp_project):
        """init() creates CLAUDE.md with expected content."""
        project = Project(temp_project)
        project.init()
        claude_md = temp_project / "CLAUDE.md"
        content = claude_md.read_text()
        assert "Vibe Engineering" in content
        assert "docs/trunk/" in content
        assert "docs/chunks/" in content
        assert "/chunk-create" in content

    def test_init_reports_created_files(self, temp_project):
        """init() reports all created files in result."""
        project = Project(temp_project)
        result = project.init()
        # Verify items are created and key files are present
        assert len(result.created) > 0
        assert "CLAUDE.md" in result.created
        assert any("docs/trunk/" in f for f in result.created)
        assert any(".claude/commands/" in f for f in result.created)


class TestProjectInitIdempotency:
    """Tests for Project.init() idempotency."""

    def test_init_is_idempotent(self, temp_project):
        """Running init() twice doesn't fail - second run skips all items."""
        project = Project(temp_project)
        result1 = project.init()
        result2 = project.init()
        # First run creates items, second run skips them all
        assert len(result1.created) > 0
        assert len(result2.created) == 0
        assert len(result2.skipped) == len(result1.created)

    def test_init_skips_existing_trunk_files(self, temp_project):
        """init() skips existing trunk files without overwriting."""
        project = Project(temp_project)

        # Create trunk dir with custom GOAL.md
        trunk_dir = temp_project / "docs" / "trunk"
        trunk_dir.mkdir(parents=True)
        custom_content = "# Custom Goal\nThis is custom content."
        (trunk_dir / "GOAL.md").write_text(custom_content)

        project.init()

        # Custom content should be preserved
        assert (trunk_dir / "GOAL.md").read_text() == custom_content

    def test_init_skips_existing_symlinks(self, temp_project):
        """init() skips existing command symlinks."""
        project = Project(temp_project)

        # Create commands dir with existing symlink
        commands_dir = temp_project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        existing_symlink = commands_dir / "chunk-create.md"
        existing_symlink.symlink_to("/tmp/fake-target")

        result = project.init()

        # Should skip the existing symlink
        assert ".claude/commands/chunk-create.md" in result.skipped

    def test_init_skips_existing_claude_md(self, temp_project):
        """init() skips existing CLAUDE.md without overwriting."""
        project = Project(temp_project)

        # Create custom CLAUDE.md
        custom_content = "# Custom CLAUDE.md\nDo not overwrite."
        (temp_project / "CLAUDE.md").write_text(custom_content)

        result = project.init()

        # Custom content should be preserved
        assert (temp_project / "CLAUDE.md").read_text() == custom_content
        assert "CLAUDE.md" in result.skipped

    def test_init_result_tracks_skipped_files(self, temp_project):
        """init() result correctly tracks which files were skipped."""
        project = Project(temp_project)

        # First run - all created, none skipped
        result1 = project.init()
        assert len(result1.skipped) == 0
        assert len(result1.created) > 0

        # Second run - all skipped, none created
        result2 = project.init()
        assert len(result2.skipped) == len(result1.created)
        assert len(result2.created) == 0

    def test_init_restores_deleted_file(self, temp_project):
        """init() restores a deleted file on subsequent run."""
        project = Project(temp_project)

        # First run - initialize
        project.init()
        claude_md = temp_project / "CLAUDE.md"
        assert claude_md.exists()

        # Delete a file
        claude_md.unlink()
        assert not claude_md.exists()

        # Second run - should restore the deleted file
        result = project.init()
        assert claude_md.exists()
        assert "CLAUDE.md" in result.created
