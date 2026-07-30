"""Tests for the workspace manifest model, loader, scan, and `ve workspace` CLI.

# Chunk: docs/chunks/federation_workspace_manifest - Workspace manifest tests
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from click.testing import CliRunner
from pydantic import ValidationError

from models.workspace import WorkspaceManifest, WorkspaceMember
from ve import cli
from workspace import (
    WORKSPACE_MANIFEST_NAME,
    Workspace,
    WorkspaceManifestError,
    WorkspaceNotFoundError,
    find_workspace_root,
    has_trunk,
    is_ve_tree,
    load_workspace,
    scan_for_trees,
    suggest_member_names,
    validate_member_paths,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_tree(path: pathlib.Path, trunk: bool = True, artifacts=("chunks",)) -> pathlib.Path:
    """Create a VE tree at path.

    Args:
        path: Directory that becomes the tree root.
        trunk: Whether to create docs/trunk/ (with a GOAL.md).
        artifacts: Artifact directory names to create under docs/.
    """
    docs = path / "docs"
    if trunk:
        (docs / "trunk").mkdir(parents=True, exist_ok=True)
        (docs / "trunk" / "GOAL.md").write_text("# Goal\n")
    for name in artifacts:
        (docs / name).mkdir(parents=True, exist_ok=True)
    return path


def make_pointer_tree(path: pathlib.Path, artifact: str = "borrowed") -> pathlib.Path:
    """Create a pointer-only tree: an external.yaml chunk stub and no trunk."""
    chunk_dir = path / "docs" / "chunks" / artifact
    chunk_dir.mkdir(parents=True, exist_ok=True)
    (chunk_dir / "external.yaml").write_text(
        "artifact_type: chunk\nartifact_id: borrowed\nrepo: acme/hub\n"
    )
    return path


def write_workspace(root: pathlib.Path, members: dict[str, str]) -> pathlib.Path:
    """Write a .ve-workspace.yaml with the given name -> path mapping."""
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / WORKSPACE_MANIFEST_NAME
    manifest.write_text(yaml.safe_dump({"members": dict(members)}, sort_keys=False))
    return manifest


def make_workspace(root: pathlib.Path, members: dict[str, str]) -> pathlib.Path:
    """Create member trees on disk and a manifest registering them."""
    for rel in members.values():
        make_tree(root / rel)
    write_workspace(root, members)
    return root


def read_members(root: pathlib.Path) -> dict[str, str]:
    """Read the members mapping straight off disk."""
    data = yaml.safe_load((root / WORKSPACE_MANIFEST_NAME).read_text())
    return data["members"] or {}


# ---------------------------------------------------------------------------
# Member name grammar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_name",
    [
        "Pybusiness",  # uppercase is out of grammar
        "pkg/lib",  # slash would collide with org/repo qualifiers
        "a::b",  # :: is the qualifier delimiter itself
        "",  # empty
        "has space",
        "dots.not.allowed",
    ],
)
def test_member_name_grammar_rejects(bad_name):
    """Names outside [a-z0-9_-]+ are rejected, so `<member>::` stays unambiguous."""
    with pytest.raises(ValidationError):
        WorkspaceMember(name=bad_name, path="packages/thing")


def test_member_name_rejection_message_calls_out_qualifier_characters():
    """The error tells the operator why / and :: are forbidden."""
    with pytest.raises(ValidationError) as exc:
        WorkspaceMember(name="acme/pybusiness", path="packages/pybusiness")

    message = str(exc.value)
    assert "/" in message and "::" in message


@pytest.mark.parametrize("good_name", ["pybusiness", "run-rate", "rsv2_model", "a"])
def test_member_name_grammar_accepts(good_name):
    """Lowercase letters, digits, underscores and hyphens are all legal."""
    assert WorkspaceMember(name=good_name, path="packages/thing").name == good_name


# ---------------------------------------------------------------------------
# Member path shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_path",
    [
        "/abs/packages/thing",  # absolute
        "../sibling",  # escapes the workspace root
        "packages/../../escape",  # escapes after normalization
        "",  # empty
    ],
)
def test_member_path_must_stay_inside_workspace(bad_path):
    """Member paths are workspace-root-relative and may not escape the root."""
    with pytest.raises(ValidationError):
        WorkspaceMember(name="thing", path=bad_path)


def test_member_path_is_normalized_to_relative_posix():
    """Redundant separators and ./ segments normalize so paths compare equal."""
    member = WorkspaceMember(name="thing", path="./packages//libs/thing/")
    assert member.path == "packages/libs/thing"


def test_workspace_root_itself_can_be_a_member():
    """A monorepo root that is itself a VE tree is registrable as '.'."""
    assert WorkspaceMember(name="platform", path=".").path == "."


# ---------------------------------------------------------------------------
# Manifest shape: mapping form, ordering, duplicates
# ---------------------------------------------------------------------------


def test_manifest_accepts_mapping_form_and_preserves_order():
    """The on-disk name -> path mapping loads, in declaration order."""
    manifest = WorkspaceManifest.model_validate(
        {"members": {"viz": "apps/viz", "pybusiness": "packages/libs/pybusiness"}}
    )

    assert manifest.names() == ["viz", "pybusiness"]
    assert manifest.get("pybusiness").path == "packages/libs/pybusiness"
    assert manifest.get("absent") is None


def test_manifest_round_trips_through_mapping():
    """to_mapping() is the inverse of the mapping form it was loaded from."""
    mapping = {"viz": "apps/viz", "pybusiness": "packages/libs/pybusiness"}

    manifest = WorkspaceManifest.model_validate({"members": mapping})

    assert manifest.to_mapping() == mapping


def test_manifest_rejects_duplicate_names_when_built_programmatically():
    """Two members cannot share a name: the name is what `::` resolves against."""
    with pytest.raises(ValidationError) as exc:
        WorkspaceManifest(
            members=[
                WorkspaceMember(name="viz", path="apps/viz"),
                WorkspaceMember(name="viz", path="apps/viz2"),
            ]
        )

    assert "viz" in str(exc.value)


def test_empty_manifest_is_valid():
    """`ve workspace init` writes a member-less manifest, which must load."""
    assert WorkspaceManifest.model_validate({"members": {}}).names() == []


# ---------------------------------------------------------------------------
# Loading and discovery
# ---------------------------------------------------------------------------


def test_load_workspace_resolves_member_paths_to_absolute_paths(tmp_path):
    """A loaded workspace turns member names into usable filesystem paths."""
    make_workspace(tmp_path, {"pybusiness": "packages/libs/pybusiness", "viz": "apps/viz"})

    ws = load_workspace(tmp_path)

    assert ws.root == tmp_path
    assert ws.resolve("pybusiness") == tmp_path / "packages/libs/pybusiness"
    assert ws.resolve("viz").is_dir()


def test_resolve_unknown_member_names_known_members(tmp_path):
    """Resolving a name that is not registered fails with the available names."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    ws = load_workspace(tmp_path)

    with pytest.raises(KeyError) as exc:
        ws.resolve("pybusiness")

    assert "viz" in str(exc.value)


def test_find_workspace_root_walks_up_from_nested_directory(tmp_path):
    """A command run deep inside a member still finds the workspace root."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    nested = tmp_path / "apps" / "viz" / "src" / "deep"
    nested.mkdir(parents=True)

    assert find_workspace_root(nested) == tmp_path


def test_find_workspace_root_returns_none_without_manifest(tmp_path):
    """No manifest anywhere above means no workspace."""
    (tmp_path / "sub").mkdir()

    assert find_workspace_root(tmp_path / "sub") is None


def test_load_workspace_without_manifest_raises_not_found(tmp_path):
    """The loader distinguishes 'no workspace' from 'broken workspace'."""
    with pytest.raises(WorkspaceNotFoundError) as exc:
        load_workspace(tmp_path)

    assert WORKSPACE_MANIFEST_NAME in str(exc.value)


def test_load_workspace_rejects_duplicate_keys_in_the_file(tmp_path):
    """A hand-edited file with a repeated member name is an error, not last-wins.

    yaml.safe_load would silently keep the last value; the manifest is the
    single authority for `<member>::` resolution, so a repeated key must fail.
    """
    (tmp_path / WORKSPACE_MANIFEST_NAME).write_text(
        "members:\n"
        "  viz: apps/viz\n"
        "  viz: apps/other_viz\n"
    )

    with pytest.raises(WorkspaceManifestError) as exc:
        load_workspace(tmp_path)

    assert "viz" in str(exc.value)


def test_load_workspace_reports_bad_member_name_from_file(tmp_path):
    """Shape errors in the file surface as manifest errors, not raw pydantic."""
    write_workspace(tmp_path, {"Not_Valid": "apps/viz"})

    with pytest.raises(WorkspaceManifestError):
        load_workspace(tmp_path)


def test_load_workspace_reports_malformed_yaml(tmp_path):
    """Unparseable YAML is a manifest error naming the file."""
    (tmp_path / WORKSPACE_MANIFEST_NAME).write_text("members: [unclosed\n")

    with pytest.raises(WorkspaceManifestError):
        load_workspace(tmp_path)


def test_write_then_load_round_trips_nested_members(tmp_path):
    """Nested members are legal and survive a save/load cycle unchanged.

    Nesting is the point of a workspace: a library tree can live inside a
    platform tree. Both must remain individually addressable.
    """
    make_tree(tmp_path)
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")
    manifest = WorkspaceManifest.model_validate(
        {"members": {"platform": ".", "pybusiness": "packages/libs/pybusiness"}}
    )

    write_manifest(tmp_path, manifest)
    reloaded = load_workspace(tmp_path)

    assert reloaded.manifest.to_mapping() == manifest.to_mapping()
    assert reloaded.resolve("platform") == tmp_path
    assert reloaded.resolve("pybusiness") == tmp_path / "packages/libs/pybusiness"


# ---------------------------------------------------------------------------
# Nesting resolution: longest prefix wins
# ---------------------------------------------------------------------------


def test_find_member_for_path_returns_innermost_member(tmp_path):
    """A file inside a nested member belongs to the nested member, not the outer one."""
    make_tree(tmp_path)
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")
    write_workspace(tmp_path, {"platform": ".", "pybusiness": "packages/libs/pybusiness"})
    ws = load_workspace(tmp_path)

    inner = ws.find_member_for_path(
        tmp_path / "packages" / "libs" / "pybusiness" / "savings" / "realized.py"
    )
    outer = ws.find_member_for_path(tmp_path / "apps" / "viz" / "main.py")

    assert inner.name == "pybusiness"
    assert outer.name == "platform"


def test_find_member_for_path_returns_none_outside_all_members(tmp_path):
    """A path in no registered member has no owning tree."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    ws = load_workspace(tmp_path)

    assert ws.find_member_for_path(tmp_path / "tools" / "script.py") is None


def test_find_member_for_path_does_not_match_sibling_name_prefix(tmp_path):
    """`apps/viz2` is not inside `apps/viz` despite the string prefix."""
    make_workspace(tmp_path, {"viz": "apps/viz", "viz2": "apps/viz2"})
    ws = load_workspace(tmp_path)

    assert ws.find_member_for_path(tmp_path / "apps" / "viz2" / "app.py").name == "viz2"


# ---------------------------------------------------------------------------
# VE tree predicates and filesystem validation
# ---------------------------------------------------------------------------


def test_is_ve_tree_requires_docs_with_an_artifact_or_trunk_directory(tmp_path):
    """A bare directory, or docs/ with nothing recognizable, is not a VE tree."""
    plain = tmp_path / "plain"
    plain.mkdir()
    empty_docs = tmp_path / "empty_docs"
    (empty_docs / "docs" / "images").mkdir(parents=True)

    assert not is_ve_tree(plain)
    assert not is_ve_tree(empty_docs)
    assert is_ve_tree(make_tree(tmp_path / "full"))


def test_pointer_only_tree_is_a_valid_member(tmp_path):
    """A tree that is only external.yaml pointers still counts as a member.

    Scaffolded packages get pointer-only trees (no docs/trunk/); they must be
    registrable or the workspace cannot describe them.
    """
    pointer = make_pointer_tree(tmp_path / "apps" / "viz")

    assert is_ve_tree(pointer)
    assert not has_trunk(pointer)


def test_validate_member_paths_reports_missing_and_non_tree_members(tmp_path):
    """Filesystem validation names each defective member and the reason."""
    make_tree(tmp_path / "apps" / "viz")
    (tmp_path / "tools" / "scripts").mkdir(parents=True)
    write_workspace(
        tmp_path,
        {
            "viz": "apps/viz",
            "gone": "packages/deleted",
            "scripts": "tools/scripts",
        },
    )
    ws = load_workspace(tmp_path)

    errors = validate_member_paths(ws)

    joined = "\n".join(errors)
    assert len(errors) == 2
    assert "gone" in joined and "packages/deleted" in joined
    assert "scripts" in joined
    assert "viz" not in joined


def test_validate_member_paths_clean_workspace_has_no_errors(tmp_path):
    """A workspace whose members all exist and hold trees validates clean."""
    make_workspace(tmp_path, {"viz": "apps/viz", "pybusiness": "packages/pybusiness"})

    assert validate_member_paths(load_workspace(tmp_path)) == []


def test_validate_member_paths_rejects_member_pointing_at_a_file(tmp_path):
    """A member path that is a file, not a directory, is a defect."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    (tmp_path / "notes.md").write_text("hi\n")
    ws = Workspace(
        root=tmp_path,
        manifest=WorkspaceManifest.model_validate({"members": {"notes": "notes.md"}}),
    )

    assert len(validate_member_paths(ws)) == 1


# ---------------------------------------------------------------------------
# Scan discovery
# ---------------------------------------------------------------------------


def test_scan_finds_trunk_trees_including_nested_and_root(tmp_path):
    """Scan proposes every directory holding docs/trunk/, without pruning nesting."""
    make_tree(tmp_path)
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")
    make_tree(tmp_path / "apps" / "viz")

    found = scan_for_trees(tmp_path)

    assert found == [".", "apps/viz", "packages/libs/pybusiness"]


def test_scan_ignores_pointer_only_trees(tmp_path):
    """docs/trunk/ is the signal of an intentional tree; pointer stubs are not proposed."""
    make_tree(tmp_path / "packages" / "pybusiness")
    make_pointer_tree(tmp_path / "apps" / "viz")

    assert scan_for_trees(tmp_path) == ["packages/pybusiness"]


def test_scan_skips_vcs_and_dependency_directories(tmp_path):
    """A scan must not descend into .git, .venv, node_modules or __pycache__."""
    make_tree(tmp_path / "packages" / "pybusiness")
    for junk in (".git", ".venv", "node_modules", "__pycache__", "build", "dist"):
        make_tree(tmp_path / junk / "vendored")

    assert scan_for_trees(tmp_path) == ["packages/pybusiness"]


def test_scan_skips_worktree_checkouts_of_the_same_repo(tmp_path):
    """Agent and orchestrator worktrees must not be proposed as members.

    VE keeps worktree checkouts under .claude/worktrees/ and .ve/chunks/*/, each
    a full copy of the repository's own trees. Proposing them would offer the
    operator the same tree several times under different paths.
    """
    make_tree(tmp_path)
    make_tree(tmp_path / "packages" / "pybusiness")
    make_tree(tmp_path / ".claude" / "worktrees" / "agent-abc")
    make_tree(tmp_path / ".claude" / "worktrees" / "agent-abc" / "packages" / "pybusiness")
    make_tree(tmp_path / ".ve" / "chunks" / "some_chunk" / "worktree")

    assert scan_for_trees(tmp_path) == [".", "packages/pybusiness"]


def test_scan_excludes_a_scaffolding_template_tree(tmp_path):
    """A cookiecutter template that ships its own docs tree is excludable.

    The case-study monorepo had exactly this: a task template directory
    containing a full docs/ tree, minting a namespace per scaffolded package.
    """
    make_tree(tmp_path / "packages" / "pybusiness")
    make_tree(tmp_path / "tools" / "cookiecutter" / "package_template")

    without_exclude = scan_for_trees(tmp_path)
    with_exclude = scan_for_trees(tmp_path, exclude=["*_template"])

    assert "tools/cookiecutter/package_template" in without_exclude
    assert with_exclude == ["packages/pybusiness"]


def test_scan_exclude_by_path_prefix_prunes_the_whole_subtree(tmp_path):
    """Excluding a directory drops the trees beneath it too."""
    make_tree(tmp_path / "packages" / "pybusiness")
    make_tree(tmp_path / "tools" / "templates" / "a")
    make_tree(tmp_path / "tools" / "templates" / "b")

    assert scan_for_trees(tmp_path, exclude=["tools/templates"]) == ["packages/pybusiness"]


def test_scan_of_a_repo_with_no_trees_is_empty(tmp_path):
    """Scanning a monorepo with no VE trees yields nothing rather than failing."""
    (tmp_path / "src").mkdir()

    assert scan_for_trees(tmp_path) == []


# ---------------------------------------------------------------------------
# Name suggestion
# ---------------------------------------------------------------------------


def test_suggest_member_names_uses_directory_names(tmp_path):
    """A candidate's short name defaults to its directory name."""
    suggestions = suggest_member_names(["packages/libs/pybusiness", "apps/viz"], root=tmp_path)

    assert suggestions == [("pybusiness", "packages/libs/pybusiness"), ("viz", "apps/viz")]


def test_suggest_member_names_uses_root_directory_name_for_dot(tmp_path):
    """The workspace root itself gets named after the root directory."""
    root = tmp_path / "platform"
    root.mkdir()

    assert suggest_member_names(["."], root=root) == [("platform", ".")]


def test_suggest_member_names_coerces_out_of_grammar_characters(tmp_path):
    """A directory name that is not a legal member name is coerced into one."""
    (name, _), = suggest_member_names(["packages/My.Lib"], root=tmp_path)

    assert name == "my_lib"
    assert WorkspaceMember(name=name, path="packages/My.Lib").name == name


def test_suggest_member_names_disambiguates_collisions(tmp_path):
    """Two trees with the same directory name get distinct names, not a clash."""
    suggestions = suggest_member_names(
        ["packages/alpha/common", "packages/beta/common"], root=tmp_path
    )

    names = [name for name, _ in suggestions]
    assert names[0] == "common"
    assert len(set(names)) == 2
    assert "beta" in names[1]


# ---------------------------------------------------------------------------
# CLI: ve workspace list
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_list_prints_members_and_paths(tmp_path, runner):
    """`ve workspace list` enumerates the members with their paths."""
    make_workspace(tmp_path, {"pybusiness": "packages/libs/pybusiness", "viz": "apps/viz"})

    result = runner.invoke(cli, ["workspace", "list", "--workspace-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "pybusiness" in result.output
    assert "packages/libs/pybusiness" in result.output
    assert "viz" in result.output
    assert "apps/viz" in result.output


def test_cli_list_without_manifest_exits_nonzero(tmp_path, runner):
    """With no manifest the command fails with an actionable message."""
    result = runner.invoke(cli, ["workspace", "list", "--workspace-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert WORKSPACE_MANIFEST_NAME in result.output
    assert "ve workspace init" in result.output


def test_cli_list_flags_members_whose_trees_are_gone(tmp_path, runner):
    """Defective members are marked, and the two failure modes are told apart."""
    make_tree(tmp_path / "apps" / "viz")
    (tmp_path / "tools" / "scripts").mkdir(parents=True)
    write_workspace(
        tmp_path,
        {"viz": "apps/viz", "gone": "packages/deleted", "scripts": "tools/scripts"},
    )

    result = runner.invoke(cli, ["workspace", "list", "--workspace-dir", str(tmp_path)])

    assert result.exit_code == 0
    lines = {
        line.split()[0]: line for line in result.output.splitlines() if line.startswith("  ")
    }
    assert "does not exist" in lines["gone"]
    assert "no VE tree" in lines["scripts"]
    assert "missing" not in lines["viz"]


def test_cli_list_from_a_nested_directory_finds_the_workspace(tmp_path, runner):
    """The command works from inside a member, not just at the workspace root."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    nested = tmp_path / "apps" / "viz" / "src"
    nested.mkdir(parents=True)

    result = runner.invoke(cli, ["workspace", "list", "--workspace-dir", str(nested)])

    assert result.exit_code == 0
    assert "viz" in result.output


def test_cli_list_reports_a_broken_manifest_clearly(tmp_path, runner):
    """A manifest with a duplicate key fails with the offending name."""
    (tmp_path / WORKSPACE_MANIFEST_NAME).write_text(
        "members:\n  viz: apps/viz\n  viz: apps/other\n"
    )

    result = runner.invoke(cli, ["workspace", "list", "--workspace-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert "viz" in result.output


# ---------------------------------------------------------------------------
# CLI: ve workspace add
# ---------------------------------------------------------------------------


def test_cli_add_registers_a_member(tmp_path, runner):
    """`ve workspace add` appends the member to the manifest on disk."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")

    result = runner.invoke(
        cli,
        [
            "workspace", "add", "pybusiness", "packages/libs/pybusiness",
            "--workspace-dir", str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {
        "viz": "apps/viz",
        "pybusiness": "packages/libs/pybusiness",
    }


def test_cli_add_accepts_an_absolute_path_inside_the_workspace(tmp_path, runner):
    """An absolute path is stored relative to the workspace root."""
    make_workspace(tmp_path, {})
    tree = make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli, ["workspace", "add", "viz", str(tree), "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {"viz": "apps/viz"}


def test_cli_add_accepts_a_pointer_only_tree(tmp_path, runner):
    """Pointer-only trees are registrable members."""
    make_workspace(tmp_path, {})
    make_pointer_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli, ["workspace", "add", "viz", "apps/viz", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {"viz": "apps/viz"}


def test_cli_add_rejects_duplicate_name_and_leaves_manifest_untouched(tmp_path, runner):
    """Re-registering a name fails; the existing mapping is preserved."""
    make_workspace(tmp_path, {"viz": "apps/viz"})
    make_tree(tmp_path / "apps" / "viz2")

    result = runner.invoke(
        cli, ["workspace", "add", "viz", "apps/viz2", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert read_members(tmp_path) == {"viz": "apps/viz"}


def test_cli_add_rejects_bad_member_name(tmp_path, runner):
    """A name outside the grammar is refused before anything is written."""
    make_workspace(tmp_path, {})
    make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli, ["workspace", "add", "acme/viz", "apps/viz", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert read_members(tmp_path) == {}


def test_cli_add_rejects_missing_path(tmp_path, runner):
    """A path that does not exist cannot be registered."""
    make_workspace(tmp_path, {})

    result = runner.invoke(
        cli, ["workspace", "add", "viz", "apps/viz", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert read_members(tmp_path) == {}


def test_cli_add_rejects_a_directory_that_is_not_a_ve_tree(tmp_path, runner):
    """Registering a directory with no docs tree fails with a clear reason."""
    make_workspace(tmp_path, {})
    (tmp_path / "tools" / "scripts").mkdir(parents=True)

    result = runner.invoke(
        cli, ["workspace", "add", "scripts", "tools/scripts", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "docs" in result.output
    assert read_members(tmp_path) == {}


def test_cli_add_rejects_a_path_outside_the_workspace(tmp_path, runner):
    """A tree outside the workspace root is not a member of it."""
    root = tmp_path / "monorepo"
    make_workspace(root, {})
    outside = make_tree(tmp_path / "elsewhere")

    result = runner.invoke(
        cli, ["workspace", "add", "elsewhere", str(outside), "--workspace-dir", str(root)]
    )

    assert result.exit_code != 0
    assert read_members(root) == {}


def test_cli_add_rejects_a_relative_path_that_escapes_the_workspace(tmp_path, runner):
    """A `../` path is refused, not silently stored as an escaping member."""
    root = tmp_path / "monorepo"
    make_workspace(root, {})
    make_tree(tmp_path / "elsewhere")

    result = runner.invoke(
        cli, ["workspace", "add", "elsewhere", "../elsewhere", "--workspace-dir", str(root)]
    )

    assert result.exit_code != 0
    assert read_members(root) == {}


def test_cli_add_without_manifest_exits_nonzero(tmp_path, runner):
    """Adding to a nonexistent workspace tells the operator to init first."""
    make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli, ["workspace", "add", "viz", "apps/viz", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "ve workspace init" in result.output


# ---------------------------------------------------------------------------
# CLI: ve workspace init
# ---------------------------------------------------------------------------


def test_cli_init_writes_an_empty_manifest(tmp_path, runner):
    """Without --scan, init creates a manifest with no members."""
    result = runner.invoke(cli, ["workspace", "init", "--workspace-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert read_members(tmp_path) == {}
    assert load_workspace(tmp_path).manifest.names() == []


def test_cli_init_refuses_to_overwrite_an_existing_manifest(tmp_path, runner):
    """An existing manifest is never clobbered."""
    make_workspace(tmp_path, {"viz": "apps/viz"})

    result = runner.invoke(cli, ["workspace", "init", "--workspace-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert read_members(tmp_path) == {"viz": "apps/viz"}


def test_cli_init_scan_registers_confirmed_candidates(tmp_path, runner):
    """--scan discovers trees and writes them once the operator confirms."""
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")
    make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli,
        ["workspace", "init", "--scan", "--workspace-dir", str(tmp_path)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {
        "viz": "apps/viz",
        "pybusiness": "packages/libs/pybusiness",
    }


def test_cli_init_scan_presents_candidates_before_writing(tmp_path, runner):
    """Candidates are shown with their suggested names, not silently registered."""
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")

    result = runner.invoke(
        cli,
        ["workspace", "init", "--scan", "--workspace-dir", str(tmp_path)],
        input="n\n",
    )

    assert "pybusiness" in result.output
    assert "packages/libs/pybusiness" in result.output
    assert "--exclude" in result.output


def test_cli_init_scan_declined_writes_nothing(tmp_path, runner):
    """Answering no leaves no manifest behind."""
    make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli,
        ["workspace", "init", "--scan", "--workspace-dir", str(tmp_path)],
        input="n\n",
    )

    assert result.exit_code != 0
    assert not (tmp_path / WORKSPACE_MANIFEST_NAME).exists()


def test_cli_init_scan_yes_skips_the_prompt(tmp_path, runner):
    """-y registers the candidates without prompting."""
    make_tree(tmp_path / "apps" / "viz")

    result = runner.invoke(
        cli, ["workspace", "init", "--scan", "-y", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {"viz": "apps/viz"}


def test_cli_init_scan_excludes_a_template_tree(tmp_path, runner):
    """--exclude keeps a scaffolding template out of the manifest.

    This is the case-study repair: the cookiecutter template ships a docs tree
    and must not become a workspace member.
    """
    make_tree(tmp_path / "packages" / "pybusiness")
    make_tree(tmp_path / "tools" / "cookiecutter" / "package_template")

    result = runner.invoke(
        cli,
        [
            "workspace", "init", "--scan", "-y",
            "--exclude", "*_template",
            "--workspace-dir", str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {"pybusiness": "packages/pybusiness"}


def test_cli_init_scan_with_no_trees_found(tmp_path, runner):
    """Scanning a repo with no trees says so and writes an empty manifest."""
    (tmp_path / "src").mkdir()

    result = runner.invoke(
        cli, ["workspace", "init", "--scan", "-y", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert read_members(tmp_path) == {}


def test_cli_init_scan_result_is_loadable_and_resolvable(tmp_path, runner):
    """The manifest init writes is a working resolution surface.

    End-to-end check of the chunk's purpose: after bootstrapping, a member name
    resolves to the tree that owns it, including for a nested tree.
    """
    make_tree(tmp_path)
    make_tree(tmp_path / "packages" / "libs" / "pybusiness")

    result = runner.invoke(
        cli, ["workspace", "init", "--scan", "-y", "--workspace-dir", str(tmp_path)]
    )
    assert result.exit_code == 0

    ws = load_workspace(tmp_path)
    assert validate_member_paths(ws) == []
    assert ws.resolve("pybusiness") == tmp_path / "packages/libs/pybusiness"
    assert (
        ws.find_member_for_path(
            tmp_path / "packages/libs/pybusiness/savings/realized.py"
        ).name
        == "pybusiness"
    )
