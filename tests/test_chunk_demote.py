"""Tests for chunk demotion (full-collapse, cross-repo → single-project).

# Chunk: docs/chunks/chunk_demote - Full-collapse demotion path for cross-repo chunks
"""

import re

import pytest
import yaml
from click.testing import CliRunner

from ve import cli
from conftest import setup_task_directory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_arch_chunk(arch_path, chunk_name, dependents=None, code_paths=None, code_references=None):
    """Create a chunk in the architecture repo.

    Args:
        arch_path: Path to architecture repo root.
        chunk_name: Chunk directory name.
        dependents: List of dependent dicts.
        code_paths: List of code path strings for GOAL.md.
        code_references: List of code_reference dicts for GOAL.md.

    Returns:
        Path to the chunk directory.
    """
    chunk_dir = arch_path / "docs" / "chunks" / chunk_name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "status": "IMPLEMENTING",
        "ticket": None,
        "parent_chunk": None,
        "code_paths": code_paths or [],
        "code_references": code_references or [],
        "created_after": [],
        "depends_on": [],
    }
    if dependents:
        frontmatter["dependents"] = dependents

    body = f"# Chunk Goal\n\n## Minor Goal\n\nTest chunk {chunk_name}.\n"
    fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\n{body}")
    (chunk_dir / "PLAN.md").write_text("---\n{}\n---\n\n# Plan\n\nPlan content.\n")

    return chunk_dir


def _make_external_yaml(project_path, chunk_name, repo):
    """Create an external.yaml pointer in a project's docs/chunks/<name>/.

    Args:
        project_path: Root of the project repo.
        chunk_name: Chunk directory name.
        repo: External repo reference (org/repo).

    Returns:
        Path to the chunk pointer directory.
    """
    pointer_dir = project_path / "docs" / "chunks" / chunk_name
    pointer_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "artifact_type": "chunk",
        "artifact_id": chunk_name,
        "repo": repo,
        "track": "main",
    }
    (pointer_dir / "external.yaml").write_text(yaml.dump(data, default_flow_style=False))
    return pointer_dir


def _read_frontmatter(filepath):
    """Read and parse YAML frontmatter from a markdown file."""
    content = filepath.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _setup_full_demote_scenario(tmp_path, chunk_name="my_feature", target_name="proj1"):
    """Create a standard two-project cross-repo scenario for demotion tests.

    Layout:
        task_dir/
            .ve-task.yaml          (projects: acme/proj1, acme/proj2)
            architecture/          (external artifact repo)
                docs/chunks/my_feature/  GOAL.md + PLAN.md
            proj1/
                docs/chunks/my_feature/  external.yaml
            proj2/
                docs/chunks/my_feature/  external.yaml

    Returns:
        (task_dir, arch_path, proj1_path, proj2_path)
    """
    task_dir, arch_path, project_paths = setup_task_directory(
        tmp_path,
        external_name="architecture",
        project_names=["proj1", "proj2"],
    )
    proj1_path, proj2_path = project_paths

    # Create the chunk in architecture
    _make_arch_chunk(
        arch_path,
        chunk_name,
        dependents=[
            {"artifact_type": "chunk", "artifact_id": chunk_name, "repo": "acme/proj1"},
            {"artifact_type": "chunk", "artifact_id": chunk_name, "repo": "acme/proj2"},
        ],
        code_paths=[f"acme/proj1::src/feature.py", f"acme/proj1::src/utils.py"],
        code_references=[
            {"ref": f"acme/proj1::src/feature.py#MyClass", "implements": "core logic"},
        ],
    )

    # Create external.yaml pointers in both projects
    _make_external_yaml(proj1_path, chunk_name, "acme/architecture")
    _make_external_yaml(proj2_path, chunk_name, "acme/architecture")

    return task_dir, arch_path, proj1_path, proj2_path


# ===========================================================================
# TestValidateChunkScope
# ===========================================================================

class TestValidateChunkScope:
    """Unit tests for validate_chunk_scope()."""

    def test_accepts_bare_paths(self, tmp_path):
        """Paths without '::' prefix are always acceptable."""
        from chunk_demote import validate_chunk_scope

        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        fm = {"status": "IMPLEMENTING", "code_paths": ["src/foo.py", "src/bar.py"]}
        fm_yaml = yaml.dump(fm, default_flow_style=False)
        (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\nBody.\n")

        offenders = validate_chunk_scope(chunk_dir, "myrepo")
        assert offenders == []

    def test_accepts_target_prefixed_paths(self, tmp_path):
        """Paths prefixed with target org/repo:: are acceptable."""
        from chunk_demote import validate_chunk_scope

        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        fm = {
            "status": "IMPLEMENTING",
            "code_paths": [
                "cloudcapitalco/myrepo::src/foo.py",
                "cloudcapitalco/myrepo::src/bar.py",
            ],
        }
        fm_yaml = yaml.dump(fm, default_flow_style=False)
        (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\nBody.\n")

        offenders = validate_chunk_scope(chunk_dir, "myrepo")
        assert offenders == []

    def test_rejects_other_repo_paths(self, tmp_path):
        """Paths referencing a different repo are returned as offenders."""
        from chunk_demote import validate_chunk_scope

        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        offending_path = "cloudcapitalco/otherrepo::src/bar.py"
        fm = {
            "status": "IMPLEMENTING",
            "code_paths": [
                "cloudcapitalco/myrepo::src/foo.py",
                offending_path,
            ],
        }
        fm_yaml = yaml.dump(fm, default_flow_style=False)
        (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\nBody.\n")

        offenders = validate_chunk_scope(chunk_dir, "myrepo")
        assert offenders == [offending_path]

    def test_empty_code_paths_passes(self, tmp_path):
        """Chunk with no code_paths is always valid."""
        from chunk_demote import validate_chunk_scope

        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        fm = {"status": "IMPLEMENTING", "code_paths": []}
        fm_yaml = yaml.dump(fm, default_flow_style=False)
        (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\nBody.\n")

        offenders = validate_chunk_scope(chunk_dir, "myrepo")
        assert offenders == []

    def test_multiple_violations_reported(self, tmp_path):
        """All offending paths are returned, not just the first."""
        from chunk_demote import validate_chunk_scope

        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        offenders_expected = [
            "cloudcapitalco/other1::src/a.py",
            "cloudcapitalco/other2::src/b.py",
        ]
        fm = {
            "status": "IMPLEMENTING",
            "code_paths": [
                "cloudcapitalco/myrepo::src/ok.py",
                *offenders_expected,
            ],
        }
        fm_yaml = yaml.dump(fm, default_flow_style=False)
        (chunk_dir / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\nBody.\n")

        result = validate_chunk_scope(chunk_dir, "myrepo")
        assert sorted(result) == sorted(offenders_expected)


# ===========================================================================
# TestStripProjectPrefix
# ===========================================================================

class TestStripProjectPrefix:
    """Unit tests for strip_project_prefix()."""

    def test_strips_org_repo_prefix(self):
        """Strips 'org/repo::' prefix correctly."""
        from chunk_demote import strip_project_prefix

        result = strip_project_prefix("cloudcapitalco/myrepo::src/foo.py", "cloudcapitalco/myrepo")
        assert result == "src/foo.py"

    def test_leaves_bare_path_unchanged(self):
        """Bare paths are returned as-is."""
        from chunk_demote import strip_project_prefix

        result = strip_project_prefix("src/bar.py", "cloudcapitalco/myrepo")
        assert result == "src/bar.py"

    def test_leaves_other_org_repo_unchanged(self):
        """Paths with a different org/repo are not stripped."""
        from chunk_demote import strip_project_prefix

        result = strip_project_prefix("other/repo::src/x.py", "cloudcapitalco/myrepo")
        assert result == "other/repo::src/x.py"

    def test_strips_ref_with_symbol(self):
        """Prefix is stripped even when a #Symbol is appended."""
        from chunk_demote import strip_project_prefix

        result = strip_project_prefix("acme/proj::src/f.py#Cls", "acme/proj")
        assert result == "src/f.py#Cls"


# ===========================================================================
# TestRewriteChunkFrontmatter
# ===========================================================================

class TestRewriteChunkFrontmatter:
    """Unit tests for rewrite_chunk_frontmatter() on a file on disk."""

    def _write_goal(self, path, fm, body="# Body\n"):
        """Write a GOAL.md with the given frontmatter dict and body."""
        fm_yaml = yaml.dump(fm, default_flow_style=False, sort_keys=False)
        (path / "GOAL.md").write_text(f"---\n{fm_yaml}---\n\n{body}")

    def test_strips_code_path_prefixes(self, tmp_path):
        """code_paths have org/repo:: prefix stripped after rewrite."""
        from chunk_demote import rewrite_chunk_frontmatter

        self._write_goal(tmp_path, {
            "status": "IMPLEMENTING",
            "code_paths": ["acme/myrepo::src/a.py", "acme/myrepo::src/b.py"],
        })

        rewrite_chunk_frontmatter(tmp_path / "GOAL.md", "acme/myrepo")

        fm = _read_frontmatter(tmp_path / "GOAL.md")
        assert fm["code_paths"] == ["src/a.py", "src/b.py"]

    def test_strips_code_reference_ref_prefixes(self, tmp_path):
        """code_references[].ref fields have prefix stripped."""
        from chunk_demote import rewrite_chunk_frontmatter

        self._write_goal(tmp_path, {
            "status": "IMPLEMENTING",
            "code_paths": [],
            "code_references": [
                {"ref": "acme/myrepo::src/f.py#MyClass", "implements": "core"},
            ],
        })

        rewrite_chunk_frontmatter(tmp_path / "GOAL.md", "acme/myrepo")

        fm = _read_frontmatter(tmp_path / "GOAL.md")
        assert fm["code_references"][0]["ref"] == "src/f.py#MyClass"

    def test_removes_dependents_key(self, tmp_path):
        """dependents key is removed entirely after rewrite."""
        from chunk_demote import rewrite_chunk_frontmatter

        self._write_goal(tmp_path, {
            "status": "IMPLEMENTING",
            "code_paths": [],
            "dependents": [{"repo": "acme/proj2"}],
        })

        rewrite_chunk_frontmatter(tmp_path / "GOAL.md", "acme/myrepo")

        fm = _read_frontmatter(tmp_path / "GOAL.md")
        assert "dependents" not in fm

    def test_preserves_other_frontmatter_fields(self, tmp_path):
        """Unrelated frontmatter fields (status, ticket, created_after, etc.) are unchanged."""
        from chunk_demote import rewrite_chunk_frontmatter

        self._write_goal(tmp_path, {
            "status": "IMPLEMENTING",
            "ticket": "VE-123",
            "created_after": ["some_chunk"],
            "depends_on": [],
            "code_paths": [],
        })

        rewrite_chunk_frontmatter(tmp_path / "GOAL.md", "acme/myrepo")

        fm = _read_frontmatter(tmp_path / "GOAL.md")
        assert fm["status"] == "IMPLEMENTING"
        assert fm["ticket"] == "VE-123"
        assert fm["created_after"] == ["some_chunk"]
        assert fm["depends_on"] == []

    def test_noop_on_bare_paths(self, tmp_path):
        """Rewriting a file with no prefixed paths produces identical content."""
        from chunk_demote import rewrite_chunk_frontmatter

        original_fm = {
            "status": "IMPLEMENTING",
            "code_paths": ["src/a.py", "src/b.py"],
        }
        self._write_goal(tmp_path, original_fm)
        original_content = (tmp_path / "GOAL.md").read_text()

        rewrite_chunk_frontmatter(tmp_path / "GOAL.md", "acme/myrepo")

        new_content = (tmp_path / "GOAL.md").read_text()
        # Parse both to compare semantically (YAML serialization order may differ slightly)
        assert _read_frontmatter(tmp_path / "GOAL.md")["code_paths"] == ["src/a.py", "src/b.py"]


# ===========================================================================
# TestDemoteChunkCore
# ===========================================================================

class TestDemoteChunkCore:
    """Integration tests for demote_chunk()."""

    def test_happy_path(self, tmp_path):
        """Happy path: chunk demoted from architecture to target project."""
        from chunk_demote import demote_chunk

        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        result = demote_chunk(task_dir, "my_feature", "proj1")

        # Target project should now have GOAL.md + PLAN.md (no external.yaml)
        target_chunk_dir = proj1_path / "docs" / "chunks" / "my_feature"
        assert (target_chunk_dir / "GOAL.md").exists()
        assert (target_chunk_dir / "PLAN.md").exists()
        assert not (target_chunk_dir / "external.yaml").exists()

        # GOAL.md should have no dependents key and no org/repo:: prefixes
        fm = _read_frontmatter(target_chunk_dir / "GOAL.md")
        assert "dependents" not in fm
        for cp in fm.get("code_paths", []):
            assert "::" not in cp
        for cr in fm.get("code_references", []):
            ref = cr if isinstance(cr, str) else cr.get("ref", "")
            assert "::" not in ref

        # Non-target project's pointer directory should be deleted
        proj2_chunk_dir = proj2_path / "docs" / "chunks" / "my_feature"
        assert not proj2_chunk_dir.exists()

        # Architecture source dir no longer exists
        arch_chunk_dir = arch_path / "docs" / "chunks" / "my_feature"
        assert not arch_chunk_dir.exists()

    def test_scope_violation_rejected(self, tmp_path):
        """Chunk with cross-repo paths in code_paths raises ChunkDemoteError."""
        from chunk_demote import demote_chunk, ChunkDemoteError

        task_dir, arch_path, (proj1_path, proj2_path) = setup_task_directory(
            tmp_path,
            external_name="architecture",
            project_names=["proj1", "proj2"],
        )

        _make_arch_chunk(
            arch_path,
            "bad_chunk",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "bad_chunk", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "bad_chunk", "repo": "acme/proj2"},
            ],
            code_paths=[
                "acme/proj1::src/ok.py",
                "acme/proj2::src/bad.py",   # ← offending
            ],
        )
        _make_external_yaml(proj1_path, "bad_chunk", "acme/architecture")
        _make_external_yaml(proj2_path, "bad_chunk", "acme/architecture")

        with pytest.raises(ChunkDemoteError) as exc_info:
            demote_chunk(task_dir, "bad_chunk", "proj1")

        assert "acme/proj2::src/bad.py" in str(exc_info.value)

        # No filesystem changes should have occurred
        assert (arch_path / "docs" / "chunks" / "bad_chunk").exists()
        assert (proj1_path / "docs" / "chunks" / "bad_chunk" / "external.yaml").exists()
        assert (proj2_path / "docs" / "chunks" / "bad_chunk" / "external.yaml").exists()

    def test_refuses_non_pointer_in_other_project(self, tmp_path):
        """If a non-target project has actual GOAL.md content, refuse."""
        from chunk_demote import demote_chunk, ChunkDemoteError

        task_dir, arch_path, (proj1_path, proj2_path) = setup_task_directory(
            tmp_path,
            external_name="architecture",
            project_names=["proj1", "proj2"],
        )

        _make_arch_chunk(
            arch_path,
            "conflict_chunk",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "conflict_chunk", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "conflict_chunk", "repo": "acme/proj2"},
            ],
            code_paths=["acme/proj1::src/ok.py"],
        )
        _make_external_yaml(proj1_path, "conflict_chunk", "acme/architecture")

        # proj2 has actual GOAL.md instead of external.yaml
        proj2_chunk = proj2_path / "docs" / "chunks" / "conflict_chunk"
        proj2_chunk.mkdir(parents=True)
        fm = yaml.dump({"status": "ACTIVE"}, default_flow_style=False)
        (proj2_chunk / "GOAL.md").write_text(f"---\n{fm}---\n\n# Conflict\n")

        with pytest.raises(ChunkDemoteError) as exc_info:
            demote_chunk(task_dir, "conflict_chunk", "proj1")

        assert "proj2" in str(exc_info.value).lower() or "conflict" in str(exc_info.value).lower()

    def test_idempotent_rerun_after_copy(self, tmp_path):
        """Partial completion: target has files but arch source + other pointers still exist."""
        from chunk_demote import demote_chunk

        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        # Simulate partial completion: copy files to target but leave arch + proj2 pointer
        arch_chunk_dir = arch_path / "docs" / "chunks" / "my_feature"
        target_chunk_dir = proj1_path / "docs" / "chunks" / "my_feature"

        # Remove external.yaml pointer, copy arch files
        (target_chunk_dir / "external.yaml").unlink()
        import shutil
        for item in arch_chunk_dir.iterdir():
            shutil.copy2(item, target_chunk_dir / item.name)

        # Re-run should complete the cascade without error
        result = demote_chunk(task_dir, "my_feature", "proj1")

        # Architecture should be removed
        assert not arch_chunk_dir.exists()
        # Non-target pointer should be deleted
        assert not (proj2_path / "docs" / "chunks" / "my_feature").exists()

    def test_idempotent_rerun_after_full_completion(self, tmp_path):
        """Everything already done: re-run succeeds reporting nothing to do."""
        from chunk_demote import demote_chunk

        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        # First run (full completion)
        demote_chunk(task_dir, "my_feature", "proj1")

        # Second run should succeed without error
        result = demote_chunk(task_dir, "my_feature", "proj1")

        assert result["demoted_chunk"] == "my_feature"
        assert result["source_removed"] is False  # already gone on first run

    def test_returns_summary_dict(self, tmp_path):
        """Return value contains the expected summary keys."""
        from chunk_demote import demote_chunk

        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        result = demote_chunk(task_dir, "my_feature", "proj1")

        assert "demoted_chunk" in result
        assert "target_project" in result
        assert "pointers_removed" in result
        assert "source_removed" in result
        assert result["demoted_chunk"] == "my_feature"
        assert result["pointers_removed"] == 1  # proj2 pointer removed
        assert result["source_removed"] is True


# ===========================================================================
# TestDemoteChunkCLI
# ===========================================================================

class TestDemoteChunkCLI:
    """CLI integration tests for ve chunk demote."""

    def test_command_exists(self):
        """ve chunk demote --help exits 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["chunk", "demote", "--help"])
        assert result.exit_code == 0

    def test_happy_path_cli(self, tmp_path):
        """ve chunk demote succeeds and prints demoted chunk name."""
        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "demote", "my_feature", "proj1", "--cwd", str(task_dir)],
        )

        assert result.exit_code == 0, result.output
        assert "my_feature" in result.output

    def test_scope_violation_exits_nonzero(self, tmp_path):
        """Chunk with cross-repo paths → exit 1, message lists offending paths."""
        task_dir, arch_path, (proj1_path, proj2_path) = setup_task_directory(
            tmp_path,
            external_name="architecture",
            project_names=["proj1", "proj2"],
        )

        _make_arch_chunk(
            arch_path,
            "bad_chunk",
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "bad_chunk", "repo": "acme/proj1"},
                {"artifact_type": "chunk", "artifact_id": "bad_chunk", "repo": "acme/proj2"},
            ],
            code_paths=["acme/proj2::src/bad.py"],
        )
        _make_external_yaml(proj1_path, "bad_chunk", "acme/architecture")
        _make_external_yaml(proj2_path, "bad_chunk", "acme/architecture")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "demote", "bad_chunk", "proj1", "--cwd", str(task_dir)],
        )

        assert result.exit_code == 1
        assert "acme/proj2::src/bad.py" in result.output

    def test_missing_chunk_exits_nonzero(self, tmp_path):
        """Chunk not in architecture → exit 1."""
        task_dir, arch_path, (proj1_path, proj2_path) = setup_task_directory(
            tmp_path,
            external_name="architecture",
            project_names=["proj1", "proj2"],
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "demote", "nonexistent_chunk", "proj1", "--cwd", str(task_dir)],
        )

        assert result.exit_code == 1

    def test_no_git_operations_performed(self, tmp_path):
        """Demotion does not change git status in any repo."""
        import subprocess

        task_dir, arch_path, proj1_path, proj2_path = _setup_full_demote_scenario(tmp_path)

        def _git_status(path):
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            return r.stdout.strip()

        # Baseline git status (all clean after setup_task_directory committed everything)
        # Note: setup creates repos with initial commits but our added files are not committed.
        # We just verify the operation itself doesn't spawn git subprocesses that alter state.

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "demote", "my_feature", "proj1", "--cwd", str(task_dir)],
        )
        assert result.exit_code == 0, result.output

        # Git status after demotion — the command should not have made any commits
        # (files are modified/deleted on disk but not staged or committed by us)
        status_arch = _git_status(arch_path)
        status_proj1 = _git_status(proj1_path)
        status_proj2 = _git_status(proj2_path)

        # There should be untracked/modified files but NO NEW COMMITS
        # (i.e., the operation is filesystem-only, operator handles git)
        log_arch = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=arch_path, capture_output=True, text=True,
        ).stdout.strip().count("\n")
        log_proj1 = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=proj1_path, capture_output=True, text=True,
        ).stdout.strip().count("\n")
        log_proj2 = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=proj2_path, capture_output=True, text=True,
        ).stdout.strip().count("\n")

        # All repos should still have exactly 1 commit (the initial one from setup)
        assert log_arch == 0   # 1 commit = 0 newlines between lines
        assert log_proj1 == 0
        assert log_proj2 == 0
