"""Tests for artifact demotion from external to project-local.

# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/artifact_demote_to_project - Demote external artifacts to project-local
"""

import re

import pytest
import yaml
from click.testing import CliRunner

from ve import cli
from external_refs import load_external_ref, ARTIFACT_MAIN_FILE, ARTIFACT_DIR_NAME
from models import ArtifactType
from task import (
    demote_artifact,
    scan_demotable_artifacts,
    TaskDemoteError,
)
from conftest import setup_task_directory


def _create_external_artifact(external_path, artifact_type, name, dependents=None, extra_frontmatter=None):
    """Helper to create an artifact in the external repo with dependents.

    Args:
        external_path: Path to external repo.
        artifact_type: ArtifactType enum.
        name: Artifact name (directory name).
        dependents: List of dependent dicts.
        extra_frontmatter: Additional frontmatter fields.

    Returns:
        Path to the created artifact directory.
    """
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    main_file = ARTIFACT_MAIN_FILE[artifact_type]
    artifact_dir = external_path / "docs" / dir_name / name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "status": "IMPLEMENTING" if artifact_type == ArtifactType.CHUNK else "ONGOING",
        "created_after": [],
    }
    if dependents:
        frontmatter["dependents"] = dependents
    if extra_frontmatter:
        frontmatter.update(extra_frontmatter)

    body = f"# {name}\n\nArtifact content.\n"
    frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    (artifact_dir / main_file).write_text(f"---\n{frontmatter_yaml}---\n\n{body}")

    # For chunks, also create PLAN.md
    if artifact_type == ArtifactType.CHUNK:
        plan_fm = yaml.dump({}, default_flow_style=False, sort_keys=False)
        (artifact_dir / "PLAN.md").write_text(f"---\n{plan_fm}---\n\n# Plan\n\nPlan content.\n")

    return artifact_dir


def _create_external_yaml_pointer(project_path, artifact_type, name, repo, artifact_id=None, created_after=None):
    """Helper to create an external.yaml pointer in a project.

    Args:
        project_path: Path to project repo.
        artifact_type: ArtifactType enum.
        name: Local directory name for the artifact.
        repo: External repo reference (org/repo).
        artifact_id: Artifact ID in external repo (defaults to name).
        created_after: Local causal ordering deps.

    Returns:
        Path to the artifact directory containing external.yaml.
    """
    dir_name = ARTIFACT_DIR_NAME[artifact_type]
    artifact_dir = project_path / "docs" / dir_name / name
    artifact_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "artifact_type": artifact_type.value,
        "artifact_id": artifact_id or name,
        "repo": repo,
        "track": "main",
    }
    if created_after:
        data["created_after"] = created_after

    (artifact_dir / "external.yaml").write_text(yaml.dump(data, default_flow_style=False))
    return artifact_dir


def _read_frontmatter(filepath):
    """Read and parse YAML frontmatter from a file."""
    content = filepath.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


# =============================================================================
# Tests for demote_artifact() core function
# =============================================================================

class TestDemoteArtifactCore:
    """Tests for the demote_artifact() core function."""

    def test_happy_path_demotes_chunk(self, tmp_path):
        """Demotes a single-dependent chunk from external to project-local."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create chunk in external repo with one dependent
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "my_feature",
            dependents=[{"artifact_type": "chunk", "artifact_id": "my_feature", "repo": "acme/proj"}],
        )

        # Create external.yaml pointer in project
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "my_feature", "acme/ext",
        )

        # Demote
        result = demote_artifact(task_dir, "my_feature")

        # Verify result
        assert result["demoted_artifact"] == "my_feature"
        assert result["artifact_type"] == "chunk"
        assert result["target_project"] == "acme/proj"

        # Verify GOAL.md and PLAN.md now exist locally
        local_chunk_dir = project_path / "docs" / "chunks" / "my_feature"
        assert (local_chunk_dir / "GOAL.md").exists()
        assert (local_chunk_dir / "PLAN.md").exists()

        # Verify external.yaml is gone
        assert not (local_chunk_dir / "external.yaml").exists()

    def test_multi_project_raises_error(self, tmp_path):
        """Cannot demote artifact with multiple dependents without specifying project."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Create chunk with two dependents
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "shared_chunk",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "shared_chunk", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "shared_chunk", "repo": "acme/proj2"},
            ],
        )

        # Create external.yaml in both projects
        for proj_path in project_paths:
            _create_external_yaml_pointer(
                proj_path, ArtifactType.CHUNK, "shared_chunk", "acme/ext",
            )

        with pytest.raises(TaskDemoteError, match="multiple dependent projects"):
            demote_artifact(task_dir, "shared_chunk")

    def test_already_local_raises_error(self, tmp_path):
        """Cannot demote an artifact that has no external.yaml (already local)."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create chunk in external repo with one dependent
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "local_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "local_chunk", "repo": "acme/proj"}],
        )

        # Create the chunk directory locally WITHOUT external.yaml (already local)
        local_chunk_dir = project_path / "docs" / "chunks" / "local_chunk"
        local_chunk_dir.mkdir(parents=True)
        (local_chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n\n# Local\n")

        with pytest.raises(TaskDemoteError, match="already local"):
            demote_artifact(task_dir, "local_chunk")

    def test_all_artifact_types(self, tmp_path):
        """Demote works for all artifact types: chunk, investigation, narrative, subsystem."""
        for artifact_type in ArtifactType:
            # Fresh task dir for each type to avoid conflicts
            type_dir = tmp_path / artifact_type.value
            type_dir.mkdir()
            task_dir, external_path, project_paths = setup_task_directory(
                type_dir
            )
            project_path = project_paths[0]

            name = f"test_{artifact_type.value}"
            _create_external_artifact(
                external_path, artifact_type, name,
                dependents=[{"artifact_type": artifact_type.value, "artifact_id": name, "repo": "acme/proj"}],
            )
            _create_external_yaml_pointer(
                project_path, artifact_type, name, "acme/ext",
            )

            result = demote_artifact(task_dir, f"docs/{ARTIFACT_DIR_NAME[artifact_type]}/{name}")

            assert result["artifact_type"] == artifact_type.value
            assert result["demoted_artifact"] == name

            # Verify main file exists locally
            main_file = ARTIFACT_MAIN_FILE[artifact_type]
            local_dir = project_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / name
            assert (local_dir / main_file).exists()
            assert not (local_dir / "external.yaml").exists()

    def test_preserves_frontmatter(self, tmp_path):
        """After demote, the local artifact retains its original frontmatter."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create chunk with rich frontmatter
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "rich_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "rich_chunk", "repo": "acme/proj"}],
            extra_frontmatter={
                "code_paths": ["src/foo.py", "src/bar.py"],
                "ticket": "PROJ-123",
            },
        )
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "rich_chunk", "acme/ext",
        )

        demote_artifact(task_dir, "rich_chunk")

        # Verify frontmatter is preserved
        local_goal = project_path / "docs" / "chunks" / "rich_chunk" / "GOAL.md"
        fm = _read_frontmatter(local_goal)
        assert fm.get("code_paths") == ["src/foo.py", "src/bar.py"]
        assert fm.get("ticket") == "PROJ-123"

    def test_removes_dependent_entry(self, tmp_path):
        """Demoting removes the dependent entry from the external artifact's frontmatter."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "dep_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "dep_chunk", "repo": "acme/proj"}],
        )
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "dep_chunk", "acme/ext",
        )

        result = demote_artifact(task_dir, "dep_chunk")
        assert result["external_cleaned"] is True

        # Verify the external artifact's dependents list is now empty
        ext_goal = external_path / "docs" / "chunks" / "dep_chunk" / "GOAL.md"
        fm = _read_frontmatter(ext_goal)
        assert fm.get("dependents") == []

    def test_no_dependents_raises_error(self, tmp_path):
        """Cannot demote an orphaned artifact (zero dependents)."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create chunk with no dependents
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "orphan_chunk",
            dependents=[],
        )

        with pytest.raises(TaskDemoteError, match="no dependent projects"):
            demote_artifact(task_dir, "orphan_chunk")

    def test_demote_with_target_project(self, tmp_path):
        """Can demote multi-dependent artifact when target_project is specified."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "multi_chunk",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "multi_chunk", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "multi_chunk", "repo": "acme/proj2"},
            ],
        )
        for proj_path in project_paths:
            _create_external_yaml_pointer(
                proj_path, ArtifactType.CHUNK, "multi_chunk", "acme/ext",
            )

        result = demote_artifact(task_dir, "multi_chunk", target_project="proj1")

        assert result["target_project"] == "acme/proj1"
        assert result["external_cleaned"] is False  # proj2 still depends on it

        # Verify proj1 has local files
        local_dir = project_paths[0] / "docs" / "chunks" / "multi_chunk"
        assert (local_dir / "GOAL.md").exists()
        assert not (local_dir / "external.yaml").exists()

        # Verify proj2 still has external.yaml
        ext_dir = project_paths[1] / "docs" / "chunks" / "multi_chunk"
        assert (ext_dir / "external.yaml").exists()

    def test_restores_created_after_from_external_yaml(self, tmp_path):
        """Demote restores the original created_after from external.yaml."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create chunk in external with external-repo created_after
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "causal_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "causal_chunk", "repo": "acme/proj"}],
            extra_frontmatter={"created_after": ["external_tip_1", "external_tip_2"]},
        )

        # The external.yaml has local created_after (different from external repo's)
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "causal_chunk", "acme/ext",
            created_after=["local_dep_1"],
        )

        demote_artifact(task_dir, "causal_chunk")

        # After demote, created_after should be restored from external.yaml
        local_goal = project_path / "docs" / "chunks" / "causal_chunk" / "GOAL.md"
        fm = _read_frontmatter(local_goal)
        assert fm.get("created_after") == ["local_dep_1"]


# =============================================================================
# Tests for scan_demotable_artifacts()
# =============================================================================

class TestScanDemotableArtifacts:
    """Tests for the scan_demotable_artifacts() function."""

    def test_finds_single_project_artifacts(self, tmp_path):
        """Identifies artifacts with exactly one dependent as demotable."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # One-dependent artifact (demotable)
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "single_dep",
            dependents=[{"artifact_type": "chunk", "artifact_id": "single_dep", "repo": "acme/proj1"}],
        )

        # Two-dependent artifact (not demotable)
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "multi_dep",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "multi_dep", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "multi_dep", "repo": "acme/proj2"},
            ],
        )

        # Orphaned artifact (not demotable)
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "orphan",
            dependents=[],
        )

        candidates = scan_demotable_artifacts(task_dir)

        assert len(candidates) == 1
        assert candidates[0]["artifact_id"] == "single_dep"
        assert candidates[0]["target_project"] == "acme/proj1"

    def test_empty_result_all_multi_dependent(self, tmp_path):
        """Returns empty list when all artifacts have multiple dependents."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "shared1",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "shared1", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "shared1", "repo": "acme/proj2"},
            ],
        )

        candidates = scan_demotable_artifacts(task_dir)
        assert candidates == []

    def test_code_path_heuristic(self, tmp_path):
        """Artifacts with code_paths and no cross-project refs get enhanced reason."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "confined_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "confined_chunk", "repo": "acme/proj"}],
            extra_frontmatter={
                "code_paths": ["src/foo.py"],
                "code_references": [],
            },
        )

        candidates = scan_demotable_artifacts(task_dir)

        assert len(candidates) == 1
        assert "confined to one project" in candidates[0]["reason"]

    def test_scans_all_artifact_types(self, tmp_path):
        """Scanner finds demotable artifacts across all types."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "demotable_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "demotable_chunk", "repo": "acme/proj"}],
        )
        _create_external_artifact(
            external_path, ArtifactType.INVESTIGATION, "demotable_inv",
            dependents=[{"artifact_type": "investigation", "artifact_id": "demotable_inv", "repo": "acme/proj"}],
        )

        candidates = scan_demotable_artifacts(task_dir)

        assert len(candidates) == 2
        types = {c["artifact_type"] for c in candidates}
        assert types == {"chunk", "investigation"}


# =============================================================================
# Tests for CLI commands
# =============================================================================

class TestDemoteCLI:
    """Tests for the `ve task demote` CLI command."""

    def test_demote_single_artifact(self, tmp_path):
        """CLI: ve task demote my_chunk."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "cli_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "cli_chunk", "repo": "acme/proj"}],
        )
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "cli_chunk", "acme/ext",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "cli_chunk", "--cwd", str(task_dir)])

        assert result.exit_code == 0, result.output
        assert "Demoted" in result.output
        assert "cli_chunk" in result.output

    def test_demote_auto_dry_run(self, tmp_path):
        """CLI: ve task demote --auto lists candidates without modifying."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "auto_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "auto_chunk", "repo": "acme/proj"}],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "--auto", "--cwd", str(task_dir)])

        assert result.exit_code == 0, result.output
        assert "auto_chunk" in result.output
        assert "eligible for demotion" in result.output

        # Verify artifact was NOT demoted (dry run)
        ext_goal = external_path / "docs" / "chunks" / "auto_chunk" / "GOAL.md"
        fm = _read_frontmatter(ext_goal)
        assert len(fm.get("dependents", [])) == 1

    def test_demote_auto_apply(self, tmp_path):
        """CLI: ve task demote --auto --apply demotes all candidates."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "apply_chunk",
            dependents=[{"artifact_type": "chunk", "artifact_id": "apply_chunk", "repo": "acme/proj"}],
        )
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "apply_chunk", "acme/ext",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "--auto", "--apply", "--cwd", str(task_dir)])

        assert result.exit_code == 0, result.output
        assert "Demoted" in result.output

        # Verify artifact was demoted
        local_dir = project_path / "docs" / "chunks" / "apply_chunk"
        assert (local_dir / "GOAL.md").exists()
        assert not (local_dir / "external.yaml").exists()

    def test_demote_no_args_shows_error(self, tmp_path):
        """CLI: ve task demote without args shows error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "--cwd", str(tmp_path)])

        assert result.exit_code == 1
        assert "provide an ARTIFACT" in result.output or "Error" in result.output

    def test_demote_multi_project_error(self, tmp_path):
        """CLI: ve task demote on multi-project artifact shows error."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "shared",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "shared", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "shared", "repo": "acme/proj2"},
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "shared", "--cwd", str(task_dir)])

        assert result.exit_code == 1
        assert "multiple" in result.output.lower()

    def test_apply_without_auto_shows_error(self):
        """CLI: --apply without --auto shows error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["task", "demote", "some_artifact", "--apply", "--cwd", "."])

        assert result.exit_code == 1
        assert "--apply requires --auto" in result.output


# =============================================================================
# Tests for chunk-complete in task context
# =============================================================================

class TestChunkCompleteTaskContext:
    """Tests for chunk-complete auto-demotion in task context."""

    def test_auto_demote_on_complete(self, tmp_path):
        """In task context, completing a single-dependent chunk auto-demotes it."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an IMPLEMENTING chunk in external repo
        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "complete_me",
            dependents=[{"artifact_type": "chunk", "artifact_id": "complete_me", "repo": "acme/proj"}],
            extra_frontmatter={"status": "IMPLEMENTING"},
        )
        _create_external_yaml_pointer(
            project_path, ArtifactType.CHUNK, "complete_me", "acme/ext",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "complete", "complete_me", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0, result.output
        assert "Completed" in result.output
        assert "Auto-demoted" in result.output

        # Verify chunk was demoted to local
        local_dir = project_path / "docs" / "chunks" / "complete_me"
        assert (local_dir / "GOAL.md").exists()
        assert not (local_dir / "external.yaml").exists()

        # Verify the demoted local copy has ACTIVE status
        # (complete updates status to ACTIVE in external, then demote copies it locally)
        fm = _read_frontmatter(local_dir / "GOAL.md")
        assert fm.get("status") == "ACTIVE"

    def test_no_auto_demote_for_multi_project(self, tmp_path):
        """Multi-project chunks stay external after completion."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        _create_external_artifact(
            external_path, ArtifactType.CHUNK, "multi_complete",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "multi_complete", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "multi_complete", "repo": "acme/proj2"},
            ],
            extra_frontmatter={"status": "IMPLEMENTING"},
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "complete", "multi_complete", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0, result.output
        assert "Completed" in result.output
        assert "keeping as external" in result.output

    def test_non_task_context_unchanged(self, tmp_path):
        """Completing a chunk outside task context works as before."""
        # Create a simple non-task project
        from conftest import make_ve_initialized_git_repo
        project_path = tmp_path / "simple_project"
        make_ve_initialized_git_repo(project_path)

        # Create a local IMPLEMENTING chunk
        chunk_dir = project_path / "docs" / "chunks" / "simple_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\ncreated_after: []\n---\n\n# Simple\n")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "complete", "simple_chunk", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0, result.output
        assert "Completed" in result.output
        assert "demote" not in result.output.lower()

        # Verify status was updated to ACTIVE
        fm = _read_frontmatter(chunk_dir / "GOAL.md")
        assert fm.get("status") == "ACTIVE"
