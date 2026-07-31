"""Tests for the evidence-of-absence query and the deletion-grant ledger.

# Chunk: docs/chunks/crossref_absence_evidence - Absence query + authorized-deletion disposition

Three layers:

1. **The `ve exists` query** — "does this name (path or symbol) exist anywhere
   I can see?" Absence must be evidence (scope and counts stated), a moved
   file must be distinguishable from a deleted one, and symbol presence must
   agree with the workspace validator's conservative whole-word semantics.
2. **The deletion ledger** — `ve deletion record` writes an operator-attributed
   grant into `docs/trunk/DELETIONS.md` so a reviewer sees the grant in the
   same diff that removes the reference.
3. **The skill contract** — both validate-fix skills name the
   authorized-deletion disposition and the commands that implement it.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from click.testing import CliRunner

from conftest import make_ve_tree, make_workspace
from test_plugin_manifest import REPO_ROOT
from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def source(path: pathlib.Path, *lines: str) -> pathlib.Path:
    """Write a source file with the given lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines))
    return path


@pytest.fixture
def workspace(tmp_path):
    """A two-member workspace with a source file and an artifact directory."""
    root = tmp_path / "ws"
    make_workspace(root, {"alpha": "packages/alpha", "beta": "packages/beta"})
    source(
        root / "packages" / "alpha" / "src" / "mod.py",
        "class RealThing:",
        "    def compute_savings(self):",
        "        return foo_bar",
    )
    artifact_dir = root / "packages" / "alpha" / "docs" / "chunks" / "my_feature"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "GOAL.md").write_text("---\nstatus: ACTIVE\n---\n")
    (root / "packages" / "beta" / "requirements.txt").write_text("click\n")
    return root


def run_exists(root: pathlib.Path, name: str, *extra: str):
    """Invoke `ve exists NAME --dir root [extra...]`."""
    return CliRunner().invoke(cli, ["exists", name, "--dir", str(root), *extra])


def exists_json(root: pathlib.Path, name: str) -> dict:
    result = run_exists(root, name, "--format", "json")
    return json.loads(result.output), result.exit_code


# ---------------------------------------------------------------------------
# `ve exists` — path queries
# ---------------------------------------------------------------------------


def test_existing_path_is_a_path_match_and_exits_zero(workspace):
    report, exit_code = exists_json(workspace, "src/mod.py")
    assert exit_code == 0
    assert report["found"] is True
    assert any(
        m["path"] == "packages/alpha/src/mod.py" for m in report["path_matches"]
    )


def test_non_source_extensions_are_visible_to_path_queries(workspace):
    """Field cases were requirements.txt and Dockerfile, not .py files."""
    report, exit_code = exists_json(workspace, "requirements.txt")
    assert exit_code == 0
    assert any(
        m["path"] == "packages/beta/requirements.txt" for m in report["path_matches"]
    )


def test_absence_is_evidence_scope_and_counts_stated(workspace):
    result = run_exists(workspace, "nope/never.py")
    assert result.exit_code == 1
    assert "0 match" in result.output or "No match" in result.output.lower() or "absent" in result.output.lower()
    # The claim is backed by fact: what was scanned, and from where.
    assert "files" in result.output
    assert str(workspace.resolve()) in result.output

    report, exit_code = exists_json(workspace, "nope/never.py")
    assert exit_code == 1
    assert report["found"] is False
    assert report["counts"]["files_scanned"] > 0
    assert report["scope"]["root"] == str(workspace.resolve())


def test_moved_file_is_a_basename_match_not_a_path_match(workspace):
    """Same final name at a different path is 'moved', not 'still there'."""
    report, exit_code = exists_json(workspace, "packages/beta/src/mod.py")
    assert exit_code == 0  # something matched: evidence of a move
    assert report["path_matches"] == []
    assert any(
        m["path"] == "packages/alpha/src/mod.py" for m in report["basename_matches"]
    )


def test_directory_names_match_identifier_queries(workspace):
    """Artifact directory names are findable by bare name."""
    report, exit_code = exists_json(workspace, "my_feature")
    assert exit_code == 0
    assert any(
        m["path"] == "packages/alpha/docs/chunks/my_feature"
        for m in report["path_matches"]
    )


# ---------------------------------------------------------------------------
# `ve exists` — symbol queries
# ---------------------------------------------------------------------------


def test_defined_symbol_is_found_with_file_and_line(workspace):
    report, exit_code = exists_json(workspace, "RealThing")
    assert exit_code == 0
    assert any(
        m["path"] == "packages/alpha/src/mod.py" and m["line"] == 1
        for m in report["symbol_matches"]
    )


def test_absent_symbol_reports_absence(workspace):
    report, exit_code = exists_json(workspace, "AbsentThing")
    assert exit_code == 1
    assert report["found"] is False
    assert report["symbol_matches"] == []


def test_symbol_match_is_whole_word_like_the_validator(workspace):
    """`foo_bar` in a file must not count as presence of `foo`."""
    report, exit_code = exists_json(workspace, "foo")
    assert exit_code == 1
    assert report["symbol_matches"] == []


def test_file_hash_symbol_query_checks_both_parts(workspace):
    report, exit_code = exists_json(workspace, "src/mod.py#RealThing")
    assert exit_code == 0
    assert any(
        m["path"] == "packages/alpha/src/mod.py" for m in report["path_matches"]
    )
    assert any(
        m["path"] == "packages/alpha/src/mod.py" for m in report["symbol_matches"]
    )


def test_symbol_query_takes_last_double_colon_component(workspace):
    report, exit_code = exists_json(workspace, "src/mod.py#RealThing::compute_savings")
    assert exit_code == 0
    assert any(
        m["line"] == 2 for m in report["symbol_matches"]
    )


# ---------------------------------------------------------------------------
# `ve exists` — re-export mentions are classified, not counted as presence
# Chunk: docs/chunks/crossref_reexport_absence - Query stays in agreement
# ---------------------------------------------------------------------------


def test_reexport_mention_is_classified_apart_from_symbol_matches(workspace):
    """The defining file is a symbol match; the re-exporting file is not."""
    source(
        workspace / "packages" / "alpha" / "src" / "__init__.py",
        "from .mod import RealThing  # noqa: F401",
    )
    report, exit_code = exists_json(workspace, "RealThing")
    assert exit_code == 0
    assert any(
        m["path"] == "packages/alpha/src/mod.py" for m in report["symbol_matches"]
    )
    assert all(
        m["path"] != "packages/alpha/src/__init__.py"
        for m in report["symbol_matches"]
    )
    assert any(
        m["path"] == "packages/alpha/src/__init__.py"
        for m in report["reexport_matches"]
    )


def test_name_surviving_only_as_reexport_is_still_evidence(workspace):
    """A deleted definition leaves the re-export as the moved-to breadcrumb."""
    source(
        workspace / "packages" / "beta" / "src" / "__init__.py",
        "from great_library import GoneThing",
    )
    report, exit_code = exists_json(workspace, "GoneThing")
    assert exit_code == 0
    assert report["found"] is True
    assert report["symbol_matches"] == []
    (mention,) = report["reexport_matches"]
    assert mention["path"] == "packages/beta/src/__init__.py"


def test_text_output_renders_reexport_mentions_distinctly(workspace):
    source(
        workspace / "packages" / "beta" / "src" / "__init__.py",
        "from great_library import GoneThing",
    )
    result = run_exists(workspace, "GoneThing")
    assert result.exit_code == 0
    assert "Re-export" in result.output
    assert "Symbol matches" not in result.output


# ---------------------------------------------------------------------------
# `ve exists` — scope resolution
# ---------------------------------------------------------------------------


def test_without_a_manifest_scope_falls_back_to_the_enclosing_tree(tmp_path):
    tree = make_ve_tree(tmp_path / "solo")
    source(tree / "src" / "only.py", "class OnlyHere:")
    report, exit_code = exists_json(tree, "OnlyHere")
    assert exit_code == 0
    assert report["scope"]["root"] == str(tree.resolve())
    assert report["scope"]["kind"] == "tree"


def test_workspace_scope_names_the_workspace(workspace):
    report, _ = exists_json(workspace, "RealThing")
    assert report["scope"]["kind"] == "workspace"
    assert set(report["scope"]["members"]) == {"alpha", "beta"}


def test_json_report_shape_is_the_skill_contract(workspace):
    report, _ = exists_json(workspace, "RealThing")
    for key in (
        "query",
        "found",
        "scope",
        "path_matches",
        "basename_matches",
        "symbol_matches",
        "reexport_matches",
        "counts",
    ):
        assert key in report, f"JSON report missing '{key}'"
    assert report["query"] == "RealThing"
    assert "files_scanned" in report["counts"]
    assert "reexport_matches" in report["counts"]


# ---------------------------------------------------------------------------
# `ve deletion` — the recorded grant
# ---------------------------------------------------------------------------


def record(tree: pathlib.Path, reference: str, **fields):
    args = [
        "deletion",
        "record",
        reference,
        "--location",
        fields.get("location", "src/gone.py:12"),
        "--by",
        fields.get("by", "brian"),
        "--reason",
        fields.get("reason", "code deliberately deleted in the pricing rewrite"),
        "--project-dir",
        str(tree),
    ]
    if "evidence" in fields:
        args += ["--evidence", fields["evidence"]]
    return CliRunner().invoke(cli, args)


def test_first_record_creates_the_ledger_with_the_grant(tmp_path):
    tree = make_ve_tree(tmp_path / "proj")
    result = record(
        tree,
        "docs/chunks/retired_feature",
        evidence="ve exists retired_feature: absent across 42 files",
    )
    assert result.exit_code == 0, result.output
    assert "D001" in result.output

    ledger = tree / "docs" / "trunk" / "DELETIONS.md"
    assert ledger.is_file()
    content = ledger.read_text()
    assert "D001" in content
    assert "docs/chunks/retired_feature" in content
    assert "src/gone.py:12" in content
    assert "brian" in content
    assert "pricing rewrite" in content
    assert "absent across 42 files" in content


def test_second_record_appends_without_disturbing_the_first(tmp_path):
    tree = make_ve_tree(tmp_path / "proj")
    record(tree, "docs/chunks/first_gone")
    result = record(tree, "docs/chunks/second_gone", by="alex")
    assert result.exit_code == 0, result.output
    assert "D002" in result.output

    content = (tree / "docs" / "trunk" / "DELETIONS.md").read_text()
    assert "D001" in content and "docs/chunks/first_gone" in content
    assert "D002" in content and "docs/chunks/second_gone" in content


def test_deletion_list_round_trips_every_field(tmp_path):
    tree = make_ve_tree(tmp_path / "proj")
    record(
        tree,
        "docs/chunks/retired_feature",
        location="src/gone.py:12",
        by="brian",
        reason="code deliberately deleted in the pricing rewrite",
        evidence="ve exists retired_feature: absent across 42 files",
    )
    result = CliRunner().invoke(
        cli, ["deletion", "list", "--project-dir", str(tree), "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    entries = json.loads(result.output)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == "D001"
    assert entry["reference"] == "docs/chunks/retired_feature"
    assert entry["location"] == "src/gone.py:12"
    assert entry["authorized_by"] == "brian"
    assert "pricing rewrite" in entry["reason"]
    assert "absent across 42 files" in entry["evidence"]

    text = CliRunner().invoke(cli, ["deletion", "list", "--project-dir", str(tree)])
    assert "D001" in text.output
    assert "docs/chunks/retired_feature" in text.output


def test_recording_outside_a_ve_tree_fails_actionably(tmp_path):
    bare = tmp_path / "not_a_tree"
    bare.mkdir()
    result = record(bare, "docs/chunks/whatever")
    assert result.exit_code != 0
    assert "docs/trunk" in result.output or "VE tree" in result.output


def test_empty_ledger_list_is_not_an_error(tmp_path):
    tree = make_ve_tree(tmp_path / "proj")
    result = CliRunner().invoke(
        cli, ["deletion", "list", "--project-dir", str(tree), "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


# ---------------------------------------------------------------------------
# The skills name the disposition
# ---------------------------------------------------------------------------

WORKSPACE_SKILL = REPO_ROOT / "skills" / "workspace-validate-fix" / "SKILL.md"
SINGLE_TREE_SKILL = REPO_ROOT / "skills" / "validate-fix" / "SKILL.md"


@pytest.mark.parametrize("skill", [WORKSPACE_SKILL, SINGLE_TREE_SKILL])
def test_skills_name_the_authorized_deletion_disposition(skill):
    body = skill.read_text()
    assert "ve exists" in body, f"{skill} does not name the absence query"
    assert "ve deletion record" in body, f"{skill} does not name the grant command"
    assert "Authorized deletions" in body, (
        f"{skill} has no report section for the disposition"
    )


def test_workspace_skill_keeps_the_deletion_invariant_verbatim():
    """The grant is an exception to the invariant, not its repeal."""
    body = WORKSPACE_SKILL.read_text()
    assert "Never delete a reference" in body
