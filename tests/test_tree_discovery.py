"""Tests for nearest-enclosing-tree discovery.

These tests exercise the two guarantees the chunk makes:

1. `find_enclosing_tree` answers "which VE tree governs this path?" by walking
   up, so a bare backreference in a source file can be resolved against the
   nearest enclosing tree of *that file* rather than the cwd or the repo root.
2. CLI commands act on the discovered tree, announce the choice when it differs
   from what was asked for, and behave exactly as before in a single-tree
   project.

The fixtures build trees by hand (`docs/trunk/`) rather than using
`make_ve_initialized_git_repo`, which deliberately creates `docs/chunks/` and
friends *without* `docs/trunk/`.
"""
# Chunk: docs/chunks/federation_tree_discovery - Tests for tree discovery and CLI wiring

import click
import pytest

from cli.tree_discovery import install_tree_discovery
from project import find_enclosing_tree, resolve_project_dir
from ve import cli


def _make_tree(path):
    """Create a minimal VE tree (the docs/trunk/ marker plus docs/chunks/)."""
    (path / "docs" / "trunk").mkdir(parents=True, exist_ok=True)
    (path / "docs" / "chunks").mkdir(parents=True, exist_ok=True)
    return path


def _make_chunk(tree, name):
    """Create a listable ACTIVE chunk inside a tree."""
    chunk_dir = tree / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "GOAL.md").write_text(
        "---\n"
        "status: ACTIVE\n"
        "ticket: null\n"
        "parent_chunk: null\n"
        "code_paths: []\n"
        "code_references: []\n"
        "created_after: []\n"
        "---\n\n"
        f"# Chunk Goal\n\n{name}\n"
    )
    return chunk_dir


@pytest.fixture
def nested_trees(tmp_path):
    """A tree inside a tree, with a gap directory between them.

    outer/                      <- tree (docs/trunk/)
    outer/mid/                  <- between the trees, no tree of its own
    outer/mid/inner/            <- tree (docs/trunk/)
    outer/mid/inner/pkg/src/    <- deep inside the inner tree
    """
    outer = _make_tree(tmp_path / "outer")
    mid = outer / "mid"
    mid.mkdir()
    inner = _make_tree(mid / "inner")
    deep = inner / "pkg" / "src"
    deep.mkdir(parents=True)
    return {"outer": outer, "mid": mid, "inner": inner, "deep": deep}


# Chunk: docs/chunks/federation_tree_discovery
class TestFindEnclosingTree:
    """The nearest-enclosing-tree rule."""

    def test_directory_deep_inside_inner_tree_resolves_to_inner_tree(self, nested_trees):
        """A path inside the inner tree resolves to the inner tree, not the outer."""
        assert find_enclosing_tree(nested_trees["deep"]) == nested_trees["inner"]

    def test_file_inside_inner_tree_resolves_to_inner_tree(self, nested_trees):
        """A *file* resolves against the nearest enclosing tree of that file.

        This is the rule bare backreferences follow: the file's tree governs,
        so a `# Subsystem: docs/subsystems/x` comment in this file must not be
        read against the outer tree.
        """
        source = nested_trees["deep"] / "realized.py"
        source.write_text("# Subsystem: docs/subsystems/commitment_baseline\n")
        assert find_enclosing_tree(source) == nested_trees["inner"]

    def test_directory_between_trees_resolves_to_outer_tree(self, nested_trees):
        """A directory below the outer tree but outside the inner one gets the outer."""
        assert find_enclosing_tree(nested_trees["mid"]) == nested_trees["outer"]

    def test_tree_resolves_to_itself(self, nested_trees):
        """A directory that is itself a tree is its own answer."""
        assert find_enclosing_tree(nested_trees["inner"]) == nested_trees["inner"]
        assert find_enclosing_tree(nested_trees["outer"]) == nested_trees["outer"]

    def test_no_enclosing_tree_returns_none(self, tmp_path):
        """The walk stops at the filesystem root and reports failure, not a guess."""
        lonely = tmp_path / "no" / "tree" / "here"
        lonely.mkdir(parents=True)
        assert find_enclosing_tree(lonely) is None

    def test_missing_path_returns_none(self, tmp_path):
        """A path that does not exist has no enclosing tree to report."""
        assert find_enclosing_tree(tmp_path / "ghost" / "gone") is None


# Chunk: docs/chunks/federation_tree_discovery
class TestDiscoveryBoundaries:
    """Discovery stops at addressing boundaries instead of escaping upward."""

    def test_workspace_root_stops_the_walk(self, tmp_path):
        """A tree above the workspace root is not this path's tree.

        The workspace root delimits the federation; escaping past it would
        resolve a member's reference against an unrelated outer project.
        """
        outer = _make_tree(tmp_path / "outer")
        workspace = outer / "workspace"
        workspace.mkdir()
        (workspace / ".ve-workspace.yaml").write_text("members: []\n")
        member = workspace / "packages" / "libs" / "pybusiness"
        member.mkdir(parents=True)

        assert find_enclosing_tree(member) is None

    def test_workspace_root_that_is_a_tree_resolves_to_itself(self, tmp_path):
        """The boundary is inclusive: a workspace root may itself be a tree."""
        workspace = _make_tree(tmp_path / "workspace")
        (workspace / ".ve-workspace.yaml").write_text("members: []\n")
        member = workspace / "packages" / "app"
        member.mkdir(parents=True)

        assert find_enclosing_tree(member) == workspace

    def test_task_directory_stops_the_walk(self, tmp_path):
        """Task directories are a separate addressing regime (cross-repo mode)."""
        outer = _make_tree(tmp_path / "outer")
        task_dir = outer / "task"
        task_dir.mkdir()
        (task_dir / ".ve-task.yaml").write_text("projects: []\n")
        inside = task_dir / "proj"
        inside.mkdir()

        assert find_enclosing_tree(inside) is None

    def test_nearest_tree_wins_over_boundary_above_it(self, nested_trees):
        """A boundary above the nearest tree is irrelevant — the tree is closer."""
        (nested_trees["outer"] / ".ve-workspace.yaml").write_text("members: []\n")
        assert find_enclosing_tree(nested_trees["deep"]) == nested_trees["inner"]


# Chunk: docs/chunks/federation_tree_discovery
class TestResolveProjectDir:
    """The CLI-facing resolution contract."""

    def test_tree_is_used_as_is_without_redirection(self, nested_trees):
        """The single-tree case: no redirect, nothing to announce."""
        resolution = resolve_project_dir(nested_trees["inner"])
        assert resolution.project_dir == nested_trees["inner"]
        assert resolution.redirected is False
        assert resolution.notice() is None

    def test_non_tree_redirects_to_enclosing_tree_and_announces(self, nested_trees):
        """A non-tree directory is redirected, and the choice is reported."""
        resolution = resolve_project_dir(nested_trees["deep"])
        assert resolution.project_dir == nested_trees["inner"]
        assert resolution.redirected is True
        notice = resolution.notice()
        assert notice is not None
        assert str(nested_trees["inner"]) in notice

    def test_no_tree_found_falls_back_to_the_given_directory(self, tmp_path):
        """Discovery never invents a failure: with no tree, behavior is unchanged."""
        lonely = tmp_path / "lonely"
        lonely.mkdir()
        resolution = resolve_project_dir(lonely)
        assert resolution.project_dir == lonely
        assert resolution.redirected is False
        assert resolution.notice() is None


# Chunk: docs/chunks/federation_tree_discovery
class TestCliUsesDiscovery:
    """CLI commands act on the discovered tree, not the literal argument."""

    @pytest.fixture
    def populated_trees(self, nested_trees):
        _make_chunk(nested_trees["outer"], "outer_chunk")
        _make_chunk(nested_trees["inner"], "inner_chunk")
        return nested_trees

    def test_command_deep_in_inner_tree_lists_inner_chunks(self, runner, populated_trees):
        """The failure this chunk kills: landing in a real-but-wrong tree."""
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(populated_trees["deep"])]
        )
        assert result.exit_code == 0
        assert "inner_chunk" in result.output
        assert "outer_chunk" not in result.output

    def test_redirection_is_announced(self, runner, populated_trees):
        """Misrouting is never silent: one line names the selected tree."""
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(populated_trees["deep"])]
        )
        assert str(populated_trees["inner"]) in result.stderr

    def test_directory_between_trees_lists_outer_chunks(self, runner, populated_trees):
        """A directory outside the inner tree belongs to the outer tree."""
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(populated_trees["mid"])]
        )
        assert result.exit_code == 0
        assert "outer_chunk" in result.output
        assert "inner_chunk" not in result.output

    def test_tree_argument_is_not_announced(self, runner, populated_trees):
        """Single-tree projects see no new output at all."""
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(populated_trees["inner"])]
        )
        assert result.exit_code == 0
        assert "inner_chunk" in result.output
        assert "Using VE tree" not in result.stderr

    def test_directory_with_no_enclosing_tree_is_unchanged(self, runner, tmp_path):
        """No tree above: the command runs against the given directory as before."""
        lonely = tmp_path / "lonely"
        (lonely / "docs" / "chunks").mkdir(parents=True)
        result = runner.invoke(cli, ["chunk", "list", "--project-dir", str(lonely)])
        assert "No chunks found" in result.output


# Chunk: docs/chunks/federation_tree_discovery
class TestInstaller:
    """The single wiring point covers the whole CLI and can be re-run safely."""

    def _project_dir_params(self, group, prefix=""):
        """Every project_dir parameter in the command tree, groups included."""
        for name, command in group.commands.items():
            for param in command.params:
                if param.name == "project_dir":
                    yield f"{prefix}{name}", param
            if isinstance(command, click.Group):
                yield from self._project_dir_params(command, f"{prefix}{name} ")

    def test_every_project_dir_option_resolves_except_exempt_commands(self):
        """Discovery is not opt-in per command: the whole CLI gets it at once."""
        unwired = [
            path
            for path, param in self._project_dir_params(cli)
            if not getattr(param, "_ve_tree_discovery_installed", False)
        ]
        assert unwired == ["init"]

    def test_reinstalling_does_not_double_wrap(self):
        """Idempotent: a second install leaves existing callbacks untouched."""
        before = {path: param.callback for path, param in self._project_dir_params(cli)}
        install_tree_discovery(cli)
        after = {path: param.callback for path, param in self._project_dir_params(cli)}
        assert before == after


# Chunk: docs/chunks/federation_tree_discovery
class TestInitIsExemptFromDiscovery:
    """`ve init` creates a tree, so it must never walk up to an existing one."""

    def test_init_inside_a_tree_initializes_the_given_directory(self, runner, nested_trees):
        fresh = nested_trees["mid"] / "fresh_package"
        fresh.mkdir()

        result = runner.invoke(cli, ["init", "--project-dir", str(fresh)])
        assert result.exit_code == 0
        assert (fresh / "docs" / "trunk" / "GOAL.md").exists()

    def test_init_does_not_report_a_redirect(self, runner, nested_trees):
        fresh = nested_trees["mid"] / "another_package"
        fresh.mkdir()

        result = runner.invoke(cli, ["init", "--project-dir", str(fresh)])
        assert "Using VE tree" not in result.stderr
