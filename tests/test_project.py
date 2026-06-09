"""Tests for the Project class."""
# Chunk: docs/chunks/project_init_command - Tests for Project class, init(), and idempotency
# Chunk: docs/chunks/project_artifact_registry - Tests for unified artifact registry properties
# Chunk: docs/chunks/agentskills_migration - Updated for AGENTS.md and .agents/skills/ structure

from chunks import Chunks
from friction import Friction
from investigations import Investigations
from narratives import Narratives
from project import Project, InitResult, _is_ve_generated_file
from subsystems import Subsystems


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


# Chunk: docs/chunks/project_artifact_registry - Tests for new lazy-loaded manager properties
class TestProjectArtifactRegistry:
    """Tests for Project artifact registry properties."""

    # Narratives property tests
    def test_narratives_property_returns_narratives_instance(self, temp_project):
        """Project.narratives returns a Narratives instance."""
        project = Project(temp_project)
        assert isinstance(project.narratives, Narratives)

    def test_narratives_property_is_lazy(self, temp_project):
        """Project.narratives is lazily instantiated."""
        project = Project(temp_project)
        assert project._narratives is None
        _ = project.narratives
        assert project._narratives is not None

    def test_narratives_property_returns_same_instance(self, temp_project):
        """Project.narratives returns the same instance on repeated calls."""
        project = Project(temp_project)
        narratives1 = project.narratives
        narratives2 = project.narratives
        assert narratives1 is narratives2

    # Investigations property tests
    def test_investigations_property_returns_investigations_instance(self, temp_project):
        """Project.investigations returns an Investigations instance."""
        project = Project(temp_project)
        assert isinstance(project.investigations, Investigations)

    def test_investigations_property_is_lazy(self, temp_project):
        """Project.investigations is lazily instantiated."""
        project = Project(temp_project)
        assert project._investigations is None
        _ = project.investigations
        assert project._investigations is not None

    def test_investigations_property_returns_same_instance(self, temp_project):
        """Project.investigations returns the same instance on repeated calls."""
        project = Project(temp_project)
        investigations1 = project.investigations
        investigations2 = project.investigations
        assert investigations1 is investigations2

    # Subsystems property tests
    def test_subsystems_property_returns_subsystems_instance(self, temp_project):
        """Project.subsystems returns a Subsystems instance."""
        project = Project(temp_project)
        assert isinstance(project.subsystems, Subsystems)

    def test_subsystems_property_is_lazy(self, temp_project):
        """Project.subsystems is lazily instantiated."""
        project = Project(temp_project)
        assert project._subsystems is None
        _ = project.subsystems
        assert project._subsystems is not None

    def test_subsystems_property_returns_same_instance(self, temp_project):
        """Project.subsystems returns the same instance on repeated calls."""
        project = Project(temp_project)
        subsystems1 = project.subsystems
        subsystems2 = project.subsystems
        assert subsystems1 is subsystems2

    # Friction property tests
    def test_friction_property_returns_friction_instance(self, temp_project):
        """Project.friction returns a Friction instance."""
        project = Project(temp_project)
        assert isinstance(project.friction, Friction)

    def test_friction_property_is_lazy(self, temp_project):
        """Project.friction is lazily instantiated."""
        project = Project(temp_project)
        assert project._friction is None
        _ = project.friction
        assert project._friction is not None

    def test_friction_property_returns_same_instance(self, temp_project):
        """Project.friction returns the same instance on repeated calls."""
        project = Project(temp_project)
        friction1 = project.friction
        friction2 = project.friction
        assert friction1 is friction2


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

    # Chunk: docs/chunks/plugin_init_slimdown - Fresh init renders no skills or command symlinks
    def test_init_creates_no_agents_skills_directory(self, temp_project):
        """init() does not create a .agents/ directory (commands live in the plugin)."""
        project = Project(temp_project)
        project.init()
        assert not (temp_project / ".agents").exists()

    # Chunk: docs/chunks/plugin_init_slimdown - Fresh init renders no skills or command symlinks
    def test_init_creates_no_claude_commands_directory(self, temp_project):
        """init() does not create a .claude/commands/ directory (commands live in the plugin)."""
        project = Project(temp_project)
        project.init()
        assert not (temp_project / ".claude").exists()

    def test_init_creates_agents_md(self, temp_project):
        """init() creates AGENTS.md at project root."""
        project = Project(temp_project)
        project.init()
        agents_md = temp_project / "AGENTS.md"
        assert agents_md.exists()
        assert agents_md.is_file()

    def test_init_creates_claude_md_symlink(self, temp_project):
        """init() creates CLAUDE.md as symlink to AGENTS.md."""
        project = Project(temp_project)
        project.init()
        claude_md = temp_project / "CLAUDE.md"
        agents_md = temp_project / "AGENTS.md"
        assert claude_md.is_symlink()
        assert claude_md.resolve() == agents_md.resolve()

    def test_init_agents_md_has_content(self, temp_project):
        """init() creates AGENTS.md with expected content."""
        project = Project(temp_project)
        project.init()
        agents_md = temp_project / "AGENTS.md"
        content = agents_md.read_text()
        assert "Vibe Engineering" in content
        assert "docs/trunk/" in content
        assert "docs/chunks/" in content
        # Chunk: docs/chunks/plugin_init_slimdown - Commands are documented by the plugin, not AGENTS.md
        assert "/plugin install vibe-engineer" in content
        assert "## Available Commands" not in content

    def test_init_claude_md_symlink_has_same_content(self, temp_project):
        """CLAUDE.md symlink reads same content as AGENTS.md."""
        project = Project(temp_project)
        project.init()
        agents_content = (temp_project / "AGENTS.md").read_text()
        claude_content = (temp_project / "CLAUDE.md").read_text()
        assert agents_content == claude_content

    def test_init_reports_created_files(self, temp_project):
        """init() reports all created files in result."""
        project = Project(temp_project)
        result = project.init()
        # Verify items are created and key files are present
        assert len(result.created) > 0
        assert "AGENTS.md" in result.created
        assert any("docs/trunk/" in f for f in result.created)
        # Chunk: docs/chunks/plugin_init_slimdown - No rendered skills in init output
        assert not any(".agents/skills/" in f for f in result.created)
        assert not any(".claude/commands/" in f for f in result.created)


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


class TestProjectInitReviewers:
    """Tests for Project.init() baseline reviewer creation."""

    def test_init_creates_reviewers_directory(self, temp_project):
        """init() creates docs/reviewers/baseline/ directory."""
        project = Project(temp_project)
        project.init()
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        assert reviewers_dir.exists()
        assert reviewers_dir.is_dir()

    def test_init_creates_reviewer_files(self, temp_project):
        """init() creates all baseline reviewer files."""
        project = Project(temp_project)
        project.init()
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        expected_files = ["METADATA.yaml", "PROMPT.md"]
        for filename in expected_files:
            assert (reviewers_dir / filename).exists(), f"Missing {filename}"

    def test_init_reports_reviewer_files_created(self, temp_project):
        """init() reports reviewer files in the created list."""
        project = Project(temp_project)
        result = project.init()
        # Check that reviewer files are reported
        reviewer_files = [
            "docs/reviewers/baseline/METADATA.yaml",
            "docs/reviewers/baseline/PROMPT.md",
        ]
        for file in reviewer_files:
            assert file in result.created, f"Expected {file} in created list"

    def test_init_reviewer_metadata_has_content(self, temp_project):
        """init() creates METADATA.yaml with expected content."""
        project = Project(temp_project)
        project.init()
        metadata_path = temp_project / "docs" / "reviewers" / "baseline" / "METADATA.yaml"
        content = metadata_path.read_text()
        # Check for key YAML fields
        assert "name: baseline" in content
        assert "trust_level: observation" in content
        assert "loop_detection:" in content
        assert "created_at:" in content

    def test_init_reviewer_prompt_has_content(self, temp_project):
        """init() creates PROMPT.md with expected content."""
        project = Project(temp_project)
        project.init()
        prompt_path = temp_project / "docs" / "reviewers" / "baseline" / "PROMPT.md"
        content = prompt_path.read_text()
        # Check for key content
        assert "Baseline Reviewer Prompt" in content
        assert "APPROVE" in content
        assert "FEEDBACK" in content
        assert "ESCALATE" in content

    def test_init_skips_existing_reviewer_files(self, temp_project):
        """init() skips existing reviewer files (idempotent/preserves decision logs)."""
        project = Project(temp_project)

        # Create reviewer dir with custom METADATA.yaml before init
        reviewers_dir = temp_project / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        custom_content = "# Custom METADATA\nname: custom_baseline"
        (reviewers_dir / "METADATA.yaml").write_text(custom_content)

        result = project.init()

        # Custom content should be preserved (file skipped)
        assert (reviewers_dir / "METADATA.yaml").read_text() == custom_content
        assert "docs/reviewers/baseline/METADATA.yaml" in result.skipped
        # Other files should be created
        assert "docs/reviewers/baseline/PROMPT.md" in result.created


# Chunk: docs/chunks/claudemd_magic_markers - Test suite for marker detection, preservation, and edge cases
# Chunk: docs/chunks/agentskills_migration - Updated for AGENTS.md as canonical file
class TestMagicMarkers:
    """Tests for AGENTS.md magic marker functionality."""

    MARKER_START = "<!-- VE:MANAGED:START -->"
    MARKER_END = "<!-- VE:MANAGED:END -->"

    def test_new_agents_md_includes_markers(self, temp_project):
        """New AGENTS.md files include magic markers."""
        project = Project(temp_project)
        project.init()

        agents_md = temp_project / "AGENTS.md"
        content = agents_md.read_text()

        assert self.MARKER_START in content
        assert self.MARKER_END in content
        # START should come before END
        assert content.index(self.MARKER_START) < content.index(self.MARKER_END)

    def test_markers_preserve_content_before(self, temp_project):
        """Content before START marker is preserved on reinit."""
        project = Project(temp_project)
        project.init()

        agents_md = temp_project / "AGENTS.md"
        original = agents_md.read_text()

        # Add custom content before the START marker
        custom_header = "# My Custom Project\n\nThis is my custom documentation.\n\n"
        start_idx = original.index(self.MARKER_START)
        modified = custom_header + original[start_idx:]
        agents_md.write_text(modified)

        # Reinit should preserve custom content
        project.init()
        result = agents_md.read_text()

        assert result.startswith(custom_header)
        assert self.MARKER_START in result
        assert self.MARKER_END in result

    def test_markers_preserve_content_after(self, temp_project):
        """Content after END marker is preserved on reinit."""
        project = Project(temp_project)
        project.init()

        agents_md = temp_project / "AGENTS.md"
        original = agents_md.read_text()

        # Add custom content after the END marker
        custom_footer = "\n\n## My Custom Section\n\nMore custom content here.\n"
        modified = original + custom_footer
        agents_md.write_text(modified)

        # Reinit should preserve custom content
        project.init()
        result = agents_md.read_text()

        assert result.endswith(custom_footer)
        assert self.MARKER_START in result
        assert self.MARKER_END in result

    def test_markers_rewrite_content_inside(self, temp_project):
        """Content inside markers is rewritten with latest template."""
        project = Project(temp_project)
        project.init()

        agents_md = temp_project / "AGENTS.md"
        original = agents_md.read_text()

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
        agents_md.write_text(modified)

        # Reinit should replace the managed content
        project.init()
        result = agents_md.read_text()

        assert "OLD MANAGED CONTENT THAT SHOULD BE REPLACED" not in result
        # The managed content should contain VE instructions
        assert "Vibe Engineering" in result

    def test_existing_agents_md_without_markers_unchanged(self, temp_project):
        """Existing AGENTS.md without markers is left unchanged (backward compat)."""
        project = Project(temp_project)

        # Create an AGENTS.md without markers
        agents_md = temp_project / "AGENTS.md"
        custom_content = "# Custom AGENTS.md\n\nNo markers here.\n"
        agents_md.write_text(custom_content)

        result = project.init()

        # File should be unchanged
        assert agents_md.read_text() == custom_content
        assert "AGENTS.md" in result.skipped

    def test_pre_migration_claude_md_renamed_to_agents_md(self, temp_project):
        """Existing CLAUDE.md (regular file) is renamed to AGENTS.md on init."""
        project = Project(temp_project)

        # Create a CLAUDE.md with markers (simulating pre-migration state)
        claude_md = temp_project / "CLAUDE.md"
        content_with_markers = (
            "# My Project\n\n"
            + self.MARKER_START
            + "\nOld managed content\n"
            + self.MARKER_END
            + "\n\n## Custom Footer\n"
        )
        claude_md.write_text(content_with_markers)

        result = project.init()

        # CLAUDE.md should now be a symlink
        assert claude_md.is_symlink()
        # AGENTS.md should exist and have updated managed content
        agents_md = temp_project / "AGENTS.md"
        assert agents_md.exists()
        assert not agents_md.is_symlink()
        # Custom content outside markers should be preserved
        agents_content = agents_md.read_text()
        assert "# My Project" in agents_content
        assert "## Custom Footer" in agents_content

    def test_malformed_markers_missing_end_warns(self, temp_project):
        """Missing END marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create AGENTS.md with only START marker
        agents_md = temp_project / "AGENTS.md"
        malformed_content = f"# Header\n\n{self.MARKER_START}\n\nSome content\n"
        agents_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert agents_md.read_text() == malformed_content
        assert "AGENTS.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_malformed_markers_missing_start_warns(self, temp_project):
        """Missing START marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create AGENTS.md with only END marker
        agents_md = temp_project / "AGENTS.md"
        malformed_content = f"# Header\n\nSome content\n\n{self.MARKER_END}\n"
        agents_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert agents_md.read_text() == malformed_content
        assert "AGENTS.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_malformed_markers_wrong_order_warns(self, temp_project):
        """END before START marker results in warning and file unchanged."""
        project = Project(temp_project)

        # Create AGENTS.md with markers in wrong order
        agents_md = temp_project / "AGENTS.md"
        malformed_content = f"# Header\n\n{self.MARKER_END}\n\nContent\n\n{self.MARKER_START}\n"
        agents_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert agents_md.read_text() == malformed_content
        assert "AGENTS.md" in result.skipped
        # Should have a warning about malformed markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_multiple_marker_pairs_warns(self, temp_project):
        """Multiple marker pairs results in warning and file unchanged."""
        project = Project(temp_project)

        # Create AGENTS.md with multiple marker pairs
        agents_md = temp_project / "AGENTS.md"
        malformed_content = (
            f"# Header\n\n"
            f"{self.MARKER_START}\nContent 1\n{self.MARKER_END}\n\n"
            f"{self.MARKER_START}\nContent 2\n{self.MARKER_END}\n"
        )
        agents_md.write_text(malformed_content)

        result = project.init()

        # File should be unchanged
        assert agents_md.read_text() == malformed_content
        assert "AGENTS.md" in result.skipped
        # Should have a warning about multiple markers
        assert any("marker" in w.lower() for w in result.warnings)

    def test_reinit_reports_updated_not_skipped(self, temp_project):
        """When markers exist and content is rewritten, report as created not skipped."""
        project = Project(temp_project)
        project.init()

        # Second init should update the managed content
        result = project.init()

        # With markers, we should see it in created (updated), not skipped
        assert "AGENTS.md" in result.created


class TestProjectInitIdempotency:
    """Tests for Project.init() idempotency.

    Note: Trunk docs are never overwritten (overwrite=False) so they appear
    in skipped on subsequent runs. AGENTS.md with markers has its managed
    content updated while preserving user content.
    """

    # Chunk: docs/chunks/plugin_init_slimdown - Skills are no longer rendered by init
    def test_init_preserves_user_content_updates_agents_md(self, temp_project):
        """Running init() twice: trunk skipped, AGENTS.md updated.

        Note: AGENTS.md with markers is updated (in created) on subsequent runs,
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

        # AGENTS.md with markers is updated, not skipped
        assert "AGENTS.md" in result2.created

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

    # Chunk: docs/chunks/plugin_init_slimdown - Init leaves legacy skill layouts untouched
    def test_init_does_not_touch_existing_legacy_skills(self, temp_project):
        """init() neither updates nor removes a pre-existing legacy .agents/skills/ layout.

        Cleaning up legacy layouts is plugin_legacy_migration's job; the
        slimmed init simply stops rendering skills.
        """
        project = Project(temp_project)

        # Create a legacy skills dir with existing file
        skill_dir = temp_project / ".agents" / "skills" / "chunk-create"
        skill_dir.mkdir(parents=True)
        existing_skill = skill_dir / "SKILL.md"
        existing_skill.write_text("Old content")

        result = project.init()

        # The legacy file is left exactly as it was and is not reported
        assert existing_skill.read_text() == "Old content"
        assert not any(".agents/skills/" in f for f in result.created)
        assert not any(".agents/skills/" in f for f in result.skipped)

    def test_init_skips_existing_agents_md_without_markers(self, temp_project):
        """init() skips existing AGENTS.md without markers."""
        project = Project(temp_project)

        # Create custom AGENTS.md without markers
        custom_content = "# Custom AGENTS.md\nDo not overwrite."
        (temp_project / "AGENTS.md").write_text(custom_content)

        result = project.init()

        # Custom content should be preserved
        assert (temp_project / "AGENTS.md").read_text() == custom_content
        assert "AGENTS.md" in result.skipped

    def test_init_result_tracks_skipped_and_created(self, temp_project):
        """init() result correctly tracks which files were skipped vs created."""
        project = Project(temp_project)

        # First run - all created, none skipped
        result1 = project.init()
        assert len(result1.skipped) == 0
        assert len(result1.created) > 0

        # Second run - user content skipped, AGENTS.md managed block updated
        result2 = project.init()
        # Trunk + narratives + chunks + reviewers should be skipped
        assert len(result2.skipped) >= 6  # 4 trunk files + narratives + chunks + reviewers
        # AGENTS.md (with markers) should be in created (updated)
        assert len(result2.created) > 0

    def test_init_restores_deleted_agents_md(self, temp_project):
        """init() restores a deleted AGENTS.md on subsequent run."""
        project = Project(temp_project)

        # First run - initialize
        project.init()
        agents_md = temp_project / "AGENTS.md"
        assert agents_md.exists()

        # Delete AGENTS.md and its symlink
        claude_md = temp_project / "CLAUDE.md"
        if claude_md.is_symlink():
            claude_md.unlink()
        agents_md.unlink()
        assert not agents_md.exists()

        # Second run - should restore the deleted file
        result = project.init()
        assert agents_md.exists()
        assert "AGENTS.md" in result.created
        # CLAUDE.md symlink should be recreated
        assert claude_md.is_symlink()


# Chunk: docs/chunks/plugin_init_slimdown - Direct coverage for the kept helper (used by plugin_legacy_migration)
class TestIsVeGeneratedFile:
    """Tests for the _is_ve_generated_file() helper.

    The helper is retained after the init slim-down because legacy-layout
    cleanup (plugin_legacy_migration) uses it to identify VE-generated files
    that are safe to remove.
    """

    def test_detects_auto_generated_header(self, tmp_path):
        """Returns True for files containing the AUTO-GENERATED header."""
        path = tmp_path / "chunk-create.md"
        path.write_text(
            "<!--\nAUTO-GENERATED FILE - DO NOT EDIT DIRECTLY\n-->\n# chunk-create skill"
        )
        assert _is_ve_generated_file(path) is True

    def test_user_authored_file_is_not_ve_generated(self, tmp_path):
        """Returns False for files without the AUTO-GENERATED header."""
        path = tmp_path / "custom.md"
        path.write_text("# My custom command\nThis is user-authored content.")
        assert _is_ve_generated_file(path) is False

    def test_missing_file_is_not_ve_generated(self, tmp_path):
        """Returns False (no exception) when the file cannot be read."""
        path = tmp_path / "does-not-exist.md"
        assert _is_ve_generated_file(path) is False

    def test_binary_file_is_not_ve_generated(self, tmp_path):
        """Returns False for files that cannot be decoded as UTF-8."""
        path = tmp_path / "binary.md"
        path.write_bytes(b"\xff\xfe\x00\x01invalid utf-8 \x80\x81")
        assert _is_ve_generated_file(path) is False
