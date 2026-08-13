"""Tests for reverse interest queries and workspace-wide aggregation.

# Chunk: docs/chunks/federation_reverse_interest - Reverse interest and aggregation tests

A peer `external.yaml` is an inbound edge: tree B recording that it reads an
artifact owned by tree A. These tests exercise reading those edges *backwards*
("who consumes this?") and the aggregated listings that make a workspace
browsable without promoting artifacts to the root tree.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from click.testing import CliRunner

from conftest import make_ve_tree, write_workspace_manifest
from external_refs import ARTIFACT_DIR_NAME, ARTIFACT_MAIN_FILE, create_peer_yaml
from interest import (
    find_consumers,
    iter_member_trees,
    scan_interest_edges,
)
from models import ArtifactType
from ve import cli
from workspace import load_workspace

ALL_ARTIFACT_DIRS = ("chunks", "narratives", "investigations", "subsystems")


# ---------------------------------------------------------------------------
# Helpers
#
# These duplicate `make_artifact` in test_external_peer_refs.py deliberately:
# conftest.py is off limits while sibling chunks run in parallel worktrees. Fold
# them into conftest.py once this wave lands.
# ---------------------------------------------------------------------------


def write_artifact(
    tree: pathlib.Path,
    artifact_type: ArtifactType,
    name: str,
    status: str = "ACTIVE",
    body: str = "Owned here.",
) -> pathlib.Path:
    """Create a real (non-pointer) artifact with parseable frontmatter."""
    directory = tree / "docs" / ARTIFACT_DIR_NAME[artifact_type] / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ARTIFACT_MAIN_FILE[artifact_type]).write_text(
        f"---\nstatus: {status}\n---\n\n# {name}\n\n{body}\n"
    )
    if artifact_type == ArtifactType.CHUNK:
        (directory / "PLAN.md").write_text("# Plan\n")
    return directory


def write_raw_pointer(
    tree: pathlib.Path,
    artifact_type: ArtifactType,
    name: str,
    payload: dict | str,
) -> pathlib.Path:
    """Write an external.yaml verbatim, bypassing model validation."""
    directory = tree / "docs" / ARTIFACT_DIR_NAME[artifact_type] / name
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "external.yaml"
    if isinstance(payload, str):
        target.write_text(payload)
    else:
        target.write_text(yaml.safe_dump(payload, sort_keys=False))
    return directory


@pytest.fixture
def workspace_trees(tmp_path):
    """A three-member workspace shaped like the case-study monorepo.

    `pybusiness` owns the intent (a subsystem whose invariant its code enforces);
    `viz` and `rsv2` are consumers with their own trees.
    """
    root = tmp_path / "monorepo"
    owner = make_ve_tree(root / "packages" / "libs" / "pybusiness", artifacts=ALL_ARTIFACT_DIRS)
    viz = make_ve_tree(root / "apps" / "viz", artifacts=ALL_ARTIFACT_DIRS)
    rsv2 = make_ve_tree(root / "apps" / "rsv2", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(
        root,
        {
            "pybusiness": "packages/libs/pybusiness",
            "viz": "apps/viz",
            "rsv2": "apps/rsv2",
        },
    )
    write_artifact(owner, ArtifactType.SUBSYSTEM, "commitment_baseline")
    return root, owner, viz, rsv2


def consumers_of(root, owner, artifact_id, artifact_type=ArtifactType.SUBSYSTEM):
    """Run the reverse query for an artifact owned by `owner`."""
    return find_consumers(
        load_workspace(root),
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        owner_root=owner,
    )


# ---------------------------------------------------------------------------
# Library: inbound edge enumeration
# ---------------------------------------------------------------------------


def test_peer_pointer_is_reported_as_a_consumer(workspace_trees):
    """The owning tree can name who reads its artifact, and why."""
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="renders the realized-savings baseline",
    )

    report = consumers_of(root, owner, "commitment_baseline")

    assert [edge.member for edge in report.peers] == ["viz"]
    edge = report.peers[0]
    assert edge.why == "renders the realized-savings baseline"
    assert edge.pointer_rel == "apps/viz/docs/subsystems/commitment_baseline"
    assert edge.target_dir == (owner / "docs" / "subsystems" / "commitment_baseline")


def test_consumers_excludes_pointers_at_other_artifacts(workspace_trees):
    """Naming the same member is not enough - the artifact must match."""
    root, owner, viz, rsv2 = workspace_trees
    write_artifact(owner, ArtifactType.SUBSYSTEM, "rate_cards")
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    create_peer_yaml(
        project_path=rsv2,
        short_name="rate_cards",
        member="pybusiness",
        external_artifact_id="rate_cards",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    report = consumers_of(root, owner, "commitment_baseline")

    assert [edge.member for edge in report.peers] == ["viz"]


def test_consumers_excludes_same_name_artifact_of_another_type(workspace_trees):
    """A chunk pointer never answers a question about a subsystem."""
    root, owner, viz, _ = workspace_trees
    write_artifact(owner, ArtifactType.CHUNK, "commitment_baseline")
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.CHUNK,
    )

    subsystem_report = consumers_of(root, owner, "commitment_baseline")
    chunk_report = consumers_of(root, owner, "commitment_baseline", ArtifactType.CHUNK)

    assert subsystem_report.peers == []
    assert [edge.member for edge in chunk_report.peers] == ["viz"]


def test_consumers_match_the_owning_tree_through_an_alias(tmp_path):
    """Matching is by resolved path, so a second member name still resolves here."""
    root = tmp_path / "monorepo"
    owner = make_ve_tree(root / "lib", artifacts=ALL_ARTIFACT_DIRS)
    consumer = make_ve_tree(root / "app", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(root, {"lib": "lib", "lib_alias": "lib", "app": "app"})
    write_artifact(owner, ArtifactType.SUBSYSTEM, "baseline")
    create_peer_yaml(
        project_path=consumer,
        short_name="baseline",
        member="lib_alias",
        external_artifact_id="baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    report = consumers_of(root, owner, "baseline")

    assert [edge.member for edge in report.peers] == ["app"]


def test_cross_repo_pointer_is_reported_apart_from_peers(workspace_trees):
    """A `repo:` pointer with the same id is reported, but never as a peer edge."""
    root, owner, viz, rsv2 = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    write_raw_pointer(
        rsv2,
        ArtifactType.SUBSYSTEM,
        "commitment_baseline",
        {
            "artifact_type": "subsystem",
            "artifact_id": "commitment_baseline",
            "repo": "acme/architecture",
            "track": "main",
            "why": "reads the hub copy",
        },
    )

    report = consumers_of(root, owner, "commitment_baseline")

    assert [edge.member for edge in report.peers] == ["viz"]
    assert [edge.member for edge in report.cross_repo] == ["rsv2"]
    assert report.cross_repo[0].target_display == "acme/architecture"
    assert report.cross_repo[0].why == "reads the hub copy"


def test_pointer_at_unregistered_member_is_unresolved_not_dropped(workspace_trees):
    """A pointer at a member the manifest never names must be visible as broken."""
    root, _, viz, _ = workspace_trees
    write_raw_pointer(
        viz,
        ArtifactType.SUBSYSTEM,
        "ghost_ref",
        {
            "artifact_type": "subsystem",
            "artifact_id": "commitment_baseline",
            "tree": "ghost",
        },
    )

    scan = scan_interest_edges(load_workspace(root))
    ghost = [edge for edge in scan.edges if edge.ref.tree == "ghost"]

    assert len(ghost) == 1
    assert ghost[0].target_dir is None
    assert "ghost" in ghost[0].unresolved_reason


def test_malformed_pointer_is_collected_not_raised(workspace_trees):
    """One unparseable external.yaml must not abort a workspace-wide query."""
    root, owner, viz, rsv2 = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    write_raw_pointer(
        rsv2,
        ArtifactType.SUBSYSTEM,
        "broken",
        {"artifact_type": "subsystem", "artifact_id": "commitment_baseline"},
    )

    report = consumers_of(root, owner, "commitment_baseline")

    assert [edge.member for edge in report.peers] == ["viz"]
    assert len(report.malformed) == 1
    assert report.malformed[0].pointer_rel == "apps/rsv2/docs/subsystems/broken"


def test_pointer_disagreeing_with_its_own_directory_keeps_both_facts(workspace_trees):
    """A pointer's declared target type addresses; its location stays reportable."""
    root, owner, viz, _ = workspace_trees
    write_raw_pointer(
        viz,
        ArtifactType.CHUNK,
        "misfiled",
        {
            "artifact_type": "subsystem",
            "artifact_id": "commitment_baseline",
            "tree": "pybusiness",
        },
    )

    report = consumers_of(root, owner, "commitment_baseline")

    assert [edge.member for edge in report.peers] == ["viz"]
    edge = report.peers[0]
    assert edge.pointer_type == ArtifactType.CHUNK
    assert edge.ref.artifact_type == ArtifactType.SUBSYSTEM
    assert edge.qualified_pointer == "viz::docs/chunks/misfiled"


def test_pointer_error_is_reported_on_a_single_line(workspace_trees):
    """A row that carries an error must still be a row."""
    root, owner, viz, _ = workspace_trees
    write_raw_pointer(
        viz,
        ArtifactType.CHUNK,
        "targetless",
        {"artifact_type": "chunk", "artifact_id": "whoops"},
    )

    scan = scan_interest_edges(load_workspace(root))

    assert len(scan.malformed) == 1
    message = scan.malformed[0].message
    assert "\n" not in message
    assert "exactly one of" in message


def test_workspace_listing_keeps_one_row_per_artifact(workspace_trees):
    """An unreadable pointer cannot smear a listing across several lines."""
    root, owner, viz, _ = workspace_trees
    write_artifact(owner, ArtifactType.CHUNK, "baseline_calc")
    write_raw_pointer(
        viz,
        ArtifactType.CHUNK,
        "targetless",
        {"artifact_type": "chunk", "artifact_id": "whoops"},
    )

    result = run(["chunk", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    rows = [line for line in result.output.splitlines() if line.strip()]
    assert len(rows) == 2
    assert any(row.startswith("viz::docs/chunks/targetless [PARSE ERROR:") for row in rows)


def test_consumers_of_a_deleted_artifact_are_still_enumerated(workspace_trees):
    """Pointers at an artifact that is gone are exactly what needs finding."""
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="run_rate_split",
        member="pybusiness",
        external_artifact_id="run_rate_split",
        artifact_type=ArtifactType.CHUNK,
        why="depends on the split rules",
    )

    report = consumers_of(root, owner, "run_rate_split", ArtifactType.CHUNK)

    assert [edge.member for edge in report.peers] == ["viz"]
    assert report.target_exists is False


def test_scan_covers_every_artifact_type(workspace_trees):
    """Interest edges are not a chunks-only concept."""
    root, _, viz, _ = workspace_trees
    for artifact_type in ArtifactType:
        create_peer_yaml(
            project_path=viz,
            short_name=f"target_{artifact_type.value}",
            member="pybusiness",
            external_artifact_id=f"target_{artifact_type.value}",
            artifact_type=artifact_type,
        )

    scan = scan_interest_edges(load_workspace(root))

    assert {edge.ref.artifact_type for edge in scan.edges} == set(ArtifactType)


def test_one_scan_answers_many_artifacts(workspace_trees):
    """The reuse path a validator needs: walk once, ask about everything."""
    root, owner, viz, rsv2 = workspace_trees
    write_artifact(owner, ArtifactType.SUBSYSTEM, "rate_cards")
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    create_peer_yaml(
        project_path=rsv2,
        short_name="rate_cards",
        member="pybusiness",
        external_artifact_id="rate_cards",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    ws = load_workspace(root)
    scan = scan_interest_edges(ws)
    answers = {
        artifact_id: [
            edge.member
            for edge in find_consumers(
                ws,
                artifact_type=ArtifactType.SUBSYSTEM,
                artifact_id=artifact_id,
                owner_root=owner,
                scan=scan,
            ).peers
        ]
        for artifact_id in ("commitment_baseline", "rate_cards", "never_existed")
    }

    assert answers == {
        "commitment_baseline": ["viz"],
        "rate_cards": ["rsv2"],
        "never_existed": [],
    }


def test_unregistered_owning_tree_has_no_owner_member(tmp_path):
    """An enclosing member is not the owner: nothing can point at this tree."""
    root = tmp_path / "monorepo"
    make_ve_tree(root, artifacts=ALL_ARTIFACT_DIRS)
    nested = make_ve_tree(root / "packages" / "nested", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(root, {"root": "."})
    write_artifact(nested, ArtifactType.SUBSYSTEM, "baseline")

    report = consumers_of(root, nested, "baseline")

    assert report.owner_member is None


def test_iter_member_trees_lists_an_aliased_tree_once(tmp_path):
    """Two names for one path is one tree to walk, not two."""
    root = tmp_path / "monorepo"
    make_ve_tree(root / "lib", artifacts=ALL_ARTIFACT_DIRS)
    make_ve_tree(root / "app", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(root, {"lib": "lib", "lib_alias": "lib", "app": "app"})

    walked = list(iter_member_trees(load_workspace(root)))

    assert [member.name for member, _ in walked] == ["lib", "app"]


# ---------------------------------------------------------------------------
# CLI: ve artifact consumers
# ---------------------------------------------------------------------------


def run(args):
    """Invoke the CLI with a fresh runner."""
    return CliRunner().invoke(cli, args)


def test_consumers_command_reports_member_pointer_and_why(workspace_trees):
    """The case-study question: who reads this subsystem, and for what?"""
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="renders the realized-savings baseline",
    )

    result = run(
        [
            "artifact",
            "consumers",
            "docs/subsystems/commitment_baseline",
            "--project-dir",
            str(owner),
        ]
    )

    assert result.exit_code == 0, result.output
    assert "viz" in result.output
    assert "apps/viz/docs/subsystems/commitment_baseline" in result.output
    assert "renders the realized-savings baseline" in result.output


def test_consumers_command_accepts_a_bare_artifact_name(workspace_trees):
    """The flexible path forms `normalize_artifact_path` supports all work."""
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )

    for form in ("commitment_baseline", "subsystems/commitment_baseline"):
        result = run(["artifact", "consumers", form, "--project-dir", str(owner)])
        assert result.exit_code == 0, result.output
        assert "viz" in result.output


def test_consumers_command_defaults_to_the_tree_it_is_run_from(
    workspace_trees, monkeypatch
):
    """Without --project-dir the owning tree is the cwd, not the workspace root.

    A relative path is resolved against the workspace root by manifest lookup, so
    a naive default would silently report on the root tree - misresolution of
    exactly the kind this addressing model exists to remove.
    """
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="renders the baseline",
    )
    monkeypatch.chdir(owner)

    result = run(["artifact", "consumers", "docs/subsystems/commitment_baseline"])

    assert result.exit_code == 0, result.output
    assert "Owner: pybusiness" in result.output
    assert "viz" in result.output


def test_consumers_command_distinguishes_no_consumers_from_no_manifest(workspace_trees):
    """"Nobody points at this" is an answer; "there is no registry" is not."""
    root, owner, _, _ = workspace_trees

    answered = run(
        ["artifact", "consumers", "commitment_baseline", "--project-dir", str(owner)]
    )

    assert answered.exit_code == 0, answered.output
    assert "no" in answered.output.lower()
    assert "consumer" in answered.output.lower()


def test_consumers_command_without_a_manifest_points_at_workspace_init(tmp_path):
    """Without a manifest the query is unanswerable, and says how to fix that."""
    lone = make_ve_tree(tmp_path / "solo", artifacts=ALL_ARTIFACT_DIRS)
    write_artifact(lone, ArtifactType.SUBSYSTEM, "baseline")

    result = run(["artifact", "consumers", "baseline", "--project-dir", str(lone)])

    assert result.exit_code == 1
    assert "ve workspace init" in result.output


def test_consumers_command_rejects_an_unregistered_owning_tree(tmp_path):
    """No peer pointer can name an unregistered tree, so say that plainly."""
    root = tmp_path / "monorepo"
    make_ve_tree(root / "lib", artifacts=ALL_ARTIFACT_DIRS)
    stranger = make_ve_tree(root / "apps" / "stranger", artifacts=ALL_ARTIFACT_DIRS)
    write_workspace_manifest(root, {"lib": "lib"})
    write_artifact(stranger, ArtifactType.SUBSYSTEM, "baseline")

    result = run(["artifact", "consumers", "baseline", "--project-dir", str(stranger)])

    assert result.exit_code == 1
    assert "ve workspace add" in result.output


def test_consumers_command_labels_cross_repo_pointers_separately(workspace_trees):
    """Certain (peer) and heuristic (id-matched repo) answers stay apart."""
    root, owner, viz, rsv2 = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
    )
    write_raw_pointer(
        rsv2,
        ArtifactType.SUBSYSTEM,
        "commitment_baseline",
        {
            "artifact_type": "subsystem",
            "artifact_id": "commitment_baseline",
            "repo": "acme/architecture",
        },
    )

    result = run(["artifact", "consumers", "commitment_baseline", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    peer_section, marker, repo_section = result.output.partition("Cross-repo pointers")
    assert marker, result.output
    assert "viz" in peer_section
    assert "rsv2" not in peer_section
    assert "rsv2" in repo_section
    assert "acme/architecture" in repo_section
    assert "artifact id" in repo_section


def test_consumers_command_json_reports_flavor_and_why(workspace_trees):
    """JSON output carries the fields a caller would otherwise re-derive."""
    import json

    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="commitment_baseline",
        member="pybusiness",
        external_artifact_id="commitment_baseline",
        artifact_type=ArtifactType.SUBSYSTEM,
        why="renders the baseline",
    )

    result = run(
        [
            "artifact",
            "consumers",
            "commitment_baseline",
            "--project-dir",
            str(owner),
            "--json",
        ]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["artifact_id"] == "commitment_baseline"
    assert payload["owner"] == "pybusiness"
    assert [c["member"] for c in payload["consumers"]] == ["viz"]
    assert payload["consumers"][0]["why"] == "renders the baseline"
    assert payload["consumers"][0]["flavor"] == "peer"


def test_consumers_command_warns_when_the_artifact_is_missing(workspace_trees):
    """A dangling target is worth saying out loud, not worth refusing over."""
    root, owner, viz, _ = workspace_trees
    create_peer_yaml(
        project_path=viz,
        short_name="run_rate_split",
        member="pybusiness",
        external_artifact_id="run_rate_split",
        artifact_type=ArtifactType.CHUNK,
    )

    result = run(
        [
            "artifact",
            "consumers",
            "docs/chunks/run_rate_split",
            "--project-dir",
            str(owner),
        ]
    )

    assert result.exit_code == 0, result.output
    assert "viz" in result.output
    assert "does not exist" in result.output


# ---------------------------------------------------------------------------
# CLI: --workspace aggregation
# ---------------------------------------------------------------------------


@pytest.fixture
def listable_workspace(workspace_trees):
    """Owner and consumer trees each holding artifacts of their own."""
    root, owner, viz, rsv2 = workspace_trees
    write_artifact(owner, ArtifactType.CHUNK, "baseline_calc", status="ACTIVE")
    write_artifact(viz, ArtifactType.CHUNK, "baseline_chart", status="FUTURE")
    write_artifact(viz, ArtifactType.SUBSYSTEM, "chart_layer")
    return root, owner, viz, rsv2


def test_chunk_list_workspace_lists_each_tree_once_with_labels(listable_workspace):
    """Aggregation, not promotion: both trees' chunks in one qualified listing."""
    root, owner, _, _ = listable_workspace

    result = run(["chunk", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert result.output.count("pybusiness::docs/chunks/baseline_calc") == 1
    assert result.output.count("viz::docs/chunks/baseline_chart") == 1
    assert "ACTIVE" in result.output
    assert "FUTURE" in result.output


def test_chunk_list_workspace_works_from_any_member(listable_workspace, monkeypatch):
    """The manifest is found by walking up, so any tree is a valid vantage point."""
    root, _, viz, _ = listable_workspace
    monkeypatch.chdir(viz)

    result = run(["chunk", "list", "--workspace"])

    assert result.exit_code == 0, result.output
    assert "pybusiness::docs/chunks/baseline_calc" in result.output
    assert "viz::docs/chunks/baseline_chart" in result.output


def test_chunk_list_workspace_honors_status_filters(listable_workspace):
    """The useful workspace query is "what is queued anywhere?"."""
    root, owner, _, _ = listable_workspace

    result = run(["chunk", "list", "--workspace", "--future", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert "viz::docs/chunks/baseline_chart" in result.output
    assert "baseline_calc" not in result.output


def test_chunk_list_workspace_shows_pointer_targets(listable_workspace):
    """A pointer row reports the tree it points at, as the single-tree list does."""
    root, owner, viz, _ = listable_workspace
    create_peer_yaml(
        project_path=viz,
        short_name="baseline_calc",
        member="pybusiness",
        external_artifact_id="baseline_calc",
        artifact_type=ArtifactType.CHUNK,
    )

    result = run(["chunk", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert "viz::docs/chunks/baseline_calc [EXTERNAL: tree:pybusiness]" in result.output


def test_chunk_list_workspace_json_labels_the_owning_member(listable_workspace):
    """JSON consumers need the owning tree without parsing a row string."""
    import json

    root, owner, _, _ = listable_workspace

    result = run(["chunk", "list", "--workspace", "--json", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    by_name = {row["name"]: row for row in payload}
    assert by_name["baseline_calc"]["member"] == "pybusiness"
    assert by_name["baseline_chart"]["member"] == "viz"


def test_chunk_list_workspace_json_omits_uncomputed_tips(listable_workspace):
    """Aggregation does not compute tips, so it must not report is_tip: false."""
    import json

    root, owner, _, _ = listable_workspace

    result = run(["chunk", "list", "--workspace", "--json", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload
    assert all("is_tip" not in row for row in payload)


def test_chunk_list_workspace_without_a_manifest_errors(tmp_path):
    """--workspace aggregates what a manifest names; without one, say so."""
    lone = make_ve_tree(tmp_path / "solo", artifacts=ALL_ARTIFACT_DIRS)
    write_artifact(lone, ArtifactType.CHUNK, "only_chunk")

    result = run(["chunk", "list", "--workspace", "--project-dir", str(lone)])

    assert result.exit_code == 1
    assert "ve workspace init" in result.output


def test_chunk_list_workspace_rejects_single_tree_cursor_flags(listable_workspace):
    """"The current chunk" has no aggregate answer; refuse rather than pick one."""
    root, owner, _, _ = listable_workspace

    result = run(
        ["chunk", "list", "--workspace", "--current", "--project-dir", str(owner)]
    )

    assert result.exit_code == 1
    assert "--workspace" in result.output


def test_chunk_list_workspace_warns_about_a_missing_member_path(listable_workspace):
    """A registered tree that is gone is reported; the rest still list."""
    root, owner, _, _ = listable_workspace
    write_workspace_manifest(
        root,
        {
            "pybusiness": "packages/libs/pybusiness",
            "vanished": "packages/libs/vanished",
        },
    )

    result = run(["chunk", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert "vanished" in result.output
    assert "pybusiness::docs/chunks/baseline_calc" in result.output


def test_workspace_listing_writes_nothing_into_member_trees(listable_workspace):
    """A browse query must not mutate 29 trees to answer a question."""
    root, owner, viz, _ = listable_workspace

    result = run(["chunk", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert not (owner / ".artifact-order.json").exists()
    assert not (viz / ".artifact-order.json").exists()


def test_subsystem_list_workspace_aggregates_across_trees(listable_workspace):
    """Subsystem browsability comes from aggregation too."""
    root, owner, _, _ = listable_workspace

    result = run(["subsystem", "list", "--workspace", "--project-dir", str(owner)])

    assert result.exit_code == 0, result.output
    assert result.output.count("pybusiness::docs/subsystems/commitment_baseline") == 1
    assert result.output.count("viz::docs/subsystems/chart_layer") == 1


def test_subsystem_list_workspace_without_a_manifest_errors(tmp_path):
    """Same failure mode as the chunk listing, same instruction."""
    lone = make_ve_tree(tmp_path / "solo", artifacts=ALL_ARTIFACT_DIRS)
    write_artifact(lone, ArtifactType.SUBSYSTEM, "only_subsystem")

    result = run(["subsystem", "list", "--workspace", "--project-dir", str(lone)])

    assert result.exit_code == 1
    assert "ve workspace init" in result.output
