"""CLI integration tests for ve task init command."""

import subprocess
import tempfile

from ve import cli


def make_ve_initialized_git_repo(path):
    """Helper to create a VE-initialized git repository."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "docs" / "chunks").mkdir(parents=True)


class TestTaskInitCommand:
    """Tests for 've task init' CLI command."""

    def test_task_init_command_exists(self, runner):
        """Verify the task init command is registered."""
        result = runner.invoke(cli, ["task", "init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output or "init" in result.output

    def test_successful_initialization(self, runner):
        """Successful init shows created path and lists repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)
                project = cwd / "proj"
                make_ve_initialized_git_repo(project)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 0
                assert ".ve-task.yaml" in result.output
                assert (cwd / ".ve-task.yaml").exists()

    def test_error_when_external_does_not_exist(self, runner):
        """Error when external directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                project = cwd / "proj"
                make_ve_initialized_git_repo(project)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "ext" in result.output
                assert "does not exist" in result.output

    def test_error_when_project_does_not_exist(self, runner):
        """Error when project directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "proj" in result.output
                assert "does not exist" in result.output

    def test_error_when_external_is_not_git_repo(self, runner):
        """Error when external directory is not a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                external.mkdir()
                (external / "docs" / "chunks").mkdir(parents=True)
                project = cwd / "proj"
                make_ve_initialized_git_repo(project)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "ext" in result.output
                assert "not a git repository" in result.output

    def test_error_when_external_is_not_ve_initialized(self, runner):
        """Error when external directory is not VE-initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                external.mkdir()
                subprocess.run(
                    ["git", "init"], cwd=external, check=True, capture_output=True
                )
                project = cwd / "proj"
                make_ve_initialized_git_repo(project)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "ext" in result.output
                assert "not a Vibe Engineer project" in result.output

    def test_error_when_project_is_not_ve_initialized(self, runner):
        """Error when project directory is not VE-initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)
                project = cwd / "proj"
                project.mkdir()
                subprocess.run(
                    ["git", "init"], cwd=project, check=True, capture_output=True
                )

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "proj" in result.output
                assert "not a Vibe Engineer project" in result.output

    def test_error_when_already_initialized(self, runner):
        """Error when .ve-task.yaml already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                (cwd / ".ve-task.yaml").write_text(
                    "external_chunk_repo: ext\nprojects:\n  - proj\n"
                )
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)
                project = cwd / "proj"
                make_ve_initialized_git_repo(project)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext", "--project", "proj"],
                )

                assert result.exit_code == 1
                assert "already exists" in result.output

    def test_error_when_no_projects_specified(self, runner):
        """Error when no --project flags specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)

                result = runner.invoke(
                    cli,
                    ["task", "init", "--external", "ext"],
                )

                # Click should enforce --project is required, or our validation catches it
                assert result.exit_code != 0

    def test_multiple_project_flags(self, runner):
        """Multiple --project flags work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with runner.isolated_filesystem(temp_dir=tmpdir):
                import pathlib

                cwd = pathlib.Path.cwd()
                external = cwd / "ext"
                make_ve_initialized_git_repo(external)
                proj1 = cwd / "proj1"
                make_ve_initialized_git_repo(proj1)
                proj2 = cwd / "proj2"
                make_ve_initialized_git_repo(proj2)

                result = runner.invoke(
                    cli,
                    [
                        "task",
                        "init",
                        "--external",
                        "ext",
                        "--project",
                        "proj1",
                        "--project",
                        "proj2",
                    ],
                )

                assert result.exit_code == 0
                assert (cwd / ".ve-task.yaml").exists()

                # Verify both projects are in the config
                import yaml

                with open(cwd / ".ve-task.yaml") as f:
                    config = yaml.safe_load(f)
                assert config["projects"] == ["proj1", "proj2"]
