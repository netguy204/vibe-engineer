"""Tests for peer (intra-workspace) external references.

# Chunk: docs/chunks/federation_peer_refs - Peer external reference tests

A peer reference is an `external.yaml` carrying `tree: <member>` instead of
`repo: <org>/<repo>`: the target lives in another VE tree of the same working
copy, so resolution is a manifest lookup plus a filesystem read - no repo cache,
no track, no SHA.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from click.testing import CliRunner
from pydantic import ValidationError

from conftest import make_ve_tree, write_workspace_manifest
from external_refs import (
    ARTIFACT_DIR_NAME,
    ARTIFACT_MAIN_FILE,
    create_external_yaml,
    create_peer_yaml,
    is_external_artifact,
    load_external_ref,
)
from external_resolve import resolve_artifact_peer, resolve_artifact_single_repo
from models import ArtifactType, ExternalArtifactRef
from task import TaskChunkError
from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_ARTIFACT_DIRS = ("chunks", "narratives", "investigations", "subsystems")


def make_artifact(tree: pathlib.Path, artifact_type: ArtifactType, name: str, body: str) -> pathlib.Path:
    """Create a real (non-pointer) artifact with a main document in `tree`."""
    directory = tree / "docs" / ARTIFACT_DIR_NAME[artifact_type] / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ARTIFACT_MAIN_FILE[artifact_type]).write_text(body)
    if artifact_type == ArtifactType.CHUNK:
        (directory / "PLAN.md").write_text("# Plan\n\nOwner plan.\n")
    return directory


@pytest.fixture
def two_trees(tmp_path):
    """A workspace with an `owner` tree and a `consumer` tree.

    The owner tree holds a real subsystem (`commitment_baseline`); the consumer
    tree is where peer pointers get created. This is the case study's shape: the
    tree whose code enforces an invariant owns the doc, and a second tree reads
    it.
    """
    root = tmp_path / "monorepo"
    owner = make_ve_tree(root / "packages" / "libs" / "pybusiness", artifacts=ALL_ARTIFACT_DIRS)
    consumer = make_ve_tree(root / "apps" / "viz", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(
        root,
        {"pybusiness": "packages/libs/pybusiness", "viz": "apps/viz"},
    )
    make_artifact(
        owner,
        ArtifactType.SUBSYSTEM,
        "commitment_baseline",
        "# Commitment Baseline\n\nThe invariant that governs realized savings.\n",
    )
    return root, owner, consumer


# ---------------------------------------------------------------------------
# Schema: tree xor repo, track invalid with tree, why
# ---------------------------------------------------------------------------


def test_peer_ref_accepts_tree_without_repo():
    """A `tree:` target is a complete address: no repo, no track needed."""
    ref = ExternalArtifactRef(
        artifact_type=ArtifactType.SUBSYSTEM,
        artifact_id="commitment_baseline",
        tree="pybusiness",
    )

    assert ref.is_peer
    assert ref.repo is None
    assert ref.track is None
    assert "pybusiness" in ref.target_display


def test_repo_ref_is_not_a_peer_ref():
    """The cross-repo flavor stays distinguishable from the peer flavor."""
    ref = ExternalArtifactRef(
        artifact_type=ArtifactType.CHUNK,
        artifact_id="shared_feature",
        repo="acme/hub",
        track="main",
    )

    assert not ref.is_peer
    assert ref.target_display == "acme/hub"


def test_ref_rejects_both_tree_and_repo():
    """`tree` and `repo` are mutually exclusive addresses."""
    with pytest.raises(ValidationError) as exc_info:
        ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            artifact_id="shared_feature",
            repo="acme/hub",
            tree="pybusiness",
        )

    message = str(exc_info.value)
    assert "tree" in message and "repo" in message
    assert "exactly one" in message.lower() or "mutually exclusive" in message.lower()


def test_ref_rejects_neither_tree_nor_repo():
    """A pointer with no target is unresolvable and must not validate."""
    with pytest.raises(ValidationError) as exc_info:
        ExternalArtifactRef(
            artifact_type=ArtifactType.CHUNK,
            artifact_id="shared_feature",
        )

    message = str(exc_info.value)
    assert "tree" in message and "repo" in message


def test_ref_rejects_track_with_tree():
    """Peer refs are trackless: same working copy, same commit by construction."""
    with pytest.raises(ValidationError) as exc_info:
        ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="commitment_baseline",
            tree="pybusiness",
            track="main",
        )

    message = str(exc_info.value)
    assert "track" in message
    assert "tree" in message


def test_ref_rejects_pinned_with_tree():
    """A pinned SHA is equally meaningless for a same-working-copy target."""
    with pytest.raises(ValidationError) as exc_info:
        ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="commitment_baseline",
            tree="pybusiness",
            pinned="a" * 40,
        )

    assert "pinned" in str(exc_info.value)


@pytest.mark.parametrize("bad_member", ["Pybusiness", "acme/hub", "py business", "", "tree::x"])
def test_ref_rejects_member_names_outside_the_grammar(bad_member):
    """`tree` holds a workspace member name, held to the manifest's grammar."""
    with pytest.raises(ValidationError):
        ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="commitment_baseline",
            tree=bad_member,
        )


def test_member_name_rejection_explains_the_grammar():
    """The error tells the operator what a member name may contain."""
    with pytest.raises(ValidationError) as exc_info:
        ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="commitment_baseline",
            tree="acme/hub",
        )

    assert "[a-z0-9_-]+" in str(exc_info.value)


def test_why_is_kept_on_peer_and_repo_refs():
    """An interest note is meaningful for either flavor of pointer."""
    peer = ExternalArtifactRef(
        artifact_type=ArtifactType.SUBSYSTEM,
        artifact_id="commitment_baseline",
        tree="pybusiness",
        why="  Charts render realized savings from this baseline  ",
    )
    cross_repo = ExternalArtifactRef(
        artifact_type=ArtifactType.CHUNK,
        artifact_id="shared_feature",
        repo="acme/hub",
        why="We consume the API this chunk defines",
    )

    assert peer.why == "Charts render realized savings from this baseline"
    assert cross_repo.why == "We consume the API this chunk defines"


@pytest.mark.parametrize("bad_why", ["", "   ", "first line\nsecond line"])
def test_why_rejects_empty_and_multiline_values(bad_why):
    """`why` is one line of prose: empty says nothing, multiline breaks reports."""
    with pytest.raises(ValidationError):
        ExternalArtifactRef(
            artifact_type=ArtifactType.SUBSYSTEM,
            artifact_id="commitment_baseline",
            tree="pybusiness",
            why=bad_why,
        )


def test_existing_repo_external_yaml_still_loads(tmp_path):
    """Regression: repo-based pointers written before this change parse unchanged."""
    artifact_dir = tmp_path / "docs" / "chunks" / "shared_feature"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "external.yaml").write_text(
        "artifact_type: chunk\n"
        "artifact_id: shared_feature\n"
        "repo: acme/hub\n"
        "track: main\n"
        "created_after:\n"
        "- earlier_chunk\n"
    )

    ref = load_external_ref(artifact_dir)

    assert ref.repo == "acme/hub"
    assert ref.track == "main"
    assert ref.tree is None
    assert ref.created_after == ["earlier_chunk"]


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def test_create_peer_yaml_writes_a_trackless_pointer(tmp_path):
    """The written file addresses a member and carries no track."""
    path = create_peer_yaml(
        project_path=tmp_path,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="Charts render realized savings from this baseline",
    )

    data = yaml.safe_load(path.read_text())
    assert data["tree"] == "pybusiness"
    assert data["why"] == "Charts render realized savings from this baseline"
    assert "track" not in data
    assert "repo" not in data

    ref = load_external_ref(path.parent)
    assert ref.is_peer
    assert ref.artifact_type == ArtifactType.SUBSYSTEM


def test_create_peer_yaml_places_pointer_under_the_local_name(tmp_path):
    """The local directory name may differ from the target artifact id."""
    path = create_peer_yaml(
        project_path=tmp_path,
        short_name="baseline_from_pybusiness",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    assert path == tmp_path / "docs" / "subsystems" / "baseline_from_pybusiness" / "external.yaml"
    assert load_external_ref(path.parent).artifact_id == "commitment_baseline"


def test_create_peer_yaml_refuses_an_invalid_pointer(tmp_path):
    """Validation happens before the write, so no invalid pointer reaches disk."""
    with pytest.raises(ValidationError):
        create_peer_yaml(
            project_path=tmp_path,
            short_name="broken",
            member="acme/hub",
            external_artifact_id="commitment_baseline",
            artifact_type=ArtifactType.SUBSYSTEM,
        )

    assert not (tmp_path / "docs" / "subsystems" / "broken" / "external.yaml").exists()


@pytest.mark.parametrize("artifact_type", list(ArtifactType))
def test_pointer_detection_is_flavor_blind(tmp_path, artifact_type):
    """`is_external_artifact` treats tree and repo pointers identically."""
    peer = create_peer_yaml(
        project_path=tmp_path / "peer",
        short_name="borrowed",
        member="pybusiness",
        external_artifact_id="borrowed",
        artifact_type=artifact_type,
    )
    cross_repo = create_external_yaml(
        project_path=tmp_path / "cross",
        short_name="borrowed",
        external_repo_ref="acme/hub",
        external_artifact_id="borrowed",
        artifact_type=artifact_type,
    )

    assert is_external_artifact(peer.parent, artifact_type)
    assert is_external_artifact(cross_repo.parent, artifact_type)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def test_peer_ref_resolves_to_the_owning_trees_document(two_trees):
    """Round trip: create a pointer, load it, read the owner's content."""
    _, owner, consumer = two_trees
    create_peer_yaml(
        project_path=consumer,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="Charts render realized savings from this baseline",
    )

    result = resolve_artifact_peer(consumer, "commitment_baseline", ArtifactType.SUBSYSTEM)

    assert "invariant that governs realized savings" in result.main_content
    assert result.local_path == owner / "docs" / "subsystems" / "commitment_baseline"
    assert result.tree == "pybusiness"
    assert result.why == "Charts render realized savings from this baseline"
    assert result.resolved_sha is None
    assert "OVERVIEW.md" in result.directory_contents


def test_peer_chunk_ref_resolves_both_documents(two_trees):
    """Chunk pointers carry GOAL.md and PLAN.md, as cross-repo chunk refs do."""
    _, owner, consumer = two_trees
    make_artifact(owner, ArtifactType.CHUNK, "savings_rollup", "# Goal\n\nRoll up savings.\n")
    create_peer_yaml(
        project_path=consumer,
        short_name="savings_rollup",
        member="pybusiness",
        external_artifact_id="savings_rollup",
        artifact_type=ArtifactType.CHUNK,
    )

    result = resolve_artifact_peer(consumer, "savings_rollup", ArtifactType.CHUNK)

    assert "Roll up savings" in result.main_content
    assert "Owner plan" in result.secondary_content


def test_ve_external_resolve_routes_peer_refs_without_a_cache(two_trees):
    """The generic entry point dispatches on the pointer's flavor."""
    _, _, consumer = two_trees
    create_peer_yaml(
        project_path=consumer,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    result = resolve_artifact_single_repo(
        consumer, "commitment_baseline", ArtifactType.SUBSYSTEM
    )

    assert "invariant that governs realized savings" in result.main_content
    assert result.repo is None
    assert "peer" in result.context_mode


def test_unregistered_member_error_lists_registered_members(two_trees):
    """A pointer at an unknown tree names the members that do exist."""
    _, _, consumer = two_trees
    pointer = create_peer_yaml(
        project_path=consumer,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    pointer.write_text(
        pointer.read_text().replace("tree: pybusiness", "tree: pybiz")
    )

    with pytest.raises(TaskChunkError) as exc_info:
        resolve_artifact_peer(consumer, "commitment_baseline", ArtifactType.SUBSYSTEM)

    message = str(exc_info.value)
    assert "pybiz" in message
    assert "pybusiness" in message and "viz" in message


def test_missing_target_artifact_error_names_the_expected_path(two_trees):
    """The born-dangling case: the member exists, the artifact never did."""
    _, owner, consumer = two_trees
    create_peer_yaml(
        project_path=consumer,
        short_name="rsv2_pybusiness_model",
        member="pybusiness",
        external_artifact_id="rsv2_pybusiness_model",
        artifact_type=ArtifactType.CHUNK,
    )

    with pytest.raises(TaskChunkError) as exc_info:
        resolve_artifact_peer(consumer, "rsv2_pybusiness_model", ArtifactType.CHUNK)

    message = str(exc_info.value)
    assert "rsv2_pybusiness_model" in message
    assert "pybusiness" in message
    assert str(owner / "docs" / "chunks" / "rsv2_pybusiness_model") in message


def test_missing_main_document_is_distinct_from_a_missing_directory(two_trees):
    """A directory that exists but holds no main document says exactly that."""
    _, owner, consumer = two_trees
    (owner / "docs" / "chunks" / "half_built").mkdir(parents=True)
    create_peer_yaml(
        project_path=consumer,
        short_name="half_built",
        member="pybusiness",
        external_artifact_id="half_built",
        artifact_type=ArtifactType.CHUNK,
    )

    with pytest.raises(TaskChunkError) as exc_info:
        resolve_artifact_peer(consumer, "half_built", ArtifactType.CHUNK)

    assert "GOAL.md" in str(exc_info.value)


def test_peer_ref_without_a_workspace_manifest_says_so(tmp_path):
    """A tree pointer outside any workspace cannot resolve, and explains why."""
    consumer = make_ve_tree(tmp_path / "lonely", artifacts=ALL_ARTIFACT_DIRS)
    create_peer_yaml(
        project_path=consumer,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    with pytest.raises(TaskChunkError) as exc_info:
        resolve_artifact_peer(consumer, "commitment_baseline", ArtifactType.SUBSYSTEM)

    message = str(exc_info.value)
    assert ".ve-workspace.yaml" in message
    assert "pybusiness" in message


def test_mutual_interest_between_two_trees_resolves(two_trees):
    """Interest edges may form cycles; only `created_after` stays acyclic."""
    _, owner, consumer = two_trees
    make_artifact(consumer, ArtifactType.CHUNK, "viz_savings_panel", "# Goal\n\nPanel.\n")

    create_peer_yaml(
        project_path=consumer,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="Panel labels come from this baseline",
    )
    create_peer_yaml(
        project_path=owner,
        short_name="viz_savings_panel",
        member="viz",
        external_artifact_id="viz_savings_panel",
        artifact_type=ArtifactType.CHUNK,
        why="Changing the baseline changes this panel",
    )

    forward = resolve_artifact_peer(consumer, "commitment_baseline", ArtifactType.SUBSYSTEM)
    backward = resolve_artifact_peer(owner, "viz_savings_panel", ArtifactType.CHUNK)

    assert "invariant that governs realized savings" in forward.main_content
    assert "Panel." in backward.main_content


def test_pointer_only_member_tree_can_be_a_peer_target(tmp_path):
    """A member with no docs/trunk/ is still a legal resolution target."""
    root = tmp_path / "monorepo"
    pointer_only = make_ve_tree(root / "packages" / "scaffolded", trunk=False)
    consumer = make_ve_tree(root / "apps" / "viz", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(
        root, {"scaffolded": "packages/scaffolded", "viz": "apps/viz"}
    )
    make_artifact(pointer_only, ArtifactType.CHUNK, "local_only", "# Goal\n\nScaffolded work.\n")

    create_peer_yaml(
        project_path=consumer,
        short_name="local_only",
        member="scaffolded",
        external_artifact_id="local_only",
        artifact_type=ArtifactType.CHUNK,
    )

    result = resolve_artifact_peer(consumer, "local_only", ArtifactType.CHUNK)

    assert "Scaffolded work" in result.main_content


# ---------------------------------------------------------------------------
# CLI: ve external point / ve external resolve
# ---------------------------------------------------------------------------


def test_external_point_creates_a_resolvable_pointer(two_trees):
    """`ve external point` writes an interest edge that resolves immediately."""
    _, _, consumer = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "external",
            "point",
            "pybusiness",
            "docs/subsystems/commitment_baseline",
            "--why",
            "Charts render realized savings from this baseline",
            "--project-dir",
            str(consumer),
        ],
    )

    assert result.exit_code == 0, result.output
    pointer = consumer / "docs" / "subsystems" / "commitment_baseline" / "external.yaml"
    assert pointer.exists()

    resolved = runner.invoke(
        cli,
        ["external", "resolve", "commitment_baseline", "--project-dir", str(consumer)],
    )
    assert resolved.exit_code == 0, resolved.output
    assert "invariant that governs realized savings" in resolved.output
    assert "Charts render realized savings from this baseline" in resolved.output


def test_external_point_accepts_a_bare_artifact_name(two_trees):
    """The artifact may be named without its docs/<type>/ prefix."""
    _, _, consumer = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["external", "point", "pybusiness", "commitment_baseline", "--project-dir", str(consumer)],
    )

    assert result.exit_code == 0, result.output
    assert load_external_ref(consumer / "docs" / "subsystems" / "commitment_baseline").is_peer


def test_external_point_rejects_an_unregistered_member(two_trees):
    """Pointing at a tree the manifest does not name fails loudly."""
    _, _, consumer = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["external", "point", "pybiz", "commitment_baseline", "--project-dir", str(consumer)],
    )

    assert result.exit_code == 1
    assert "pybiz" in result.output
    assert "pybusiness" in result.output


def test_external_point_refuses_to_mint_a_dangling_pointer(two_trees):
    """A pointer at a nonexistent artifact is the defect, not a valid state."""
    _, _, consumer = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "external",
            "point",
            "pybusiness",
            "docs/chunks/rsv2_pybusiness_model",
            "--project-dir",
            str(consumer),
        ],
    )

    assert result.exit_code == 1
    assert "rsv2_pybusiness_model" in result.output
    assert not (consumer / "docs" / "chunks" / "rsv2_pybusiness_model").exists()


def test_external_point_force_allows_a_not_yet_created_target(two_trees):
    """--force is the deliberate escape hatch for a target being created."""
    _, _, consumer = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "external",
            "point",
            "pybusiness",
            "docs/chunks/rsv2_pybusiness_model",
            "--force",
            "--project-dir",
            str(consumer),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (consumer / "docs" / "chunks" / "rsv2_pybusiness_model" / "external.yaml").exists()


def test_external_point_refuses_to_overwrite_an_existing_artifact(two_trees):
    """A local artifact directory is never clobbered by a pointer."""
    _, _, consumer = two_trees
    make_artifact(consumer, ArtifactType.SUBSYSTEM, "commitment_baseline", "# Local\n")
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["external", "point", "pybusiness", "commitment_baseline", "--project-dir", str(consumer)],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert "# Local" in (
        consumer / "docs" / "subsystems" / "commitment_baseline" / "OVERVIEW.md"
    ).read_text()


def test_external_point_rejects_pointing_at_your_own_tree(two_trees):
    """Interest is a peer relation: a tree already owns what it owns."""
    _, owner, _ = two_trees
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["external", "point", "pybusiness", "commitment_baseline", "--project-dir", str(owner)],
    )

    assert result.exit_code == 1
    assert "this tree" in result.output


def test_resolve_chunk_location_follows_a_peer_pointer(two_trees):
    """Chunk resolution reaches the owning tree, so validation reads real content."""
    from chunks import Chunks

    _, owner, consumer = two_trees
    make_artifact(owner, ArtifactType.CHUNK, "savings_rollup", "# Goal\n\nRoll up.\n")
    create_peer_yaml(
        project_path=consumer,
        short_name="savings_rollup",
        member="pybusiness",
        external_artifact_id="savings_rollup",
        artifact_type=ArtifactType.CHUNK,
    )

    location = Chunks(consumer).resolve_chunk_location("savings_rollup")

    assert location.is_external
    assert location.external_tree == "pybusiness"
    assert location.chunk_path == owner / "docs" / "chunks" / "savings_rollup"
    assert location.project_dir == owner


def test_resolve_chunk_location_degrades_on_an_unresolvable_peer_pointer(two_trees):
    """An unresolvable pointer reports its location rather than raising."""
    from chunks import Chunks

    _, _, consumer = two_trees
    create_peer_yaml(
        project_path=consumer,
        short_name="rsv2_pybusiness_model",
        member="pybusiness",
        external_artifact_id="rsv2_pybusiness_model",
        artifact_type=ArtifactType.CHUNK,
    )

    location = Chunks(consumer).resolve_chunk_location("rsv2_pybusiness_model")

    assert location.is_external
    assert location.external_tree == "pybusiness"
    assert location.chunk_path == consumer / "docs" / "chunks" / "rsv2_pybusiness_model"


def test_chunk_list_shows_the_member_a_peer_pointer_targets(two_trees):
    """Listing a tree with a peer chunk pointer reports its target tree."""
    _, owner, consumer = two_trees
    make_artifact(owner, ArtifactType.CHUNK, "savings_rollup", "# Goal\n\nRoll up.\n")
    create_peer_yaml(
        project_path=consumer,
        short_name="savings_rollup",
        member="pybusiness",
        external_artifact_id="savings_rollup",
        artifact_type=ArtifactType.CHUNK,
    )
    runner = CliRunner()

    text = runner.invoke(cli, ["chunk", "list", "--project-dir", str(consumer)])
    assert text.exit_code == 0, text.output
    assert "pybusiness" in text.output

    import json

    payload = runner.invoke(
        cli, ["chunk", "list", "--json", "--project-dir", str(consumer)]
    )
    assert payload.exit_code == 0, payload.output
    entries = json.loads(payload.output)
    assert [entry["tree"] for entry in entries if entry["name"] == "savings_rollup"] == [
        "pybusiness"
    ]
