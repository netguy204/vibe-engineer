"""CLI tests for ve external resolve command."""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with one commit."""
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def task_directory(tmp_path, tmp_path_factory):
    """Create a task directory with external repo and project."""
    task_dir = tmp_path

    # Create external chunk repo
    external_repo = tmp_path_factory.mktemp("external")
    subprocess.run(["git", "init"], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Create external chunk in external repo
    external_chunk_dir = external_repo / "docs" / "chunks" / "0001-shared_feature"
    external_chunk_dir.mkdir(parents=True)
    (external_chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# External Goal\n\nThis is the external goal content.")
    (external_chunk_dir / "PLAN.md").write_text("# External Plan\n\nThis is the external plan content.")

    subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Get external repo SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=external_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    external_sha = result.stdout.strip()

    # Symlink external repo into task dir
    (task_dir / "chunks-repo").symlink_to(external_repo)

    # Create project repo
    project_dir = tmp_path_factory.mktemp("service-a")
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    (project_dir / "README.md").write_text("# Service A\n")

    # Create external chunk reference
    chunks_dir = project_dir / "docs" / "chunks" / "0001-shared_feature"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "external.yaml").write_text(
        f"artifact_type: chunk\n"
        f"artifact_id: 0001-shared_feature\n"
        f"repo: acme/chunks-repo\n"
        f"track: main\n"
        f"pinned: {external_sha}\n"
    )

    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )

    # Symlink into task dir
    (task_dir / "service-a").symlink_to(project_dir)

    # Create .ve-task.yaml
    (task_dir / ".ve-task.yaml").write_text(
        "external_artifact_repo: acme/chunks-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
        "project_dir": project_dir,
    }


class TestResolveTaskDirectoryMode:
    """Tests for resolve command in task directory mode."""

    def test_resolve_displays_content(self, task_directory):
        """Resolves and displays external chunk content."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 0
        assert "External Chunk Reference" in result.output
        assert "Repository: acme/chunks-repo" in result.output
        assert "Chunk: 0001-shared_feature" in result.output
        assert "Track: main" in result.output
        assert "External Goal" in result.output
        assert "External Plan" in result.output

    def test_at_pinned_flag(self, task_directory):
        """Shows content at pinned SHA when --at-pinned specified."""
        task_dir = task_directory["task_dir"]
        external_repo = task_directory["external_repo"]
        original_sha = task_directory["external_sha"]

        # Make a new commit to external repo
        external_chunk_dir = external_repo / "docs" / "chunks" / "0001-shared_feature"
        (external_chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# Updated Goal\n")
        subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update"],
            cwd=external_repo,
            check=True,
            capture_output=True,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--at-pinned", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert f"SHA: {original_sha}" in result.output
        assert "External Goal" in result.output
        assert "Updated Goal" not in result.output

    def test_goal_only_flag(self, task_directory):
        """Shows only GOAL.md when --goal-only specified."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--goal-only", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 0
        assert "--- GOAL.md ---" in result.output
        assert "--- PLAN.md ---" not in result.output
        assert "External Goal" in result.output

    def test_plan_only_flag(self, task_directory):
        """Shows only PLAN.md when --plan-only specified."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--plan-only", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 0
        assert "--- GOAL.md ---" not in result.output
        assert "--- PLAN.md ---" in result.output
        assert "External Plan" in result.output

    def test_goal_only_and_plan_only_mutually_exclusive(self, task_directory):
        """Error when both --goal-only and --plan-only specified."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--goal-only", "--plan-only", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    def test_project_filter_in_task_directory(self, task_directory, tmp_path_factory):
        """Disambiguates with --project in task directory mode."""
        task_dir = task_directory["task_dir"]

        # Add another project with same chunk ID
        project_b = tmp_path_factory.mktemp("service-b")
        subprocess.run(["git", "init"], cwd=project_b, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )

        chunks_dir = project_b / "docs" / "chunks" / "0001-shared_feature"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            f"artifact_type: chunk\n"
            f"artifact_id: 0001-shared_feature\n"
            f"repo: acme/chunks-repo\n"
            f"track: main\n"
            f"pinned: {'a' * 40}\n"
        )
        subprocess.run(["git", "add", "."], cwd=project_b, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )

        (task_dir / "service-b").symlink_to(project_b)

        # Update task config
        (task_dir / ".ve-task.yaml").write_text(
            "external_artifact_repo: acme/chunks-repo\n"
            "projects:\n"
            "  - acme/service-a\n"
            "  - acme/service-b\n"
        )

        runner = CliRunner()

        # Without filter should error due to ambiguity
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--project-dir", str(task_dir)],
        )
        assert result.exit_code == 1
        assert "multiple projects" in result.output

        # With filter should succeed
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--project", "acme/service-a", "--project-dir", str(task_dir)],
        )
        assert result.exit_code == 0


class TestResolveSingleRepoMode:
    """Tests for resolve command in single repo mode."""

    def test_resolve_via_cache(self, git_repo, monkeypatch):
        """Resolves external chunk via cache in single repo mode."""
        # Create external chunk reference
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-feature\n"
            "repo: acme/chunks\n"
            "track: main\n"
            "pinned: null\n"
        )

        mock_sha = "a" * 40

        # Mock repo_cache functions
        import external_resolve

        monkeypatch.setattr(
            external_resolve.repo_cache, "ensure_cached", lambda repo: git_repo
        )
        monkeypatch.setattr(
            external_resolve.repo_cache, "resolve_ref", lambda repo, ref: mock_sha
        )
        monkeypatch.setattr(
            external_resolve.repo_cache,
            "get_file_at_ref",
            lambda repo, ref, path: "# Goal content" if "GOAL" in path else "# Plan content",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-external", "--project-dir", str(git_repo)],
        )

        assert result.exit_code == 0
        assert "External Chunk Reference" in result.output
        assert "Repository: acme/chunks" in result.output
        assert "Goal content" in result.output
        assert "Plan content" in result.output

    def test_project_flag_error_outside_task_directory(self, git_repo):
        """Error when --project used outside task directory."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-chunk", "--project", "some-project", "--project-dir", str(git_repo)],
        )

        assert result.exit_code == 1
        assert "--project can only be used in task directory context" in result.output


class TestResolveErrorCases:
    """Tests for error handling in resolve command."""

    def test_error_nonexistent_chunk(self, task_directory):
        """Error for nonexistent chunk."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "9999-nonexistent", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_error_not_external_chunk(self, task_directory):
        """Error when chunk is not an external reference."""
        task_dir = task_directory["task_dir"]
        project_dir = task_directory["project_dir"]

        # Create a normal chunk (with GOAL.md)
        normal_chunk = project_dir / "docs" / "chunks" / "0002-normal"
        normal_chunk.mkdir(parents=True)
        (normal_chunk / "GOAL.md").write_text("# Goal\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0002-normal", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 1
        assert "not an external reference" in result.output

    def test_error_missing_pinned_with_at_pinned(self, task_directory):
        """Error when --at-pinned but no pinned value."""
        task_dir = task_directory["task_dir"]
        project_dir = task_directory["project_dir"]

        # Update external.yaml to have no pinned value
        external_yaml = project_dir / "docs" / "chunks" / "0001-shared_feature" / "external.yaml"
        external_yaml.write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-shared_feature\n"
            "repo: acme/chunks-repo\n"
            "track: main\n"
            "pinned: null\n"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--at-pinned", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 1
        assert "no pinned SHA" in result.output

    def test_handles_missing_plan_md(self, task_directory):
        """Gracefully handles missing PLAN.md."""
        external_repo = task_directory["external_repo"]

        # Remove PLAN.md
        plan_path = external_repo / "docs" / "chunks" / "0001-shared_feature" / "PLAN.md"
        plan_path.unlink()
        subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Remove PLAN.md"],
            cwd=external_repo,
            check=True,
            capture_output=True,
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["external", "resolve", "0001-shared_feature", "--project-dir", str(task_directory["task_dir"])],
        )

        assert result.exit_code == 0
        assert "--- PLAN.md ---" in result.output
        assert "(not found)" in result.output
