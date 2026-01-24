"""Tests for ve chunk list-proposed command."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/task_list_proposed - Task-aware proposed chunk listing

import pathlib

import pytest
from click.testing import CliRunner

from ve import cli
from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from subsystems import Subsystems
from conftest import setup_task_directory


class TestListProposedChunksLogic:
    """Tests for the list_proposed_chunks business logic."""

    def test_empty_project_returns_empty_list(self, temp_project):
        """Verify empty project has no proposed chunks."""
        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)
        assert result == []

    def test_investigation_with_proposed_chunks(self, temp_project):
        """Verify investigation proposed chunks are included."""
        # Create investigation directory with proposed chunks
        inv_dir = temp_project / "docs" / "investigations" / "0001-test_inv"
        inv_dir.mkdir(parents=True)

        overview = inv_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ONGOING
trigger: "Test trigger"
proposed_chunks:
  - prompt: "First proposed chunk"
    chunk_directory: null
  - prompt: "Second proposed chunk"
    chunk_directory: "0005-already_created"
---
# Test Investigation
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should only include the one without chunk_directory
        assert len(result) == 1
        assert result[0]["prompt"] == "First proposed chunk"
        assert result[0]["source_type"] == "investigation"
        assert result[0]["source_id"] == "0001-test_inv"

    def test_narrative_with_proposed_chunks(self, temp_project):
        """Verify narrative proposed_chunks are included."""
        # Create narrative directory with proposed_chunks
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Narrative chunk prompt"
    chunk_directory: null
---
# Test Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 1
        assert result[0]["prompt"] == "Narrative chunk prompt"
        assert result[0]["source_type"] == "narrative"
        assert result[0]["source_id"] == "0001-test_narr"

    def test_narrative_with_legacy_chunks_field(self, temp_project):
        """Verify legacy 'chunks' field in narratives is handled."""
        # Create narrative directory with legacy 'chunks' field
        narr_dir = temp_project / "docs" / "narratives" / "0001-legacy_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: null
chunks:
  - prompt: "Legacy chunk prompt"
    chunk_directory: null
---
# Legacy Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should map legacy 'chunks' to 'proposed_chunks'
        assert len(result) == 1
        assert result[0]["prompt"] == "Legacy chunk prompt"
        assert result[0]["source_type"] == "narrative"

    def test_subsystem_with_proposed_chunks(self, temp_project):
        """Verify subsystem proposed_chunks are included."""
        # Create subsystem directory with proposed_chunks
        sub_dir = temp_project / "docs" / "subsystems" / "0001-test_sub"
        sub_dir.mkdir(parents=True)

        overview = sub_dir / "OVERVIEW.md"
        overview.write_text("""---
status: DOCUMENTED
chunks: []
code_references: []
proposed_chunks:
  - prompt: "Consolidation chunk prompt"
    chunk_directory: null
---
# test_sub
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 1
        assert result[0]["prompt"] == "Consolidation chunk prompt"
        assert result[0]["source_type"] == "subsystem"
        assert result[0]["source_id"] == "0001-test_sub"

    def test_created_chunks_filtered_out(self, temp_project):
        """Verify chunks with chunk_directory set are filtered out."""
        # Create narrative with a created chunk
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Already created"
    chunk_directory: "0010-already_created"
---
# Test Narrative
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        # Should be empty since the only proposed chunk has been created
        assert result == []

    def test_multiple_sources_aggregated(self, temp_project):
        """Verify proposed chunks from multiple sources are aggregated."""
        # Create investigation
        inv_dir = temp_project / "docs" / "investigations" / "0001-inv"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: null
proposed_chunks:
  - prompt: "From investigation"
    chunk_directory: null
---
""")

        # Create narrative
        narr_dir = temp_project / "docs" / "narratives" / "0001-narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "From narrative"
    chunk_directory: null
---
""")

        # Create subsystem
        sub_dir = temp_project / "docs" / "subsystems" / "0001-sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "OVERVIEW.md").write_text("""---
status: DISCOVERING
chunks: []
code_references: []
proposed_chunks:
  - prompt: "From subsystem"
    chunk_directory: null
---
""")

        chunks = Chunks(temp_project)
        investigations = Investigations(temp_project)
        narratives = Narratives(temp_project)
        subsystems = Subsystems(temp_project)

        result = chunks.list_proposed_chunks(investigations, narratives, subsystems)

        assert len(result) == 3
        prompts = {r["prompt"] for r in result}
        assert prompts == {"From investigation", "From narrative", "From subsystem"}


class TestListProposedChunksCLI:
    """Tests for the ve chunk list-proposed CLI command."""

    def test_empty_project_outputs_message(self, temp_project, runner):
        """Verify empty project outputs appropriate message."""
        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        assert "No proposed chunks found" in result.output

    def test_shows_grouped_output(self, temp_project, runner):
        """Verify output is grouped by source."""
        # Create narrative with proposed chunk
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Test chunk prompt"
    chunk_directory: null
---
""")

        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        assert "From docs/narratives/0001-test_narr:" in result.output
        assert "Test chunk prompt" in result.output

    def test_long_prompts_truncated(self, temp_project, runner):
        """Verify long prompts are truncated in output."""
        # Create narrative with very long prompt
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        long_prompt = "This is a very long prompt " * 10  # ~270 chars
        (narr_dir / "OVERVIEW.md").write_text(f"""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "{long_prompt}"
    chunk_directory: null
---
""")

        result = runner.invoke(cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)])

        assert result.exit_code == 0
        # Should be truncated with ...
        assert "..." in result.output
        # Full prompt shouldn't appear
        assert long_prompt not in result.output


class TestListProposedChunksTaskContext:
    """Tests for ve chunk list-proposed in task directory context."""

    def test_task_context_detection(self, tmp_path):
        """Verify running from task directory triggers aggregated output."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create proposed chunk in external repo
        inv_dir = external_path / "docs" / "investigations" / "test_inv"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: "Test trigger"
proposed_chunks:
  - prompt: "External proposed chunk"
    chunk_directory: null
---
# Test Investigation
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Should show external artifacts header
        assert "# External Artifacts (acme/ext)" in result.output
        assert "External proposed chunk" in result.output

    def test_external_repo_collection(self, tmp_path):
        """Verify proposed chunks from all external artifact types are collected."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create investigation with proposed chunk in external repo
        inv_dir = external_path / "docs" / "investigations" / "test_inv"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: "Test trigger"
proposed_chunks:
  - prompt: "From external investigation"
    chunk_directory: null
---
""")

        # Create narrative with proposed chunk in external repo
        narr_dir = external_path / "docs" / "narratives" / "test_narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "From external narrative"
    chunk_directory: null
---
""")

        # Create subsystem with proposed chunk in external repo
        sub_dir = external_path / "docs" / "subsystems" / "test_sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "OVERVIEW.md").write_text("""---
status: DOCUMENTED
chunks: []
code_references: []
proposed_chunks:
  - prompt: "From external subsystem"
    chunk_directory: null
---
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "From external investigation" in result.output
        assert "From external narrative" in result.output
        assert "From external subsystem" in result.output

    def test_project_repo_collection(self, tmp_path):
        """Verify proposed chunks from each project are collected."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Create proposed chunk in first project
        proj1_narr = project_paths[0] / "docs" / "narratives" / "local_narr"
        proj1_narr.mkdir(parents=True)
        (proj1_narr / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "From project 1"
    chunk_directory: null
---
""")

        # Create proposed chunk in second project
        proj2_sub = project_paths[1] / "docs" / "subsystems" / "local_sub"
        proj2_sub.mkdir(parents=True)
        (proj2_sub / "OVERVIEW.md").write_text("""---
status: DISCOVERING
chunks: []
code_references: []
proposed_chunks:
  - prompt: "From project 2"
    chunk_directory: null
---
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Should show project headers
        assert "# acme/proj1 (local)" in result.output
        assert "# acme/proj2 (local)" in result.output
        assert "From project 1" in result.output
        assert "From project 2" in result.output

    def test_grouped_output_format(self, tmp_path):
        """Verify results are grouped by repository with correct headers."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create proposed chunk in external repo
        ext_inv = external_path / "docs" / "investigations" / "ext_inv"
        ext_inv.mkdir(parents=True)
        (ext_inv / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: "Test"
proposed_chunks:
  - prompt: "External chunk"
    chunk_directory: null
---
""")

        # Create proposed chunk in project
        proj_narr = project_paths[0] / "docs" / "narratives" / "proj_narr"
        proj_narr.mkdir(parents=True)
        (proj_narr / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Project chunk"
    chunk_directory: null
---
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Check header format
        assert "# External Artifacts (acme/ext)" in result.output
        assert "# acme/proj (local)" in result.output
        # Check source grouping within sections
        assert "From docs/investigations/ext_inv:" in result.output
        assert "From docs/narratives/proj_narr:" in result.output

    def test_empty_sections_show_message(self, tmp_path):
        """Verify empty sections show 'No proposed chunks' message."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Only create proposed chunk in external repo, leave project empty
        ext_inv = external_path / "docs" / "investigations" / "ext_inv"
        ext_inv.mkdir(parents=True)
        (ext_inv / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: "Test"
proposed_chunks:
  - prompt: "External chunk"
    chunk_directory: null
---
""")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # External section should have content
        assert "# External Artifacts (acme/ext)" in result.output
        assert "External chunk" in result.output
        # Project section should show "No proposed chunks"
        assert "# acme/proj (local)" in result.output
        assert "No proposed chunks" in result.output

    def test_backwards_compatibility_single_repo(self, temp_project, runner):
        """Verify single-repo mode continues to work without task context."""
        # Create narrative with proposed chunk
        narr_dir = temp_project / "docs" / "narratives" / "test_narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Single repo chunk"
    chunk_directory: null
---
""")

        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(temp_project)]
        )

        assert result.exit_code == 0
        # Should NOT have task-style headers
        assert "# External Artifacts" not in result.output
        assert "(local)" not in result.output
        # Should have original single-repo format
        assert "From docs/narratives/test_narr:" in result.output
        assert "Single repo chunk" in result.output

    def test_all_empty_task_shows_message(self, tmp_path):
        """Verify empty task (no proposed chunks anywhere) shows appropriate message."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list-proposed", "--project-dir", str(task_dir)]
        )

        # Should still succeed but show no proposed chunks message
        assert result.exit_code == 0
        assert "No proposed chunks" in result.output


class TestListTaskProposedChunksLogic:
    """Tests for the list_task_proposed_chunks business logic."""

    def test_returns_grouped_dict_structure(self, tmp_path):
        """Verify return structure has external and projects keys."""
        from task_utils import list_task_proposed_chunks

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        result = list_task_proposed_chunks(task_dir)

        assert "external" in result
        assert "projects" in result
        assert "repo" in result["external"]
        assert "proposed_chunks" in result["external"]
        assert isinstance(result["projects"], list)

    def test_collects_from_external_repo(self, tmp_path):
        """Verify proposed chunks from external repo are collected."""
        from task_utils import list_task_proposed_chunks

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create proposed chunk in external repo investigation
        inv_dir = external_path / "docs" / "investigations" / "test_inv"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: "Test"
proposed_chunks:
  - prompt: "External proposed chunk"
    chunk_directory: null
---
""")

        result = list_task_proposed_chunks(task_dir)

        assert result["external"]["repo"] == "acme/ext"
        assert len(result["external"]["proposed_chunks"]) == 1
        assert result["external"]["proposed_chunks"][0]["prompt"] == "External proposed chunk"
        assert result["external"]["proposed_chunks"][0]["source_type"] == "investigation"

    def test_collects_from_project_repos(self, tmp_path):
        """Verify proposed chunks from each project repo are collected."""
        from task_utils import list_task_proposed_chunks

        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Create proposed chunk in first project
        narr_dir = project_paths[0] / "docs" / "narratives" / "local_narr"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: DRAFTING
advances_trunk_goal: null
proposed_chunks:
  - prompt: "Project 1 chunk"
    chunk_directory: null
---
""")

        result = list_task_proposed_chunks(task_dir)

        assert len(result["projects"]) == 2
        # Find proj1
        proj1 = next(p for p in result["projects"] if p["repo"] == "acme/proj1")
        assert len(proj1["proposed_chunks"]) == 1
        assert proj1["proposed_chunks"][0]["prompt"] == "Project 1 chunk"

    def test_raises_on_missing_external_repo(self, tmp_path):
        """Verify TaskChunkError raised when external repo not found."""
        from task_utils import list_task_proposed_chunks, TaskChunkError

        task_dir = tmp_path

        # Create .ve-task.yaml pointing to non-existent repo
        (task_dir / ".ve-task.yaml").write_text("""external_artifact_repo: acme/missing
projects:
  - acme/proj
""")

        # Create project dir but not external repo
        proj_path = task_dir / "proj"
        proj_path.mkdir()

        with pytest.raises(TaskChunkError):
            list_task_proposed_chunks(task_dir)
