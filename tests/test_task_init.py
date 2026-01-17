"""Tests for TaskInit business logic."""

import subprocess

import pytest

from task_init import TaskInit, TaskInitResult, _resolve_to_org_repo
from task_utils import load_task_config
from conftest import make_ve_initialized_git_repo


class TestTaskInitValidate:
    """Tests for TaskInit.validate() method."""

    def test_returns_error_when_task_directory_already_exists(self, tmp_path):
        """Returns error when .ve-task.yaml already exists."""
        (tmp_path / ".ve-task.yaml").write_text(
            "external_artifact_repo: acme/ext\nprojects:\n  - acme/proj\n"
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
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "does not exist" in errors[0]

    def test_returns_error_when_project_directory_does_not_exist(self, tmp_path):
        """Returns error when project directory does not exist."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")

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
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "not a git repository" in errors[0]

    def test_returns_error_when_project_is_not_git_repo(self, tmp_path):
        """Returns error when project directory is not a git repository."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
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
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/acme/ext.git"],
            cwd=external,
            check=True,
            capture_output=True,
        )
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/ext" in errors[0]
        assert "not a Vibe Engineer project" in errors[0]
        assert "docs/chunks" in errors[0]

    def test_returns_error_when_project_is_not_ve_initialized(self, tmp_path):
        """Returns error when project directory is missing docs/chunks/."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/acme/proj.git"],
            cwd=project,
            check=True,
            capture_output=True,
        )

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "acme/proj" in errors[0]
        assert "not a Vibe Engineer project" in errors[0]
        assert "docs/chunks" in errors[0]

    def test_returns_no_errors_for_valid_setup(self, tmp_path):
        """Returns empty list for valid VE-initialized git directories."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert errors == []

    def test_returns_no_errors_with_multiple_projects(self, tmp_path):
        """Returns empty list when multiple valid projects specified."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1, remote_url="https://github.com/acme/proj1.git")
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2, remote_url="https://github.com/acme/proj2.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        errors = init.validate()

        assert errors == []

    def test_collects_multiple_errors(self, tmp_path):
        """Collects errors for multiple invalid projects."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
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
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "acme" / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        errors = init.validate()

        assert errors == []


class TestTaskInitExecute:
    """Tests for TaskInit.execute() method."""

    def test_creates_ve_task_yaml(self, tmp_path):
        """Creates .ve-task.yaml file in cwd."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()  # Must call validate() first to populate resolved values
        result = init.execute()

        assert (tmp_path / ".ve-task.yaml").exists()
        assert isinstance(result, TaskInitResult)
        assert result.config_path == tmp_path / ".ve-task.yaml"

    def test_yaml_contains_correct_content(self, tmp_path):
        """Created YAML has correct external_artifact_repo and projects."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1, remote_url="https://github.com/acme/proj1.git")
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2, remote_url="https://github.com/acme/proj2.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        init.validate()  # Must call validate() first to populate resolved values
        result = init.execute()

        assert result.external_repo == "acme/ext"
        assert result.projects == ["acme/proj1", "acme/proj2"]

    def test_result_can_be_loaded_by_load_task_config(self, tmp_path):
        """Created file can be loaded by load_task_config()."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()  # Must call validate() first to populate resolved values
        init.execute()

        config = load_task_config(tmp_path)
        assert config.external_artifact_repo == "acme/ext"
        assert config.projects == ["acme/proj"]


# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
class TestTaskInitClaudeMd:
    """Tests for CLAUDE.md generation in task init."""

    def test_creates_claude_md_in_task_directory(self, tmp_path):
        """Creates CLAUDE.md file in task directory."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        assert (tmp_path / "CLAUDE.md").exists()

    def test_claude_md_contains_external_repo(self, tmp_path):
        """CLAUDE.md contains external_artifact_repo from config."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "acme/ext" in content

    def test_claude_md_contains_project_list(self, tmp_path):
        """CLAUDE.md contains project list from config."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1, remote_url="https://github.com/acme/proj1.git")
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2, remote_url="https://github.com/acme/proj2.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        init.validate()
        init.execute()

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "acme/proj1" in content
        assert "acme/proj2" in content

    def test_claude_md_is_rendered_from_template(self, tmp_path):
        """CLAUDE.md is rendered (not a copy of template source)."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        content = (tmp_path / "CLAUDE.md").read_text()
        # Should not contain Jinja2 syntax
        assert "{{" not in content
        assert "{%" not in content
        # Should contain rendered content
        assert "Multi-Project Task" in content


class TestTaskInitCommands:
    """Tests for command template rendering in task init."""

    def test_creates_claude_commands_directory(self, tmp_path):
        """Creates .claude/commands/ directory in task root."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        assert (tmp_path / ".claude" / "commands").exists()
        assert (tmp_path / ".claude" / "commands").is_dir()

    def test_renders_all_command_templates(self, tmp_path):
        """All command templates are rendered to .claude/commands/."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        commands_dir = tmp_path / ".claude" / "commands"
        # Check that key commands are rendered
        assert (commands_dir / "chunk-create.md").exists()
        assert (commands_dir / "chunk-implement.md").exists()
        assert (commands_dir / "chunk-plan.md").exists()
        assert (commands_dir / "chunk-complete.md").exists()
        assert (commands_dir / "narrative-create.md").exists()
        assert (commands_dir / "subsystem-discover.md").exists()
        assert (commands_dir / "investigation-create.md").exists()

    def test_commands_contain_task_context_content(self, tmp_path):
        """Commands contain task-context specific content."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        init.execute()

        # Check chunk-create contains task context
        chunk_create = (tmp_path / ".claude" / "commands" / "chunk-create.md").read_text()
        assert "Task Context:" in chunk_create
        assert "acme/ext" in chunk_create

    def test_commands_contain_project_list_in_task_context(self, tmp_path):
        """Commands with project lists render them correctly."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(proj1, remote_url="https://github.com/acme/proj1.git")
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(proj2, remote_url="https://github.com/acme/proj2.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj1", "acme/proj2"])
        init.validate()
        init.execute()

        # Check chunk-implement contains project list
        chunk_impl = (tmp_path / ".claude" / "commands" / "chunk-implement.md").read_text()
        assert "acme/proj1" in chunk_impl
        assert "acme/proj2" in chunk_impl


class TestTaskInitCreatedFiles:
    """Tests for created_files tracking in TaskInitResult."""

    def test_result_includes_created_files(self, tmp_path):
        """TaskInitResult.created_files lists all created files."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        result = init.execute()

        # Should include .ve-task.yaml
        assert ".ve-task.yaml" in result.created_files
        # Should include CLAUDE.md
        assert "CLAUDE.md" in result.created_files
        # Should include commands
        assert any("chunk-create.md" in f for f in result.created_files)

    def test_created_files_are_relative_paths(self, tmp_path):
        """Created files are relative paths, not absolute."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(external, remote_url="https://github.com/acme/ext.git")
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/acme/proj.git")

        init = TaskInit(cwd=tmp_path, external="acme/ext", projects=["acme/proj"])
        init.validate()
        result = init.execute()

        # All paths should be relative (not start with /)
        for f in result.created_files:
            assert not f.startswith("/"), f"Path {f} should be relative"


class TestResolveToOrgRepo:
    """Tests for _resolve_to_org_repo() function."""

    def test_plain_directory_resolves_to_org_repo(self, tmp_path):
        """Plain directory name resolves to org/repo from git remote."""
        project = tmp_path / "dotter"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/btaylor/dotter.git")

        result = _resolve_to_org_repo(tmp_path, "dotter")
        assert result == "btaylor/dotter"

    def test_existing_org_repo_format_unchanged(self, tmp_path):
        """Input already in org/repo format is still resolved from remote."""
        project = tmp_path / "dotter"
        make_ve_initialized_git_repo(project, remote_url="https://github.com/btaylor/dotter.git")

        # Even though input is "btaylor/dotter", it should resolve by finding the directory
        result = _resolve_to_org_repo(tmp_path, "btaylor/dotter")
        assert result == "btaylor/dotter"

    def test_raises_when_directory_has_no_remote(self, tmp_path):
        """Raises ValueError when directory has no git remote."""
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)  # No remote_url

        with pytest.raises(ValueError) as exc_info:
            _resolve_to_org_repo(tmp_path, "proj")
        assert "no origin remote" in str(exc_info.value).lower()

    def test_works_with_worktree(self, tmp_path, tmp_path_factory):
        """Resolves org/repo from worktree (uses parent repo's remote)."""
        # Create main repo with remote
        main_repo = tmp_path / "main-repo"
        make_ve_initialized_git_repo(main_repo, remote_url="https://github.com/btaylor/dotter.git")

        # Create a branch for worktree
        subprocess.run(
            ["git", "branch", "worktree-branch"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Create worktree in a sibling directory
        worktree_dir = tmp_path / "dotter-worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "worktree-branch"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )
        # Add docs/chunks to worktree to make it VE-initialized
        (worktree_dir / "docs" / "chunks").mkdir(parents=True)

        result = _resolve_to_org_repo(tmp_path, "dotter-worktree")
        assert result == "btaylor/dotter"

    def test_raises_when_directory_does_not_exist(self, tmp_path):
        """Raises ValueError when directory does not exist."""
        with pytest.raises(ValueError) as exc_info:
            _resolve_to_org_repo(tmp_path, "nonexistent")
        assert "does not exist" in str(exc_info.value).lower()


class TestTaskInitLocalPathResolution:
    """Tests for TaskInit resolving local paths to org/repo."""

    def test_plain_directory_names_resolve_in_execute(self, tmp_path):
        """Plain directory names are resolved to org/repo in execute."""
        external = tmp_path / "architecture"
        make_ve_initialized_git_repo(
            external, remote_url="https://github.com/btaylor/architecture.git"
        )
        project1 = tmp_path / "dotter"
        make_ve_initialized_git_repo(
            project1, remote_url="https://github.com/btaylor/dotter.git"
        )
        project2 = tmp_path / "vibe-engineer"
        make_ve_initialized_git_repo(
            project2, remote_url="https://github.com/btaylor/vibe-engineer.git"
        )

        init = TaskInit(
            cwd=tmp_path,
            external="architecture",
            projects=["dotter", "vibe-engineer"],
        )
        errors = init.validate()
        assert errors == []

        result = init.execute()

        # Result should contain resolved org/repo values
        assert result.external_repo == "btaylor/architecture"
        assert result.projects == ["btaylor/dotter", "btaylor/vibe-engineer"]

        # YAML should also contain resolved values
        config = load_task_config(tmp_path)
        assert config.external_artifact_repo == "btaylor/architecture"
        assert config.projects == ["btaylor/dotter", "btaylor/vibe-engineer"]

    def test_error_includes_original_input(self, tmp_path):
        """Error message includes original input when directory has no remote."""
        project = tmp_path / "proj"
        make_ve_initialized_git_repo(project)  # No remote
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(
            external, remote_url="https://github.com/acme/ext.git"
        )

        init = TaskInit(cwd=tmp_path, external="ext", projects=["proj"])
        errors = init.validate()

        assert len(errors) == 1
        assert "proj" in errors[0]

    def test_multiple_projects_all_resolved(self, tmp_path):
        """Multiple projects are all resolved correctly."""
        external = tmp_path / "ext"
        make_ve_initialized_git_repo(
            external, remote_url="https://github.com/org1/ext.git"
        )
        proj1 = tmp_path / "proj1"
        make_ve_initialized_git_repo(
            proj1, remote_url="https://github.com/org2/proj1.git"
        )
        proj2 = tmp_path / "proj2"
        make_ve_initialized_git_repo(
            proj2, remote_url="https://github.com/org3/proj2.git"
        )

        init = TaskInit(cwd=tmp_path, external="ext", projects=["proj1", "proj2"])
        errors = init.validate()
        assert errors == []

        result = init.execute()
        assert result.external_repo == "org1/ext"
        assert result.projects == ["org2/proj1", "org3/proj2"]
