"""Tests for pointer-only package scaffolding.

# Chunk: docs/chunks/federation_template_pointers - Scaffolding registers membership
# instead of minting a namespace.

Every test here answers one of the chunk's success criteria: a scaffolded package
carries interest pointers and no trunk, is registered in the workspace manifest, is
*not* a governing tree for bare-reference resolution, and its rendered AGENTS.md
says where the docs that govern it actually live.
"""

import pathlib

import pytest

import project as project_module
import workspace as workspace_module
from conftest import make_ve_tree, make_workspace
from external_refs import load_external_ref
from package_scaffold import (
    InterestSpecError,
    PackageScaffold,
    parse_interest,
)
from project import Project
from workspace import load_workspace


INTEREST = "pybusiness::docs/subsystems/commitment_baseline: Charts render realized savings"


def _owner_artifact(root, artifact_type="subsystems", name="commitment_baseline"):
    """Give the pybusiness member an artifact worth pointing at."""
    target = root / "packages/libs/pybusiness/docs" / artifact_type / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "OVERVIEW.md").write_text("# Commitment baseline\n")
    return target


@pytest.fixture
def workspace_root(tmp_path):
    """A workspace whose root is not itself a VE tree."""
    root = tmp_path / "platform"
    make_workspace(root, {"pybusiness": "packages/libs/pybusiness"})
    _owner_artifact(root)
    return root


@pytest.fixture
def governed_workspace_root(workspace_root):
    """The same workspace, with a governing tree at the root."""
    make_ve_tree(workspace_root)
    return workspace_root


# ---------------------------------------------------------------------------
# Interest spec grammar
# ---------------------------------------------------------------------------


class TestParseInterest:
    """The `<member>::docs/<type>/<id>[: why]` grammar."""

    def test_parses_member_artifact_and_why(self):
        spec = parse_interest(INTEREST)
        assert spec.member == "pybusiness"
        assert spec.artifact == "docs/subsystems/commitment_baseline"
        assert spec.why == "Charts render realized savings"

    def test_why_is_optional(self):
        spec = parse_interest("pybusiness::docs/chunks/rsv2_model")
        assert spec.member == "pybusiness"
        assert spec.why is None

    def test_why_may_contain_colons(self):
        spec = parse_interest("pybusiness::docs/chunks/x: needed for: the split")
        assert spec.why == "needed for: the split"

    def test_unqualified_spec_is_rejected(self):
        with pytest.raises(InterestSpecError) as exc:
            parse_interest("docs/subsystems/commitment_baseline")
        assert "::" in str(exc.value)

    def test_org_repo_qualifier_is_rejected(self):
        """`org/repo::` is a cross-repo qualifier, not a workspace member."""
        with pytest.raises(InterestSpecError) as exc:
            parse_interest("acme/platform::docs/chunks/x")
        assert "member" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Pointer-only default
# ---------------------------------------------------------------------------


class TestPointerOnlyScaffold:
    """Criterion: docs contains only pointers; the manifest is updated."""

    def test_writes_a_peer_pointer_carrying_the_why_note(self, workspace_root):
        package = workspace_root / "apps/viz"
        scaffold = PackageScaffold(path=package, interests=[INTEREST])

        assert scaffold.validate() == []
        scaffold.execute()

        ref = load_external_ref(package / "docs/subsystems/commitment_baseline")
        assert ref.tree == "pybusiness"
        assert ref.artifact_id == "commitment_baseline"
        assert ref.why == "Charts render realized savings"

    def test_mints_no_namespace(self, workspace_root):
        """No trunk, and no artifact directory that holds no pointer."""
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        assert not (package / "docs/trunk").exists()
        assert [p.name for p in (package / "docs").iterdir()] == ["subsystems"]

    def test_registers_the_package_as_a_workspace_member(self, workspace_root):
        package = workspace_root / "apps/viz"
        result = PackageScaffold(path=package, interests=[INTEREST]).execute()

        assert result.registered is True
        assert result.name == "viz"

        reloaded = load_workspace(workspace_root)
        assert reloaded.manifest.get("viz").path == "apps/viz"
        assert reloaded.resolve("viz") == package

    def test_explicit_name_overrides_the_directory_name(self, workspace_root):
        package = workspace_root / "apps/viz"
        result = PackageScaffold(path=package, name="visualization", interests=[INTEREST]).execute()

        assert result.name == "visualization"
        assert load_workspace(workspace_root).manifest.get("visualization") is not None

    def test_registered_package_is_a_legal_member_tree(self, workspace_root):
        """A pointer-only tree satisfies the permissive membership predicate."""
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        assert workspace_module.validate_member_paths(load_workspace(workspace_root)) == []

    def test_missing_why_warns_without_failing(self, workspace_root):
        package = workspace_root / "apps/viz"
        result = PackageScaffold(
            path=package, interests=["pybusiness::docs/subsystems/commitment_baseline"]
        ).execute()

        assert result.registered is True
        assert any("why" in warning for warning in result.warnings)

    def test_several_interests_each_get_a_pointer(self, workspace_root):
        _owner_artifact(workspace_root, "chunks", "rsv2_model")
        package = workspace_root / "apps/viz"

        PackageScaffold(
            path=package,
            interests=[INTEREST, "pybusiness::docs/chunks/rsv2_model: consumes the model"],
        ).execute()

        assert load_external_ref(package / "docs/chunks/rsv2_model").tree == "pybusiness"
        assert load_external_ref(package / "docs/subsystems/commitment_baseline").tree == "pybusiness"


# ---------------------------------------------------------------------------
# Registration behavior outside a workspace
# ---------------------------------------------------------------------------


class TestRegistrationWithoutManifest:
    """Criterion: skips registration cleanly when there is no manifest."""

    def test_full_tree_scaffold_outside_a_workspace_still_works(self, tmp_path):
        package = tmp_path / "solo"
        scaffold = PackageScaffold(path=package, full_tree=True)

        assert scaffold.validate() == []
        result = scaffold.execute()

        assert (package / "docs/trunk/GOAL.md").exists()
        assert result.registered is False
        assert result.workspace_root is None

    def test_interest_edges_require_a_manifest(self, tmp_path):
        """A `tree:` pointer names a member, so there must be a manifest to name."""
        scaffold = PackageScaffold(path=tmp_path / "solo", interests=[INTEREST])
        errors = scaffold.validate()

        assert any(".ve-workspace.yaml" in error for error in errors)
        assert not (tmp_path / "solo").exists()


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


class TestScaffoldRefusals:
    """Nothing is written unless the whole request is valid."""

    def test_a_package_with_no_interests_needs_no_docs_tree(self, workspace_root):
        scaffold = PackageScaffold(path=workspace_root / "apps/viz")
        errors = scaffold.validate()

        assert errors
        assert any("--interest" in error and "--full-tree" in error for error in errors)
        assert not (workspace_root / "apps/viz").exists()

    def test_unknown_member_is_rejected_with_the_registered_names(self, workspace_root):
        scaffold = PackageScaffold(
            path=workspace_root / "apps/viz",
            interests=["pybiz::docs/subsystems/commitment_baseline: typo"],
        )
        errors = scaffold.validate()

        assert any("pybiz" in error and "pybusiness" in error for error in errors)

    def test_pointer_at_a_nonexistent_artifact_is_rejected(self, workspace_root):
        """Born-dangling refs leave no deletion event; catch them at creation."""
        scaffold = PackageScaffold(
            path=workspace_root / "apps/viz",
            interests=["pybusiness::docs/subsystems/run_rate_split: never existed"],
        )
        errors = scaffold.validate()

        assert any("run_rate_split" in error for error in errors)
        assert not (workspace_root / "apps/viz").exists()

    def test_duplicate_member_name_is_rejected_with_the_name_flag(self, workspace_root):
        (workspace_root / "apps/pybusiness").mkdir(parents=True)
        scaffold = PackageScaffold(
            path=workspace_root / "apps/pybusiness", interests=[INTEREST]
        )
        errors = scaffold.validate()

        assert any("--name" in error for error in errors)

    def test_rescaffolding_a_registered_package_points_at_the_right_command(
        self, workspace_root
    ):
        """Adding an edge to a package that already exists is a different job."""
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        errors = PackageScaffold(path=package, interests=[INTEREST]).validate()

        assert any("already registered as member 'viz'" in error for error in errors)
        assert any("ve external point" in error for error in errors)

    def test_existing_governing_tree_is_rejected(self, workspace_root):
        package = make_ve_tree(workspace_root / "apps/viz")
        errors = PackageScaffold(path=pathlib.Path(package), interests=[INTEREST]).validate()

        assert any("docs/trunk" in error for error in errors)

    def test_package_outside_the_workspace_is_rejected(self, workspace_root, tmp_path):
        scaffold = PackageScaffold(path=tmp_path / "elsewhere", interests=[INTEREST])
        errors = scaffold.validate()

        assert errors


# ---------------------------------------------------------------------------
# Full-tree opt-in
# ---------------------------------------------------------------------------


class TestFullTreeOptIn:
    """Criterion: the opt-in flag creates a full tree and registers it."""

    def test_creates_a_governing_tree_and_registers_it(self, workspace_root):
        package = workspace_root / "packages/libs/newlib"
        result = PackageScaffold(path=package, full_tree=True).execute()

        assert (package / "docs/trunk/GOAL.md").exists()
        assert (package / "docs/chunks").is_dir()
        assert result.registered is True
        assert load_workspace(workspace_root).manifest.get("newlib").path == "packages/libs/newlib"

    def test_full_tree_may_also_carry_interest_edges(self, workspace_root):
        package = workspace_root / "packages/libs/newlib"
        PackageScaffold(path=package, full_tree=True, interests=[INTEREST]).execute()

        assert (package / "docs/trunk/GOAL.md").exists()
        assert load_external_ref(package / "docs/subsystems/commitment_baseline").tree == "pybusiness"


# ---------------------------------------------------------------------------
# Resolution: a pointer-only tree is not a governing tree
# ---------------------------------------------------------------------------


class TestPointerOnlyTreeResolution:
    """Criterion: discovery does not treat a pointer-only tree as governing."""

    def test_bare_refs_in_the_package_resolve_upward(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        source_file = package / "src/charts.py"
        assert project_module.find_enclosing_tree(source_file) == governed_workspace_root

    def test_the_package_is_a_member_but_not_a_governing_tree(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        assert workspace_module.is_ve_tree(package) is True
        assert project_module.is_ve_tree(package) is False

    def test_commands_run_in_the_package_redirect_to_the_governing_tree(
        self, governed_workspace_root
    ):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        resolution = project_module.resolve_project_dir(package)
        assert resolution.project_dir == governed_workspace_root
        assert resolution.redirected is True

    def test_without_a_governing_tree_resolution_returns_no_guess(self, workspace_root):
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        assert project_module.find_enclosing_tree(package / "src/charts.py") is None

    def test_the_packages_own_pointers_still_resolve(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        ref = load_external_ref(package / "docs/subsystems/commitment_baseline")
        ws = load_workspace(package)
        target = ws.resolve(ref.tree) / "docs/subsystems" / ref.artifact_id
        assert (target / "OVERVIEW.md").exists()


# ---------------------------------------------------------------------------
# Rendered agent instructions
# ---------------------------------------------------------------------------


class TestRenderedAgentInstructions:
    """Criterion: AGENTS.md says where the governing docs live and how to opt in."""

    def test_names_the_governing_tree_and_its_trunk(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        content = (package / "AGENTS.md").read_text()
        assert "../../docs/trunk/GOAL.md" in content
        assert "nearest enclosing" in content.lower()

    def test_records_the_intent_the_package_consumes(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        content = (package / "AGENTS.md").read_text()
        assert "pybusiness::docs/subsystems/commitment_baseline" in content
        assert "Charts render realized savings" in content

    def test_explains_how_to_opt_into_a_full_tree(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        content = (package / "AGENTS.md").read_text()
        assert "ve init" in content
        assert "addressing root" in content

    def test_says_refs_must_be_qualified_when_no_tree_governs_the_package(self, workspace_root):
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        content = (package / "AGENTS.md").read_text()
        assert "No VE tree governs this package" in content
        assert "pybusiness::docs/" in content

    def test_is_rendered_as_valid_markdown(self, governed_workspace_root):
        """Template whitespace control: the managed block opens the file, and the
        interest table has no blank line splitting it in half."""
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        lines = (package / "AGENTS.md").read_text().splitlines()
        assert lines[0] == "<!-- VE:MANAGED:START -->"
        separator = lines.index("|---------------|----------|-----|")
        assert lines[separator + 1].startswith("| `docs/subsystems/commitment_baseline`")

    def test_claude_md_is_a_symlink_to_agents_md(self, workspace_root):
        package = workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        claude = package / "CLAUDE.md"
        assert claude.is_symlink()
        assert claude.resolve() == (package / "AGENTS.md").resolve()

    def test_opting_into_a_full_tree_replaces_the_managed_block(self, governed_workspace_root):
        """The pointer-only text is inside VE markers, so `ve init` supersedes it."""
        package = governed_workspace_root / "apps/viz"
        PackageScaffold(path=package, interests=[INTEREST]).execute()

        Project(package).init()

        content = (package / "AGENTS.md").read_text()
        assert "# Vibe Engineering Workflow" in content
        assert "pointer-only" not in content

    def test_full_tree_package_gets_the_standard_project_instructions(self, workspace_root):
        package = workspace_root / "packages/libs/newlib"
        PackageScaffold(path=package, full_tree=True).execute()

        content = (package / "AGENTS.md").read_text()
        assert "# Vibe Engineering Workflow" in content
        assert "pointer-only" not in content


# ---------------------------------------------------------------------------
# `ve init` advisory
# ---------------------------------------------------------------------------


class TestInitWorkspaceAdvisory:
    """Minting a namespace inside a workspace is never silent."""

    def test_init_inside_a_workspace_warns_about_the_new_addressing_root(
        self, governed_workspace_root
    ):
        package = governed_workspace_root / "apps/viz"
        package.mkdir(parents=True)

        result = Project(package).init()

        assert any("addressing root" in warning for warning in result.warnings)
        assert any("ve package scaffold" in warning for warning in result.warnings)

    def test_init_advisory_names_the_registration_command(self, governed_workspace_root):
        package = governed_workspace_root / "apps/viz"
        package.mkdir(parents=True)

        result = Project(package).init()

        assert any("ve workspace add" in warning for warning in result.warnings)

    def test_single_repo_init_is_unchanged(self, tmp_path):
        result = Project(tmp_path).init()

        assert result.warnings == []
        assert (tmp_path / "docs/trunk/GOAL.md").exists()

    def test_reinit_of_an_existing_tree_does_not_warn(self, governed_workspace_root):
        package = make_ve_tree(governed_workspace_root / "packages/libs/pybusiness")

        result = Project(pathlib.Path(package)).init()

        assert not any("addressing root" in warning for warning in result.warnings)
