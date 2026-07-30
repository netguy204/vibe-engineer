"""CLI tests for `ve package scaffold`.

# Chunk: docs/chunks/federation_template_pointers - Operator surface a package
# template calls instead of shipping a docs tree of its own.
"""

import pytest

from conftest import make_ve_tree, make_workspace
from ve import cli
from workspace import load_workspace


INTEREST = "pybusiness::docs/subsystems/commitment_baseline: Charts render realized savings"


@pytest.fixture
def workspace_root(tmp_path):
    root = tmp_path / "platform"
    make_workspace(root, {"pybusiness": "packages/libs/pybusiness"})
    make_ve_tree(root)
    target = root / "packages/libs/pybusiness/docs/subsystems/commitment_baseline"
    target.mkdir(parents=True)
    (target / "OVERVIEW.md").write_text("# Commitment baseline\n")
    return root


class TestPackageScaffoldCommand:
    def test_command_is_registered(self, runner):
        result = runner.invoke(cli, ["package", "scaffold", "--help"])
        assert result.exit_code == 0
        assert "pointer" in result.output.lower()

    def test_reports_the_pointer_and_the_registration(self, runner, workspace_root):
        package = workspace_root / "apps/viz"
        result = runner.invoke(
            cli, ["package", "scaffold", str(package), "--interest", INTEREST]
        )

        assert result.exit_code == 0, result.output
        assert "docs/subsystems/commitment_baseline/external.yaml" in result.output
        assert "tree:pybusiness" in result.output
        assert "viz" in result.output
        assert load_workspace(workspace_root).manifest.get("viz") is not None

    def test_says_when_registration_is_skipped(self, runner, tmp_path):
        package = tmp_path / "solo"
        result = runner.invoke(cli, ["package", "scaffold", str(package), "--full-tree"])

        assert result.exit_code == 0, result.output
        assert ".ve-workspace.yaml" in result.output
        assert (package / "docs/trunk/GOAL.md").exists()

    def test_refuses_a_package_with_nothing_to_point_at(self, runner, workspace_root):
        package = workspace_root / "apps/viz"
        result = runner.invoke(cli, ["package", "scaffold", str(package)])

        assert result.exit_code == 1
        assert "--full-tree" in result.output
        assert not package.exists()

    def test_reports_an_unknown_member(self, runner, workspace_root):
        result = runner.invoke(
            cli,
            [
                "package",
                "scaffold",
                str(workspace_root / "apps/viz"),
                "--interest",
                "pybiz::docs/subsystems/commitment_baseline: typo",
            ],
        )

        assert result.exit_code == 1
        assert "pybusiness" in result.output

    def test_full_tree_opt_in_reports_the_trunk(self, runner, workspace_root):
        package = workspace_root / "packages/libs/newlib"
        result = runner.invoke(
            cli, ["package", "scaffold", str(package), "--full-tree"]
        )

        assert result.exit_code == 0, result.output
        assert "docs/trunk/GOAL.md" in result.output
        assert load_workspace(workspace_root).manifest.get("newlib") is not None

    def test_name_option_sets_the_member_name(self, runner, workspace_root):
        result = runner.invoke(
            cli,
            [
                "package",
                "scaffold",
                str(workspace_root / "apps/viz"),
                "--name",
                "visualization",
                "--interest",
                INTEREST,
            ],
        )

        assert result.exit_code == 0, result.output
        assert load_workspace(workspace_root).manifest.get("visualization") is not None

    def test_missing_why_is_reported_as_a_warning(self, runner, workspace_root):
        result = runner.invoke(
            cli,
            [
                "package",
                "scaffold",
                str(workspace_root / "apps/viz"),
                "--interest",
                "pybusiness::docs/subsystems/commitment_baseline",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "why" in result.output.lower()

    def test_malformed_interest_spec_is_reported(self, runner, workspace_root):
        result = runner.invoke(
            cli,
            [
                "package",
                "scaffold",
                str(workspace_root / "apps/viz"),
                "--interest",
                "docs/subsystems/commitment_baseline",
            ],
        )

        assert result.exit_code == 1
        assert "::" in result.output
