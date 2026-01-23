"""Tests for the Project class."""

from chunks import Chunks
from project import Project, InitResult


class TestProjectClass:
    """Tests for the Project class."""

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

    def test_init_creates_command_files(self, temp_project):
        """init() creates command files (rendered from templates)."""
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
            assert cmd_path.is_file(), f"{cmd} should be a file"

    def test_init_command_files_have_content(self, temp_project):
        """init() command files have content rendered from templates."""
        project = Project(temp_project)
        project.init()
        commands_dir = temp_project / ".claude" / "commands"

        # Check that command files are not empty
        for cmd_path in commands_dir.iterdir():
            if cmd_path.is_file():
                content = cmd_path.read_text()
                assert len(content) > 0, f"{cmd_path.name} should have content"

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


class TestProjectInitChunks:
    """Tests for Project.init() chunks directory creation."""

    def test_init_creates_chunks_directory(self, temp_project):
        """init() creates docs/chunks/ directory."""
        project = Project(temp_project)
        project.init()
        chunks_dir = temp_project / "docs" / "chunks"
        assert chunks_dir.exists()
        assert chunks_dir.is_dir()

    def test_init_reports_chunks_created(self, temp_project):
        """init() reports docs/chunks/ in the created list."""
        project = Project(temp_project)
        result = project.init()
        assert "docs/chunks/" in result.created

    def test_init_skips_existing_chunks_directory(self, temp_project):
        """init() skips docs/chunks/ if it already exists (idempotent)."""
        project = Project(temp_project)

        # Create chunks dir before init
        chunks_dir = temp_project / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        result = project.init()

        # Should be skipped, not created
        assert "docs/chunks/" in result.skipped
        assert "docs/chunks/" not in result.created


class TestMagicMarkers:
    """Tests for CLAUDE.md magic marker functionality."""

    MARKER_START = "<!-- VE:MANAGED:START -->"
    MARKER_END = "<!-- VE:MANAGED:END -->"

    def test_new_claude_md_includes_markers(self, temp_project):
        """New CLAUDE.md files include magic markers."""
        project = Project(temp_project)
        project.init()

        claude_md = temp_project / "CLAUDE.md"
        content = claude_md.read_text()

        assert self.MARKER_START in content
        assert self.MARKER_END in content
        # START should come before END
        assert content.index(self.MARKER_START) < content.index(self.MARKER_END)

    def test_markers_preserve_content_before(self, temp_project):
        """Content before START marker is preserved on reinit."""
        project = Project(temp_project)
        project.init()

        claude_md = temp_project / "CLAUDE.md"
        original = claude_md.read_text()

        # Add custom content before the START marker
        custom_header = "# My Custom Project\n\nThis is my custom documentation.\n\n"
        start_idx = original.index(self.MARKER_START)
        modified = custom_header + original[start_idx:]
        claude_md.write_text(modified)

        # Reinit should preserve custom content
        project.init()
        result = claude_md.read_text()

        assert result.startswith(custom_header)
        assert self.MARKER_START in result
        assert self.MARKER_END in result

    def test_markers_preserve_content_after(self, temp_project):
        """Content after END marker is preserved on reinit."""
        project = Project(temp_project)
        project.init()

        claude_md = temp_project / "CLAUDE.md"
        original = claude_md.read_text()

        # Add custom content after the END marker
        custom_footer = "\n\n## My Custom Section\n\nMore custom content here.\n"
        modified = original + custom_footer
        claude_md.write_text(modified)

        # Reinit should preserve custom content
        project.init()
        result = claude_md.read_text()

        assert result.endswith(custom_footer)
        assert self.MARKER_START in result
        assert self.MARKER_END in result

    def test_markers_rewrite_content_inside(self, temp_project):
        """Content inside markers is rewritten with latest template."""
        project = Project(temp_project)
        project.init()

        claude_md = temp_project / "CLAUDE.md"
        original = claude_md.read_text()

        # Modify content inside markers
        start_idx = original.index(self.MARKER_START)
        end_idx = original.index(self.MARKER_END) + len(self.MARKER_END)
        modified = (
            original[:start_idx]
            + self.MARKER_START
            + "\n\nOLD MANAGED CONTENT THAT SHOULD BE REPLACED\n\n"
            + self.MARKER_END
            + original[end_idx:]
        )
        claude_md.write_text(modified)

        # Reinit should replace the managed content
        project.init()
        result = claude_md.read_text()

        assert "OLD MANAGED CONTENT THAT SHOULD BE REPLACED" not in result
        # The managed content should contain VE instructions
        assert "Vibe Engineering" in result

    def test_existing_without_markers_unchanged(self, temp_project):
        """Existing CLAUDE.md without markers is left unchanged (backward compat)."""
        project = Project(temp_project)

        # Create a CLAUDE.md without markers
        claude_md = temp_project / "CLAUDE.md"
        custom_content = "# Custom CLAUDE.md\n\nNo markers here.\n"
        claude_md.write_text(custom_content)

        result = project.init()

        # File should be unchanged
        assert claude_md.read_text() == custom_content
        assert "CLAUDE.md" in result.skipped

    def test_malformed_markers_missing_end_warns(self, temp_project):
        """Missing END marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create CLAUDE.md with only START marker
        claude_md = temp_project / "CLAUDE.md"
        malformed_content = f"# Header\n\n{self.MARKER_START}\n\nSome content\n"
        claude_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert claude_md.read_text() == malformed_content
        assert "CLAUDE.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_malformed_markers_missing_start_warns(self, temp_project):
        """Missing START marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create CLAUDE.md with only END marker
        claude_md = temp_project / "CLAUDE.md"
        malformed_content = f"# Header\n\nSome content\n\n{self.MARKER_END}\n"
        claude_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert claude_md.read_text() == malformed_content
        assert "CLAUDE.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_malformed_markers_wrong_order_warns(self, temp_project):
        """END before START marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create CLAUDE.md with markers in wrong order
        claude_md = temp_project / "CLAUDE.md"
        malformed_content = f"# Header\n\n{self.MARKER_END}\n\nContent\n\n{self.MARKER_START}\n"
        claude_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert claude_md.read_text() == malformed_content
        assert "CLAUDE.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_multiple_marker_pairs_warns(self, temp_project):
        """Multiple marker pairs results in warning and file unchanged."""
        project = Project(temp_project)

        # Create CLAUDE.md with multiple marker pairs
        claude_md = temp_project / "CLAUDE.md"
        malformed_content = (
            f"# Header\n\n"
            f"{self.MARKER_START}\nContent 1\n{self.MARKER_END}\n\n"
            f"{self.MARKER_START}\nContent 2\n{self.MARKER_END}\n"
        )
        claude_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert claude_md.read_text() == malformed_content
        assert "CLAUDE.md" in result.skipped
        # Should have a warning about multiple markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_reinit_reports_updated_not_skipped(self, temp_project):
        """When markers exist and content is rewritten, report as created not skipped."""
        project = Project(temp_project)
        project.init()

        # Second init should update the managed content
        result = project.init()

        # With markers, we should see it in created (updated), not skipped
        assert "CLAUDE.md" in result.created


class TestProjectInitIdempotency:
    """Tests for Project.init() idempotency.

    Note: Commands are always updated (overwrite=True) so they appear in
    created on every run. Trunk docs are never overwritten (overwrite=False)
    so they appear in skipped on subsequent runs. CLAUDE.md with markers
    has its managed content updated while preserving user content.
    """

    def test_init_preserves_user_content_skips_commands(self, temp_project):
        """Running init() twice: trunk skipped, commands and CLAUDE.md updated.

        Note: CLAUDE.md with markers is now updated (in created) on subsequent runs,
        preserving user content outside markers while refreshing managed content.
        """
        project = Project(temp_project)
        result1 = project.init()
        result2 = project.init()

        # First run creates everything
        assert len(result1.created) > 0

        # Second run: trunk, narratives, chunks are skipped (user content)
        assert any("docs/trunk/" in f for f in result2.skipped)
        assert "docs/narratives/" in result2.skipped
        assert "docs/chunks/" in result2.skipped

        # Commands and CLAUDE.md (with markers) are always updated
        assert any(".claude/commands/" in f for f in result2.created)
        # CLAUDE.md with markers is updated, not skipped
        assert "CLAUDE.md" in result2.created

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

    def test_init_overwrites_existing_commands(self, temp_project):
        """init() always overwrites existing command files (managed templates)."""
        project = Project(temp_project)

        # Create commands dir with existing file
        commands_dir = temp_project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        existing_cmd = commands_dir / "chunk-create.md"
        existing_cmd.write_text("Old content")

        result = project.init()

        # Command should be updated (in created), not skipped
        assert ".claude/commands/chunk-create.md" in result.created
        # Content should be updated from template
        assert existing_cmd.read_text() != "Old content"

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

    def test_init_result_tracks_skipped_and_created(self, temp_project):
        """init() result correctly tracks which files were skipped vs created."""
        project = Project(temp_project)

        # First run - all created, none skipped
        result1 = project.init()
        assert len(result1.skipped) == 0
        assert len(result1.created) > 0

        # Second run - user content skipped, commands created (updated)
        result2 = project.init()
        # Trunk + CLAUDE.md + narratives + chunks should be skipped
        assert len(result2.skipped) >= 6  # 4 trunk files + CLAUDE.md + narratives
        # Commands should be in created (updated)
        assert len(result2.created) > 0

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
