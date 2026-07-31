"""Tests for `ve refactor move` — evidence-backed rename propagation.

# Chunk: docs/chunks/crossref_refactor_move - Evidence-backed rename propagation

The field-tested guards are the test surface:

- git rename/deletion shas appear in the report as reviewable evidence;
- basename inference never fires without the immediate parent directory
  name matching (the `requirements.txt` near-miss);
- module→package splits resolve symbol anchors to their unique definer, or
  surface `implements:` prose with candidates when ambiguous;
- symbols with no successor anywhere in scope are the distinct
  NEVER_EXISTED disposition, backed by an absence basis;
- the tool refuses incomplete moves (old still on disk) and never touches
  HISTORICAL archaeology or prose bodies.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import pytest
from click.testing import CliRunner

from conftest import make_ve_tree
from refactor_move import (
    DISPOSITION_AMBIGUOUS,
    DISPOSITION_NEVER_EXISTED,
    DISPOSITION_REWRITTEN,
    RefactorMoveError,
    collect_references,
    execute_move,
    gather_git_evidence,
)
from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def git(repo: pathlib.Path, *args: str) -> str:
    """Run git in the repo, asserting success."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def make_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """A git-initialized VE tree."""
    root = tmp_path / "repo"
    root.mkdir()
    make_ve_tree(root, artifacts=("chunks", "subsystems"))
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    return root


def commit_all(repo: pathlib.Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


def write_source(path: pathlib.Path, content: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


def write_chunk(
    root: pathlib.Path,
    name: str,
    status: str = "ACTIVE",
    code_paths: list[str] | None = None,
    code_references: list[tuple[str, str]] | None = None,
    body: str = "# Goal\n",
) -> pathlib.Path:
    """Write a chunk GOAL.md with the given frontmatter."""
    lines = ["---", f"status: {status}"]
    if code_paths:
        lines.append("code_paths:")
        lines.extend(f"- {p}" for p in code_paths)
    if code_references:
        lines.append("code_references:")
        for ref, implements in code_references:
            lines.append(f"- ref: {ref}")
            lines.append(f"  implements: {implements}")
    lines.append("---")
    chunk_dir = root / "docs" / "chunks" / name
    chunk_dir.mkdir(parents=True, exist_ok=True)
    goal = chunk_dir / "GOAL.md"
    goal.write_text("\n".join(lines) + "\n" + body)
    return goal


def write_subsystem(
    root: pathlib.Path,
    name: str,
    code_references: list[tuple[str, str]],
    status: str = "DOCUMENTED",
) -> pathlib.Path:
    """Write a subsystem OVERVIEW.md with code_references."""
    lines = ["---", f"status: {status}", "code_references:"]
    for ref, implements in code_references:
        lines.append(f"- ref: {ref}")
        lines.append(f"  implements: {implements}")
    lines.append("---")
    sub_dir = root / "docs" / "subsystems" / name
    sub_dir.mkdir(parents=True, exist_ok=True)
    overview = sub_dir / "OVERVIEW.md"
    overview.write_text("\n".join(lines) + "\n# Overview\n")
    return overview


def run_move(root: pathlib.Path, old: str, new: str, *extra: str):
    return CliRunner().invoke(
        cli,
        ["refactor", "move", old, new, "--project-dir", str(root), *extra],
    )


# ---------------------------------------------------------------------------
# file → file rename
# ---------------------------------------------------------------------------


@pytest.fixture
def renamed_file_repo(tmp_path):
    """A repo where src/old.py was git-mv'd to src/shiny.py."""
    root = make_repo(tmp_path)
    write_source(
        root / "src" / "old.py",
        """\
        class Thing:
            def act(self):
                return 1
        """,
    )
    write_chunk(
        root,
        "feature",
        code_paths=["src/old.py"],
        code_references=[("src/old.py#Thing", "The core thing")],
    )
    commit_all(root, "initial")
    git(root, "mv", "src/old.py", "src/shiny.py")
    rename_sha = commit_all(root, "rename old.py to shiny.py")
    return root, rename_sha


def test_file_rename_rewrites_code_paths_and_references(renamed_file_repo):
    root, _ = renamed_file_repo
    report = execute_move(root, "src/old.py", "src/shiny.py")

    rewritten = report.by_disposition(DISPOSITION_REWRITTEN)
    assert {d.new_value for d in rewritten} == {
        "src/shiny.py",
        "src/shiny.py#Thing",
    }
    goal = (root / "docs" / "chunks" / "feature" / "GOAL.md").read_text()
    assert "src/old.py" not in goal
    assert "- src/shiny.py" in goal
    assert "ref: src/shiny.py#Thing" in goal


def test_file_rename_report_carries_git_and_ast_evidence(renamed_file_repo):
    root, rename_sha = renamed_file_repo
    report = execute_move(root, "src/old.py", "src/shiny.py", apply=False)

    assert report.git_evidence.detected
    assert any(
        sha == rename_sha and src == "src/old.py" and dst == "src/shiny.py"
        for sha, src, dst in report.git_evidence.rename_records
    )
    symbol_decision = next(
        d for d in report.decisions if d.entry.symbol_part == "Thing"
    )
    assert any("AST" in line for line in symbol_decision.evidence)
    assert any(rename_sha[:12] in line for line in symbol_decision.evidence)


def test_dry_run_writes_nothing(renamed_file_repo):
    root, _ = renamed_file_repo
    before = (root / "docs" / "chunks" / "feature" / "GOAL.md").read_text()
    result = run_move(root, "src/old.py", "src/shiny.py", "--dry-run")
    assert result.exit_code == 0
    assert "dry run" in result.output
    after = (root / "docs" / "chunks" / "feature" / "GOAL.md").read_text()
    assert before == after


def test_json_report_shape(renamed_file_repo):
    root, _ = renamed_file_repo
    result = run_move(
        root, "src/old.py", "src/shiny.py", "--format", "json", "--dry-run"
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["old"] == "src/old.py"
    assert report["new"] == "src/shiny.py"
    assert report["applied"] is False
    assert report["git_evidence"]["detected"] is True
    assert report["counts"] == {
        "rewritten": 2,
        "ambiguous": 0,
        "never_existed": 0,
    }
    for decision in report["decisions"]:
        assert {"artifact", "field", "value", "disposition", "evidence"} <= set(
            decision
        )


# ---------------------------------------------------------------------------
# Guardrails: incomplete moves, missing destinations, archaeology
# ---------------------------------------------------------------------------


def test_refuses_when_old_still_exists(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "src" / "still_here.py", "X = 1\n")
    write_source(root / "src" / "other.py", "Y = 2\n")
    with pytest.raises(RefactorMoveError, match="still exists"):
        execute_move(root, "src/still_here.py", "src/other.py")


def test_refuses_when_new_does_not_exist(tmp_path):
    root = make_repo(tmp_path)
    with pytest.raises(RefactorMoveError, match="does not exist"):
        execute_move(root, "src/gone.py", "src/never.py")


def test_cli_reports_refusal_and_exits_nonzero(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "src" / "still_here.py", "X = 1\n")
    write_source(root / "src" / "other.py", "Y = 2\n")
    result = run_move(root, "src/still_here.py", "src/other.py")
    assert result.exit_code == 1
    assert "still exists" in result.output


def test_historical_chunks_are_left_as_archaeology(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "src" / "shiny.py", "class Thing:\n    pass\n")
    write_chunk(
        root,
        "ancient",
        status="HISTORICAL",
        code_references=[("src/old.py#Thing", "Long-gone implementation")],
    )
    entries = collect_references(root, "src/old.py")
    assert entries == []


def test_project_qualified_refs_are_skipped(tmp_path):
    root = make_repo(tmp_path)
    write_chunk(
        root,
        "crossrepo",
        code_references=[("acme/lib::src/old.py#Thing", "Sibling repo code")],
    )
    entries = collect_references(root, "src/old.py")
    assert entries == []


def test_prose_mentions_of_old_path_are_not_touched(renamed_file_repo):
    root, _ = renamed_file_repo
    goal_path = root / "docs" / "chunks" / "feature" / "GOAL.md"
    goal_path.write_text(
        goal_path.read_text() + "\nThe file src/old.py held the prototype.\n"
    )
    execute_move(root, "src/old.py", "src/shiny.py")
    assert "The file src/old.py held the prototype." in goal_path.read_text()


# ---------------------------------------------------------------------------
# directory → directory move, and the parent-dir guard
# ---------------------------------------------------------------------------


def test_directory_move_maps_path_suffixes(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "pkg" / "core" / "engine.py", "class Engine:\n    pass\n")
    write_chunk(
        root,
        "engine",
        code_paths=["lib/core/engine.py"],
        code_references=[("lib/core/engine.py#Engine", "The engine")],
    )
    commit_all(root, "initial")
    report = execute_move(root, "lib", "pkg")
    rewritten = report.by_disposition(DISPOSITION_REWRITTEN)
    assert {d.new_value for d in rewritten} == {
        "pkg/core/engine.py",
        "pkg/core/engine.py#Engine",
    }


def test_basename_inference_requires_matching_parent_directory(tmp_path):
    """The requirements.txt near-miss: a unique basename match in a different
    package must NOT be accepted."""
    root = make_repo(tmp_path)
    # Old ref: lib/update-potential-savings/requirements.txt. Under the new
    # root the only requirements.txt lives in a *different* package.
    write_source(
        root / "pkg" / "other-package" / "requirements.txt", "click\n"
    )
    write_chunk(
        root,
        "savings",
        code_paths=["lib/update-potential-savings/requirements.txt"],
    )
    report = execute_move(root, "lib", "pkg", apply=False)
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_AMBIGUOUS
    assert decision.new_value is None
    # The other package's file surfaces as a *candidate* for the operator —
    # neither auto-accepted (the near-miss) nor mislabeled never-existed.
    assert "pkg/other-package/requirements.txt" in decision.candidates
    assert decision.absence_basis is not None


def test_symbolless_entry_with_no_path_anywhere_is_never_existed(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "pkg" / "core" / "engine.py", "class Engine:\n    pass\n")
    write_chunk(root, "phantom_path", code_paths=["lib/tools/imagined.cfg"])
    commit_all(root, "initial")
    report = execute_move(root, "lib", "pkg")
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_NEVER_EXISTED
    assert decision.absence_basis is not None
    assert any("never-existed" in line for line in decision.evidence)


def test_basename_inference_accepts_matching_parent_directory(tmp_path):
    root = make_repo(tmp_path)
    # The package moved deeper: lib/tools/cli.py -> pkg/nested/tools/cli.py.
    write_source(root / "pkg" / "nested" / "tools" / "cli.py", "def main():\n    pass\n")
    write_chunk(root, "tools", code_paths=["lib/tools/cli.py"])
    report = execute_move(root, "lib", "pkg")
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_REWRITTEN
    assert decision.new_value == "pkg/nested/tools/cli.py"
    assert any("parent-dir guard" in line for line in decision.evidence)


# ---------------------------------------------------------------------------
# module → package split
# ---------------------------------------------------------------------------


@pytest.fixture
def split_repo(tmp_path):
    """src/models.py split into the src/models/ package."""
    root = make_repo(tmp_path)
    write_source(
        root / "src" / "models.py",
        """\
        class ChunkThing:
            pass

        class SharedThing:
            pass

        LIMITS = {"a": 1}
        """,
    )
    write_chunk(
        root,
        "modeling",
        code_paths=["src/models.py"],
        code_references=[
            ("src/models.py#ChunkThing", "Chunk model"),
            ("src/models.py#LIMITS", "Shared limit table"),
        ],
    )
    write_subsystem(
        root,
        "artifacts",
        code_references=[("src/models.py#SharedThing", "Shared base model")],
    )
    commit_all(root, "initial")
    (root / "src" / "models.py").unlink()
    write_source(
        root / "src" / "models" / "chunk.py",
        """\
        from models.shared import SharedThing

        class ChunkThing(SharedThing):
            pass
        """,
    )
    write_source(
        root / "src" / "models" / "shared.py",
        """\
        class SharedThing:
            pass

        LIMITS = {"a": 1}
        """,
    )
    commit_all(root, "split models.py into a package")
    return root


def test_split_resolves_symbols_to_their_unique_definer(split_repo):
    report = execute_move(split_repo, "src/models.py", "src/models")
    new_values = {
        d.entry.raw: d.new_value
        for d in report.by_disposition(DISPOSITION_REWRITTEN)
    }
    assert new_values["src/models.py#ChunkThing"] == "src/models/chunk.py#ChunkThing"
    # Module-level assignments count as definitions (constants resolve to
    # their defining file, not to importers).
    assert new_values["src/models.py#LIMITS"] == "src/models/shared.py#LIMITS"
    # A symbol-less code_paths entry rewrites to the package directory.
    assert new_values["src/models.py"] == "src/models"


def test_split_rewrites_subsystem_overview_references(split_repo):
    execute_move(split_repo, "src/models.py", "src/models")
    overview = (
        split_repo / "docs" / "subsystems" / "artifacts" / "OVERVIEW.md"
    ).read_text()
    assert "ref: src/models/shared.py#SharedThing" in overview
    assert "src/models.py" not in overview


def test_split_deletion_sha_is_reported_as_evidence(split_repo):
    report = execute_move(split_repo, "src/models.py", "src/models", apply=False)
    assert report.git_evidence.deletion_sha is not None


def test_ambiguous_symbol_surfaces_implements_prose_and_candidates(tmp_path):
    root = make_repo(tmp_path)
    write_chunk(
        root,
        "dupes",
        code_references=[("src/models.py#Common", "Validates the frontmatter")],
    )
    write_source(root / "src" / "models" / "a.py", "class Common:\n    pass\n")
    write_source(root / "src" / "models" / "b.py", "class Common:\n    pass\n")
    commit_all(root, "initial")
    report = execute_move(root, "src/models.py", "src/models")
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_AMBIGUOUS
    assert set(decision.candidates) == {"src/models/a.py", "src/models/b.py"}
    assert decision.entry.implements == "Validates the frontmatter"
    # The entry is left untouched.
    goal = (root / "docs" / "chunks" / "dupes" / "GOAL.md").read_text()
    assert "ref: src/models.py#Common" in goal
    # And the CLI surfaces the prose at the decision point.
    result = run_move(root, "src/models.py", "src/models", "--dry-run")
    assert "implements: Validates the frontmatter" in result.output
    assert "candidate: src/models/a.py" in result.output


def test_symbol_found_elsewhere_in_scope_is_ambiguous_not_never_existed(tmp_path):
    root = make_repo(tmp_path)
    write_chunk(
        root,
        "wanderer",
        code_references=[("src/models.py#Wanderer", "Migrated helper")],
    )
    write_source(root / "src" / "models" / "core.py", "class Core:\n    pass\n")
    # The symbol's real successor lives outside the declared destination.
    write_source(root / "src" / "helpers.py", "class Wanderer:\n    pass\n")
    commit_all(root, "initial")
    report = execute_move(root, "src/models.py", "src/models")
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_AMBIGUOUS
    assert "src/helpers.py" in decision.candidates
    assert decision.absence_basis is not None


# ---------------------------------------------------------------------------
# NEVER_EXISTED disposition
# ---------------------------------------------------------------------------


def test_symbol_absent_everywhere_is_never_existed_with_absence_basis(tmp_path):
    root = make_repo(tmp_path)
    write_chunk(
        root,
        "phantom",
        code_references=[
            ("src/models.py#InventedSimulator", "Simulates originations")
        ],
    )
    write_source(root / "src" / "models" / "core.py", "class Core:\n    pass\n")
    commit_all(root, "initial")
    report = execute_move(root, "src/models.py", "src/models")
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_NEVER_EXISTED
    assert decision.absence_basis is not None
    assert decision.absence_basis["found"] is False
    assert decision.absence_basis["counts"]["files_scanned"] > 0
    # The disposition names reconstruct-or-drop, not a rename hunt.
    assert any("reconstruct-or-drop" in line.lower() for line in decision.evidence)
    # The reference itself is never deleted.
    goal = (root / "docs" / "chunks" / "phantom" / "GOAL.md").read_text()
    assert "ref: src/models.py#InventedSimulator" in goal
    # CLI points at the deletion ledger for the drop path.
    result = run_move(root, "src/models.py", "src/models", "--dry-run")
    assert "ve deletion record" in result.output


# ---------------------------------------------------------------------------
# Git evidence honesty
# ---------------------------------------------------------------------------


def test_move_without_git_history_is_reported_operator_asserted(tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    make_ve_tree(root, artifacts=("chunks", "subsystems"))
    write_source(root / "src" / "shiny.py", "class Thing:\n    pass\n")
    write_chunk(root, "feature", code_references=[("src/old.py#Thing", "Thing")])
    report = execute_move(root, "src/old.py", "src/shiny.py")
    assert not report.git_evidence.detected
    (decision,) = report.decisions
    assert decision.disposition == DISPOSITION_REWRITTEN
    assert any("operator-asserted" in line for line in decision.evidence)


def test_gather_git_evidence_finds_rename_records(tmp_path):
    root = make_repo(tmp_path)
    write_source(root / "a.py", "X = 1\n")
    commit_all(root, "initial")
    git(root, "mv", "a.py", "b.py")
    sha = commit_all(root, "rename")
    evidence = gather_git_evidence(root, "a.py", "b.py")
    assert evidence.rename_records == ((sha, "a.py", "b.py"),)
