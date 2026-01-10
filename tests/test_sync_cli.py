"""Tests for ve sync CLI command."""

import subprocess

import pytest
import yaml
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


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
    """Create a task directory with external repo and projects."""
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
    (external_repo / "README.md").write_text("# External chunks\n")
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

    # Create project repos
    for project_name in ["service-a", "service-b"]:
        project_dir = tmp_path_factory.mktemp(project_name)
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
        (project_dir / "README.md").write_text(f"# {project_name}\n")
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )

        # Symlink into task dir
        (task_dir / project_name).symlink_to(project_dir)

        # Create external chunk reference with outdated SHA
        chunks_dir = project_dir / "docs" / "chunks" / "0001-shared_feature"
        chunks_dir.mkdir(parents=True)
        outdated_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: acme/chunks-repo\n"
            f"chunk: 0001-shared_feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"
        )

    # Create .ve-task.yaml
    (task_dir / ".ve-task.yaml").write_text(
        "external_chunk_repo: acme/chunks-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
        "  - acme/service-b\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
    }


class TestSyncCommand:
    """Tests for ve sync command."""

    def test_sync_task_directory_outputs_results(self, runner, task_directory):
        """Outputs formatted results for task directory sync."""
        task_dir = task_directory["task_dir"]

        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "service-a" in result.output
        assert "service-b" in result.output
        assert "0001-shared_feature" in result.output
        assert "Updated" in result.output

    def test_sync_shows_summary_count(self, runner, task_directory):
        """Shows summary count of updated references."""
        task_dir = task_directory["task_dir"]

        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "Updated 2 of 2" in result.output

    def test_sync_dry_run_output(self, runner, task_directory):
        """Dry run shows [dry-run] prefix and 'would update' language."""
        task_dir = task_directory["task_dir"]

        result = runner.invoke(cli, ["sync", "--dry-run", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "[dry-run]" in result.output.lower() or "would update" in result.output.lower()

    def test_sync_dry_run_does_not_modify(self, runner, task_directory):
        """Dry run does not modify files."""
        task_dir = task_directory["task_dir"]

        runner.invoke(cli, ["sync", "--dry-run", "--project-dir", str(task_dir)])

        # Verify files unchanged
        service_a_yaml = (
            task_dir
            / "service-a"
            / "docs"
            / "chunks"
            / "0001-shared_feature"
            / "external.yaml"
        )
        content = yaml.safe_load(service_a_yaml.read_text())
        assert content["pinned"] == "0" * 40

    def test_sync_project_filter(self, runner, task_directory):
        """--project filter only syncs specified projects."""
        task_dir = task_directory["task_dir"]

        result = runner.invoke(
            cli,
            ["sync", "--project", "acme/service-a", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "service-a" in result.output
        # service-b should not appear in results
        assert "Updated 1 of 1" in result.output

    def test_sync_chunk_filter(self, runner, task_directory):
        """--chunk filter only syncs specified chunks."""
        task_dir = task_directory["task_dir"]

        result = runner.invoke(
            cli,
            ["sync", "--chunk", "0001-shared_feature", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "0001-shared_feature" in result.output

    def test_sync_project_filter_error_outside_task_dir(self, runner, git_repo):
        """--project filter errors when used outside task directory."""
        result = runner.invoke(
            cli,
            ["sync", "--project", "acme/service-a", "--project-dir", str(git_repo)],
        )

        assert result.exit_code != 0
        assert "project" in result.output.lower() and "task" in result.output.lower()

    def test_sync_already_current(self, runner, task_directory):
        """Shows 'already current' when nothing to update."""
        task_dir = task_directory["task_dir"]

        # First sync
        runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        # Second sync
        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "Updated 0 of 2" in result.output or "already current" in result.output.lower()

    def test_sync_no_external_refs(self, runner, git_repo):
        """Shows message when no external refs found."""
        result = runner.invoke(cli, ["sync", "--project-dir", str(git_repo)])

        assert result.exit_code == 0
        assert "no external" in result.output.lower()

    def test_sync_with_errors_nonzero_exit(self, runner, task_directory):
        """Non-zero exit code when errors occurred."""
        task_dir = task_directory["task_dir"]

        # Make one external.yaml point to non-existent repo
        service_b_yaml = (
            task_dir
            / "service-b"
            / "docs"
            / "chunks"
            / "0001-shared_feature"
            / "external.yaml"
        )
        outdated_sha = "0" * 40
        service_b_yaml.write_text(
            f"repo: nonexistent/repo\n"
            f"chunk: 0001-feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"
        )

        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        # Should still complete but with non-zero exit
        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestSyncCommandSingleRepo:
    """Tests for ve sync in single repo mode."""

    def test_sync_single_repo(self, runner, git_repo, monkeypatch):
        """Syncs external refs in single repo mode."""
        import sync

        # Create external reference
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        old_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: octocat/Hello-World\n"
            f"chunk: 0001-feature\n"
            f"track: master\n"
            f"pinned: '{old_sha}'\n"
        )

        # Mock repo_cache.resolve_ref
        mock_sha = "a" * 40
        monkeypatch.setattr(sync.repo_cache, "resolve_ref", lambda *args, **kwargs: mock_sha)

        result = runner.invoke(cli, ["sync", "--project-dir", str(git_repo)])

        assert result.exit_code == 0
        assert "0001-external" in result.output
        assert "Updated 1 of 1" in result.output
