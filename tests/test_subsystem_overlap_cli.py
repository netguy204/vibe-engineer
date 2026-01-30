"""Tests for the 've subsystem overlap' CLI command."""
# Chunk: docs/chunks/taskdir_subsystem_overlap - Task context support for subsystem overlap

from click.testing import CliRunner

from ve import cli
from conftest import setup_task_directory, make_ve_initialized_git_repo


class TestSubsystemOverlapNoOverlap:
    """Tests for 've subsystem overlap' when no overlap exists."""

    def _create_chunk_with_refs(self, temp_project, chunk_name, code_refs=None, code_paths=None):
        """Helper to create a chunk with code_references and/or code_paths."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

        parts = ["status: IMPLEMENTING"]

        if code_refs:
            parts.append("code_references:")
            for ref in code_refs:
                parts.append(f'  - ref: "{ref["ref"]}"')
                parts.append(f'    implements: "{ref.get("implements", "Implementation")}"')
        else:
            parts.append("code_references: []")

        if code_paths:
            parts.append("code_paths:")
            for path in code_paths:
                parts.append(f"  - {path}")
        else:
            parts.append("code_paths: []")

        frontmatter = "\n".join(parts)
        (chunk_path / "GOAL.md").write_text(f"""---
{frontmatter}
---

# Chunk Goal
""")

    def _create_subsystem_with_refs(self, temp_project, subsystem_name, code_refs, status="DOCUMENTED"):
        """Helper to create a subsystem with code_references."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (subsystem_path / "OVERVIEW.md").write_text(f"""---
status: {status}
chunks: []
{refs_yaml}
---

# Subsystem
""")

    def test_exits_0_with_no_output_when_no_overlap(self, runner, temp_project):
        """Exits 0 with no output when no overlap detected."""
        # Create chunk referencing one file
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py", "implements": "Foo module"}
        ])

        # Create subsystem referencing different file
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/bar.py", "implements": "Bar module"}
        ])

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestSubsystemOverlapWithOverlap:
    """Tests for 've subsystem overlap' when overlap exists."""

    def _create_chunk_with_refs(self, temp_project, chunk_name, code_refs=None, code_paths=None):
        """Helper to create a chunk with code_references and/or code_paths."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

        parts = ["status: IMPLEMENTING"]

        if code_refs:
            parts.append("code_references:")
            for ref in code_refs:
                parts.append(f'  - ref: "{ref["ref"]}"')
                parts.append(f'    implements: "{ref.get("implements", "Implementation")}"')
        else:
            parts.append("code_references: []")

        if code_paths:
            parts.append("code_paths:")
            for path in code_paths:
                parts.append(f"  - {path}")
        else:
            parts.append("code_paths: []")

        frontmatter = "\n".join(parts)
        (chunk_path / "GOAL.md").write_text(f"""---
{frontmatter}
---

# Chunk Goal
""")

    def _create_subsystem_with_refs(self, temp_project, subsystem_name, code_refs, status="DOCUMENTED"):
        """Helper to create a subsystem with code_references."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (subsystem_path / "OVERVIEW.md").write_text(f"""---
status: {status}
chunks: []
{refs_yaml}
---

# Subsystem
""")

    def test_exits_0_listing_overlapping_subsystems(self, runner, temp_project):
        """Exits 0 and lists overlapping subsystems when overlap detected."""
        # Create overlapping chunk and subsystem
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        self._create_subsystem_with_refs(
            temp_project, "0001-validation",
            [{"ref": "src/foo.py#Bar", "implements": "Bar class"}],
            status="STABLE"
        )

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output

    def test_shows_subsystem_status(self, runner, temp_project):
        """Each output line includes subsystem status."""
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        self._create_subsystem_with_refs(
            temp_project, "0001-validation",
            [{"ref": "src/foo.py#Bar", "implements": "Bar class"}],
            status="STABLE"
        )

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "[STABLE]" in result.output

    def test_lists_multiple_overlapping_subsystems(self, runner, temp_project):
        """Lists all overlapping subsystems when multiple exist."""
        # Chunk references two files
        self._create_chunk_with_refs(temp_project, "0001-feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"},
            {"ref": "src/baz.py#Qux", "implements": "Qux class"},
        ])

        # First subsystem overlaps with src/foo.py
        self._create_subsystem_with_refs(temp_project, "0001-validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ], status="STABLE")

        # Second subsystem overlaps with src/baz.py
        self._create_subsystem_with_refs(temp_project, "0002-processing", [
            {"ref": "src/baz.py#Qux", "implements": "Qux class"}
        ], status="DOCUMENTED")

        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "0001-feature", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output
        assert "[STABLE]" in result.output
        assert "docs/subsystems/0002-processing" in result.output
        assert "[DOCUMENTED]" in result.output


class TestSubsystemOverlapErrors:
    """Tests for error handling."""

    def test_exits_1_for_invalid_chunk_id(self, runner, temp_project):
        """Exits 1 with error message when chunk not found."""
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "9999-nonexistent", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestSubsystemOverlapInTaskContext:
    """Tests for 've subsystem overlap' in task directory context."""

    def _create_chunk_with_refs(self, project_path, chunk_name, code_refs=None):
        """Helper to create a chunk with code_references."""
        chunk_path = project_path / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (chunk_path / "GOAL.md").write_text(f"""---
status: IMPLEMENTING
code_paths: []
{refs_yaml}
---

# Chunk Goal
""")

    def _create_subsystem_with_refs(self, project_path, subsystem_name, code_refs, status="DOCUMENTED"):
        """Helper to create a subsystem with code_references."""
        subsystem_path = project_path / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (subsystem_path / "OVERVIEW.md").write_text(f"""---
status: {status}
chunks: []
{refs_yaml}
---

# Subsystem
""")

    def test_finds_overlap_for_chunk_in_external_repo(self, tmp_path):
        """Finds overlapping subsystems for chunk in external repo."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create chunk in external repo with code reference
        self._create_chunk_with_refs(external_path, "auth_feature", code_refs=[
            {"ref": "src/auth.py#AuthHandler", "implements": "Auth handler"}
        ])

        # Create subsystem in external repo with overlapping reference
        self._create_subsystem_with_refs(external_path, "authentication", [
            {"ref": "src/auth.py#AuthHandler", "implements": "Auth handler"}
        ], status="STABLE")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "auth_feature", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/authentication" in result.output
        assert "[STABLE]" in result.output

    def test_finds_chunk_in_project_repo_when_not_in_external(self, tmp_path):
        """Finds chunk in project repo when not in external repo."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create chunk in project repo (not external)
        self._create_chunk_with_refs(project_paths[0], "local_feature", code_refs=[
            {"ref": "src/feature.py#Feature", "implements": "Feature class"}
        ])

        # Create subsystem in project repo with overlapping reference
        self._create_subsystem_with_refs(project_paths[0], "features", [
            {"ref": "src/feature.py#Feature", "implements": "Feature class"}
        ], status="DOCUMENTED")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "local_feature", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/features" in result.output
        assert "[DOCUMENTED]" in result.output

    def test_prefers_external_repo_over_project_repo(self, tmp_path):
        """External repo chunk is used when same name exists in both."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1"]
        )

        # Create same-named chunk in both repos with different code refs
        self._create_chunk_with_refs(external_path, "shared_chunk", code_refs=[
            {"ref": "src/external.py#Handler", "implements": "External handler"}
        ])
        self._create_chunk_with_refs(project_paths[0], "shared_chunk", code_refs=[
            {"ref": "src/local.py#Handler", "implements": "Local handler"}
        ])

        # Create subsystem matching only external chunk's reference
        self._create_subsystem_with_refs(external_path, "ext_subsystem", [
            {"ref": "src/external.py#Handler", "implements": "External handler"}
        ], status="STABLE")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "shared_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Should find overlap with external subsystem (external chunk preferred)
        assert "docs/subsystems/ext_subsystem" in result.output

    def test_no_overlap_when_different_files(self, tmp_path):
        """No overlap when chunk and subsystem reference different files."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create chunk with one file reference
        self._create_chunk_with_refs(external_path, "my_chunk", code_refs=[
            {"ref": "src/foo.py#Foo", "implements": "Foo class"}
        ])

        # Create subsystem with different file reference
        self._create_subsystem_with_refs(external_path, "my_subsystem", [
            {"ref": "src/bar.py#Bar", "implements": "Bar class"}
        ], status="DOCUMENTED")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "my_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # No output means no overlap
        assert "my_subsystem" not in result.output

    def test_error_when_chunk_not_found_in_any_repo(self, tmp_path):
        """Reports error when chunk doesn't exist in any repo."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "nonexistent_chunk", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestSubsystemOverlapOutsideTaskContext:
    """Tests for 've subsystem overlap' outside task directory context."""

    def _create_chunk_with_refs(self, project_path, chunk_name, code_refs=None):
        """Helper to create a chunk with code_references."""
        chunk_path = project_path / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (chunk_path / "GOAL.md").write_text(f"""---
status: IMPLEMENTING
code_paths: []
{refs_yaml}
---

# Chunk Goal
""")

    def _create_subsystem_with_refs(self, project_path, subsystem_name, code_refs, status="DOCUMENTED"):
        """Helper to create a subsystem with code_references."""
        subsystem_path = project_path / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)

        if code_refs:
            refs_yaml = "code_references:"
            for ref in code_refs:
                refs_yaml += f'\n  - ref: "{ref["ref"]}"'
                refs_yaml += f'\n    implements: "{ref.get("implements", "Implementation")}"'
        else:
            refs_yaml = "code_references: []"

        (subsystem_path / "OVERVIEW.md").write_text(f"""---
status: {status}
chunks: []
{refs_yaml}
---

# Subsystem
""")

    def test_behavior_unchanged_in_single_repo(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create chunk with code reference
        self._create_chunk_with_refs(project_path, "my_feature", code_refs=[
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ])

        # Create subsystem with overlapping reference
        self._create_subsystem_with_refs(project_path, "validation", [
            {"ref": "src/foo.py#Bar", "implements": "Bar class"}
        ], status="STABLE")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "overlap", "my_feature", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/validation" in result.output
        assert "[STABLE]" in result.output
        # Should NOT have repo prefix in single-repo mode
        assert "acme/" not in result.output
