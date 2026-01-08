"""Tests for TaskInit business logic."""

import subprocess

import pytest

from task_init import TaskInit, TaskInitResult
from task_utils import load_task_config


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


class TestTaskInitValidate:
    """Tests for TaskInit.validate() method."""

    def test_returns_error_when_task_directory_already_exists(self, tmp_path):
        """Returns error when .ve-task.yaml already exists."""
        (tmp_path / ".ve-task.yaml").write_text(
            "external_chunk_repo: acme/ext\nprojects:\n  - acme/proj\n"
        )
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "already exists" in errors[0]
        assert ".ve-task.yaml" in errors[0]

    def test_returns_error_when_no_projects_specified(self, tmp_path):
        """Returns error when projects list is empty."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=[])
        errors = init.validate()

        assert len(errors) == 1
        assert "At least one --project is required" in errors[0]

    def test_returns_error_when_external_directory_does_not_exist(self, tmp_path):
        """Returns error when external directory does not exist."""
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "does not exist" in errors[0]

    def test_returns_error_when_project_directory_does_not_exist(self, tmp_path):
        """Returns error when project directory does not exist."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/proj" in errors[0]
        assert "does not exist" in errors[0]

    def test_returns_error_when_external_is_not_git_repo(self, tmp_path):
        """Returns error when external directory is not a git repository."""
        external = tmp_path / "ext"
        external.mkdir()
        (external / "docs" / "chunks").mkdir(parents=True)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "not a git repository" in errors[0]

    def test_returns_error_when_project_is_not_git_repo(self, tmp_path):
        """Returns error when project directory is not a git repository."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        project.mkdir()
        (project / "docs" / "chunks").mkdir(parents=True)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/proj" in errors[0]
        assert "not a git repository" in errors[0]

    def test_returns_error_when_external_is_not_ve_initialized(self, tmp_path):
        """Returns error when external directory is missing docs/chunks/."""
        external = tmp_path / "ext"
        external.mkdir()
        subprocess.run(["git", "init"], cwd=external, check=True, capture_output=True)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "not a Vibe Engineer project" in errors[0]
        assert "docs/chunks" in errors[0]

    def test_returns_error_when_project_is_not_ve_initialized(self, tmp_path):
        """Returns error when project directory is missing docs/chunks/."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/proj" in errors[0]
        assert "not a Vibe Engineer project" in errors[0]
        assert "docs/chunks" in errors[0]

    def test_returns_no_errors_for_valid_setup(self, tmp_path):
        """Returns empty list for valid VE-initialized git directories."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert errors == []

    def test_returns_no_errors_with_multiple_projects(self, tmp_path):
        """Returns empty list when multiple valid projects specified."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1)
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        errors = init.validate()

        assert errors == []

    def test_collects_multiple_errors(self, tmp_path):
        """Collects errors for multiple invalid projects."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        # proj1 doesn't exist, proj2 is not a git repo
        proj2 = tmp_path / "proj2"
        proj2.mkdir()

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        errors = init.validate()

        assert len(errors) == 2
        assert any("acme/proj1" in e and "does not exist" in e for e in errors)
        assert any("acme/proj2" in e and "not a git repository" in e for e in errors)

    def test_resolves_nested_directory_structure(self, tmp_path):
        """Resolves org/repo to nested directory structure when simple not found."""
        # Create nested structure: tmp_path/acme/ext
        external = tmp_path / "acme" / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "acme" / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert errors == []


class TestTaskInitExecute:
    """Tests for TaskInit.execute() method."""

    def test_creates_ve_task_yaml(self, tmp_path):
        """Creates .ve-task.yaml file in cwd."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        result = init.execute()

        assert (tmp_path / ".ve-task.yaml").exists()
        assert isinstance(result, TaskInitResult)
        assert result.config_path == tmp_path / ".ve-task.yaml"

    def test_yaml_contains_correct_content(self, tmp_path):
        """Created YAML has correct external_chunk_repo and projects."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1)
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        result = init.execute()

        assert result.external_repo == "acme/ext"
        assert result.projects == ["acme/proj1", "acme/proj2"]

    def test_result_can_be_loaded_by_load_task_config(self, tmp_path):
        """Created file can be loaded by load_task_config()."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external)
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.execute()

        config = load_task_config(tmp_path)
        assert config.external_chunk_repo == "acme/ext"
        assert config.projects == ["acme/proj"]
