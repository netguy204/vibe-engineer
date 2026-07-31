"""Tests for workspace-wide reference validation and `ve workspace validate`.

# Chunk: docs/chunks/federation_global_validator - Workspace validation tests
"""

from __future__ import annotations

import json
import pathlib

import pytest
from click.testing import CliRunner

from conftest import make_ve_tree, make_workspace, write_workspace_manifest
from models import ArtifactType
from ve import cli
from workspace import load_workspace
from workspace_validation import (
    FixClass,
    index_tree,
    validate_workspace,
    validate_workspace_at,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def artifact(tree: pathlib.Path, kind: str, name: str) -> pathlib.Path:
    """Create a local artifact directory with a main document."""
    directory = tree / "docs" / kind / name
    directory.mkdir(parents=True, exist_ok=True)
    main = "GOAL.md" if kind == "chunks" else "OVERVIEW.md"
    status = "ACTIVE" if kind == "chunks" else "DOCUMENTED"
    (directory / main).write_text(f"---\nstatus: {status}\n---\n\n# {name}\n")
    return directory


def pointer(
    tree: pathlib.Path,
    name: str,
    *,
    kind: str = "chunks",
    target_tree: str | None = None,
    repo: str | None = None,
    artifact_id: str | None = None,
    body: str | None = None,
) -> pathlib.Path:
    """Create an external.yaml pointer artifact (peer or cross-repo)."""
    directory = tree / "docs" / kind / name
    directory.mkdir(parents=True, exist_ok=True)
    if body is None:
        target = f"tree: {target_tree}" if target_tree else f"repo: {repo}\ntrack: main"
        artifact_type = "chunk" if kind == "chunks" else "subsystem"
        body = (
            f"artifact_type: {artifact_type}\n"
            f"artifact_id: {artifact_id or name}\n"
            f"{target}\n"
        )
    (directory / "external.yaml").write_text(body)
    return directory


def source(path: pathlib.Path, *lines: str) -> pathlib.Path:
    """Write a source file with the given lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines))
    return path


def validate(root: pathlib.Path):
    """Load the workspace at root and validate it."""
    return validate_workspace(load_workspace(root))


def of_class(report, fix_class: FixClass) -> list:
    """Defects of one fix class, in report order."""
    return [defect for defect in report.defects if defect.fix_class is fix_class]


def classes(report) -> list[FixClass]:
    """Fix classes of every reported defect, in report order."""
    return [defect.fix_class for defect in report.defects]


# ---------------------------------------------------------------------------
# Bare references: the nearest-enclosing-tree rule
# ---------------------------------------------------------------------------


def test_bare_ref_resolving_in_its_governing_tree_is_clean(tmp_path):
    """A bare ref whose artifact exists in the file's own tree is not a defect."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    artifact(lib, "chunks", "widget")
    source(lib / "widget.py", "# Chunk: docs/chunks/widget - the widget")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.ok
    assert report.references_checked == 1


def test_born_dangling_bare_ref_is_unresolvable_bare(tmp_path):
    """A bare ref resolvable from nowhere is reported with its file and line."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(
        lib / "rate.py",
        "import os",
        "# Chunk: docs/chunks/run_rate_split - never existed",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_BARE)
    assert defect.path == "packages/lib/rate.py"
    assert defect.line == 2
    assert defect.reference == "docs/chunks/run_rate_split"
    assert defect.candidates == ()
    assert defect.member == "lib"
    assert not report.ok


def test_bare_ref_resolving_in_another_tree_is_misrouted_with_a_candidate(tmp_path):
    """A bare ref that fails locally but resolves elsewhere names the candidate."""
    make_workspace(tmp_path, {"lib": "packages/lib", "arch": "architecture"})
    lib = tmp_path / "packages" / "lib"
    artifact(tmp_path / "architecture", "subsystems", "commitment_baseline")
    source(lib / "realized.py", "# Subsystem: docs/subsystems/commitment_baseline")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISROUTED_BARE)
    assert defect.path == "packages/lib/realized.py"
    assert defect.reference == "docs/subsystems/commitment_baseline"
    (candidate,) = defect.candidates
    assert candidate.member == "arch"
    assert candidate.qualifier == "arch::"
    assert "arch::docs/subsystems/commitment_baseline" in defect.message


def test_misrouted_bare_with_two_candidates_lists_both(tmp_path):
    """An ambiguous target lists every candidate so the fix is not guessed."""
    make_workspace(
        tmp_path, {"app": "app", "one": "packages/one", "two": "packages/two"}
    )
    artifact(tmp_path / "packages" / "one", "chunks", "shared")
    artifact(tmp_path / "packages" / "two", "chunks", "shared")
    source(tmp_path / "app" / "main.py", "# Chunk: docs/chunks/shared")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISROUTED_BARE)
    assert [candidate.member for candidate in defect.candidates] == ["one", "two"]


def test_candidate_in_an_unregistered_tree_carries_no_member_name(tmp_path):
    """An unregistered candidate tree cannot be qualified against until added."""
    make_workspace(tmp_path, {"app": "app"})
    make_ve_tree(tmp_path / "stray")
    artifact(tmp_path / "stray", "chunks", "orphan")
    source(tmp_path / "app" / "main.py", "# Chunk: docs/chunks/orphan")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISROUTED_BARE)
    (candidate,) = defect.candidates
    assert candidate.member is None
    assert candidate.qualifier is None
    assert candidate.path == "stray"
    assert "stray" in report.unregistered_trees


def test_unregistered_governing_tree_is_noted_but_does_not_gate(tmp_path):
    """References inside an unregistered tree still resolve, so it is a note."""
    make_workspace(tmp_path, {"app": "app"})
    stray = make_ve_tree(tmp_path / "stray")
    artifact(stray, "chunks", "local_work")
    source(stray / "code.py", "# Chunk: docs/chunks/local_work")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.ok
    assert report.unregistered_trees == ("stray",)


# ---------------------------------------------------------------------------
# Packages with no docs tree at all (GOAL: first-class)
# ---------------------------------------------------------------------------


def test_bare_ref_in_a_package_without_a_docs_tree_is_reported_not_skipped(tmp_path):
    """A file with no governing tree still has its bare refs classified."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "subsystems", "commitment_baseline")
    source(
        tmp_path / "backend-api-lib" / "client.py",
        "# Subsystem: docs/subsystems/commitment_baseline",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISROUTED_BARE)
    assert defect.path == "backend-api-lib/client.py"
    assert [candidate.member for candidate in defect.candidates] == ["lib"]
    assert "no governing tree" in defect.message


def test_qualified_ref_in_a_package_without_a_docs_tree_resolves(tmp_path):
    """Cross-tree vocabulary is usable from a package that has no tree at all."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "subsystems", "commitment_baseline")
    source(
        tmp_path / "backend-api-lib" / "client.py",
        "# Subsystem: lib::docs/subsystems/commitment_baseline",
    )

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.references_checked == 1


def test_unresolvable_bare_ref_without_a_governing_tree_is_class_one(tmp_path):
    """No tree anywhere has the artifact, so it is unresolvable, not misrouted."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(tmp_path / "plain" / "client.py", "# Chunk: docs/chunks/rsv2_model")

    report = validate(tmp_path)

    assert classes(report) == [FixClass.UNRESOLVABLE_BARE]


# ---------------------------------------------------------------------------
# Pointer-only trees: addressable targets, never governing roots
# ---------------------------------------------------------------------------


def test_pointer_only_member_is_a_valid_qualified_target(tmp_path):
    """A member with external.yaml stubs and no trunk can still be addressed."""
    write_workspace_manifest(tmp_path, {"app": "app", "ptr": "packages/ptr"})
    make_ve_tree(tmp_path / "app")
    pointer(tmp_path / "packages" / "ptr", "borrowed", repo="acme/hub")
    source(tmp_path / "app" / "main.py", "# Chunk: ptr::docs/chunks/borrowed")

    report = validate(tmp_path)

    assert report.defects == ()


def test_bare_ref_inside_a_pointer_only_tree_is_reported(tmp_path):
    """A pointer-only tree is not a governing root, so its bare refs are defects."""
    write_workspace_manifest(tmp_path, {"app": "app", "ptr": "packages/ptr"})
    make_ve_tree(tmp_path / "app")
    ptr = tmp_path / "packages" / "ptr"
    pointer(ptr, "borrowed", repo="acme/hub")
    source(ptr / "consumer.py", "# Chunk: docs/chunks/borrowed")

    report = validate(tmp_path)

    (defect,) = report.defects
    assert defect.fix_class is FixClass.MISROUTED_BARE
    assert [candidate.member for candidate in defect.candidates] == ["ptr"]
    assert "no governing tree" in defect.message


# ---------------------------------------------------------------------------
# Qualified references
# ---------------------------------------------------------------------------


def test_member_qualifier_absent_from_the_manifest_is_unknown_qualifier(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: platform::docs/chunks/widget",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNKNOWN_QUALIFIER)
    assert defect.reference == "platform::docs/chunks/widget"
    assert "platform" in defect.message
    assert "lib" in defect.message  # the registered members are listed


def test_registered_member_with_a_missing_tree_is_unknown_qualifier(tmp_path):
    """A member name that resolves to nothing on disk is not usable as a target."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    write_workspace_manifest(tmp_path, {"lib": "packages/lib", "gone": "packages/gone"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: gone::docs/chunks/widget",
    )

    report = validate(tmp_path)

    assert FixClass.UNKNOWN_QUALIFIER in classes(report)
    assert any("gone" in message for message in report.manifest_errors)
    assert not report.ok


def test_member_qualifier_with_a_missing_artifact_is_missing_target(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib", "arch": "architecture"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: arch::docs/chunks/widget",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISSING_TARGET)
    assert defect.reference == "arch::docs/chunks/widget"
    assert defect.line == 1


def test_legacy_prefix_style_ref_is_malformed_qualifier(tmp_path):
    """`architecture/docs/chunks/x` needs normalizing to `::` form."""
    make_workspace(tmp_path, {"lib": "packages/lib", "architecture": "architecture"})
    artifact(tmp_path / "architecture", "chunks", "widget")
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: architecture/docs/chunks/widget",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MALFORMED_QUALIFIER)
    assert defect.reference == "architecture/docs/chunks/widget"
    assert "::" in defect.message


def test_repo_qualified_ref_is_unverified_not_an_error(tmp_path):
    """Cross-repo targets cannot be resolved offline, so they never gate CI."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: acme/platform::docs/chunks/widget",
    )

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.ok
    (unverified,) = report.unverified
    assert unverified.reference == "acme/platform::docs/chunks/widget"
    assert unverified.path == "packages/lib/a.py"
    assert unverified.line == 1


# ---------------------------------------------------------------------------
# external.yaml pointers
# ---------------------------------------------------------------------------


def test_stale_peer_pointer_is_missing_target(tmp_path):
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib"})
    pointer(tmp_path / "app", "baseline", target_tree="lib", artifact_id="gone")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISSING_TARGET)
    assert defect.path == "app/docs/chunks/baseline/external.yaml"
    assert defect.reference == "tree:lib docs/chunks/gone"
    assert report.pointers_checked == 1


def test_resolvable_peer_pointer_is_clean(tmp_path):
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "chunks", "baseline")
    pointer(tmp_path / "app", "baseline", target_tree="lib")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.pointers_checked == 1


def test_peer_pointer_target_without_a_main_document_is_missing_target(tmp_path):
    """A target directory that carries no content cannot be resolved to."""
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib"})
    (tmp_path / "packages" / "lib" / "docs" / "chunks" / "baseline").mkdir(parents=True)
    pointer(tmp_path / "app", "baseline", target_tree="lib")

    report = validate(tmp_path)

    assert classes(report) == [FixClass.MISSING_TARGET]


def test_peer_pointer_to_an_unregistered_tree_is_unknown_qualifier(tmp_path):
    make_workspace(tmp_path, {"app": "app"})
    pointer(tmp_path / "app", "baseline", target_tree="lib")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNKNOWN_QUALIFIER)
    assert defect.path == "app/docs/chunks/baseline/external.yaml"
    assert "lib" in defect.message


def test_stale_pointer_whose_target_moved_names_the_new_tree(tmp_path):
    """A retargetable pointer is a mechanical fix, so the candidate is reported."""
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib", "arch": "architecture"})
    artifact(tmp_path / "architecture", "chunks", "baseline")
    pointer(tmp_path / "app", "baseline", target_tree="lib")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISSING_TARGET)
    assert [candidate.member for candidate in defect.candidates] == ["arch"]


def test_pointer_to_an_unregistered_tree_names_where_the_target_lives(tmp_path):
    make_workspace(tmp_path, {"app": "app", "arch": "architecture"})
    artifact(tmp_path / "architecture", "chunks", "baseline")
    pointer(tmp_path / "app", "baseline", target_tree="platform")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNKNOWN_QUALIFIER)
    assert [candidate.member for candidate in defect.candidates] == ["arch"]


def test_unreadable_pointer_is_missing_target(tmp_path):
    make_workspace(tmp_path, {"app": "app"})
    pointer(tmp_path / "app", "broken", body="artifact_type: chunk\nartifact_id: x\n")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISSING_TARGET)
    assert defect.path == "app/docs/chunks/broken/external.yaml"


def test_cross_repo_pointer_is_unverified(tmp_path):
    make_workspace(tmp_path, {"app": "app"})
    pointer(tmp_path / "app", "borrowed", repo="acme/hub")

    report = validate(tmp_path)

    assert report.defects == ()
    (unverified,) = report.unverified
    assert unverified.path == "app/docs/chunks/borrowed/external.yaml"


# ---------------------------------------------------------------------------
# Frontmatter code_references
# ---------------------------------------------------------------------------


def declared_paths_chunk(
    tree: pathlib.Path,
    name: str,
    *,
    status: str = "ACTIVE",
    code_paths: tuple[str, ...] = (),
    code_references: tuple[str, ...] = (),
) -> None:
    """Create a chunk declaring code_paths and/or code_references entries."""
    directory = tree / "docs" / "chunks" / name
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}"]
    if code_paths:
        lines.append("code_paths:")
        lines.extend(f"  - {path}" for path in code_paths)
    if code_references:
        lines.append("code_references:")
        for ref in code_references:
            lines.append(f"  - ref: {ref}")
            lines.append('    implements: "the thing"')
    lines.extend(["---", "", "# Goal"])
    (directory / "GOAL.md").write_text("".join(f"{line}\n" for line in lines))


def code_ref_chunk(tree: pathlib.Path, name: str, ref: str) -> None:
    """Create a chunk whose frontmatter carries one code reference."""
    declared_paths_chunk(tree, name, code_references=(ref,))


def test_code_reference_to_a_missing_file_is_unresolvable_frontmatter(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    code_ref_chunk(lib, "widget", "src/gone.py#Widget")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.path == "packages/lib/docs/chunks/widget/GOAL.md"
    assert defect.line == 4
    assert defect.reference == "src/gone.py#Widget"


def test_code_reference_to_a_deleted_symbol_is_unresolvable_frontmatter(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "widget.py", "class Gadget:", "    pass")
    code_ref_chunk(lib, "widget", "src/widget.py#Widget")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert "Widget" in defect.message


def test_code_reference_that_resolves_is_clean(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "widget.py", "class Widget:", "    pass")
    code_ref_chunk(lib, "widget", "src/widget.py#Widget")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.artifacts_scanned == 1


def test_symbol_appearing_anywhere_in_the_file_is_accepted(tmp_path):
    """The symbol check is deliberately conservative: a mention is enough."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "widget.py", "Widget = make_class('Widget')")
    code_ref_chunk(lib, "widget", "src/widget.py#Widget")

    report = validate(tmp_path)

    assert report.defects == ()


def test_qualified_code_reference_is_unverified(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    code_ref_chunk(tmp_path / "packages" / "lib", "widget", "acme/hub::src/w.py#Widget")

    report = validate(tmp_path)

    assert report.defects == ()
    (unverified,) = report.unverified
    assert unverified.reference == "acme/hub::src/w.py#Widget"


def test_subsystem_code_references_are_validated(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    directory = tmp_path / "packages" / "lib" / "docs" / "subsystems" / "baseline"
    directory.mkdir(parents=True)
    (directory / "OVERVIEW.md").write_text(
        "---\n"
        "status: DOCUMENTED\n"
        "code_references:\n"
        "  - ref: src/gone.py\n"
        '    implements: "the pattern"\n'
        "---\n\n# Baseline\n"
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.path == "packages/lib/docs/subsystems/baseline/OVERVIEW.md"


# ---------------------------------------------------------------------------
# Defect line anchoring: findings point at the owning field's entry
# # Chunk: docs/chunks/crossref_defect_line_anchor - Anchor on the offending entry, not the first occurrence
# ---------------------------------------------------------------------------


def entry_line(tree: pathlib.Path, chunk: str, needle: str, *, occurrence: int = 1) -> int:
    """1-indexed line of the Nth line containing `needle` in a chunk's GOAL.md."""
    content = (tree / "docs" / "chunks" / chunk / "GOAL.md").read_text()
    seen = 0
    for line_number, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            seen += 1
            if seen == occurrence:
                return line_number
    raise AssertionError(f"occurrence {occurrence} of {needle!r} not found")


def test_code_references_defect_anchors_past_an_identical_code_paths_entry(tmp_path):
    """The field-report regression: a path in both fields must yield two
    defects anchored on their own entries — a fix loop trusting `line` edited
    the code_paths entry, watched the anchor move, and made no progress."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    declared_paths_chunk(
        lib,
        "widget",
        code_paths=("src/gone.py",),
        code_references=("src/gone.py",),
    )

    report = validate(tmp_path)

    defects = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert len(defects) == 2
    by_field = {
        ("code_paths" if "code_paths" in d.message else "code_references"): d
        for d in defects
    }
    assert by_field["code_paths"].line == entry_line(lib, "widget", "src/gone.py", occurrence=1)
    assert by_field["code_references"].line == entry_line(
        lib, "widget", "src/gone.py", occurrence=2
    )
    assert by_field["code_paths"].line != by_field["code_references"].line


def test_symbol_absence_defect_anchors_on_the_code_references_entry(tmp_path):
    """A gone symbol anchors on the `- ref:` line even when the same file path
    appears earlier in code_paths."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "widget.py", "class Gadget:", "    pass")
    declared_paths_chunk(
        lib,
        "widget",
        code_paths=("src/widget.py",),
        code_references=("src/widget.py#Widget",),
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.line == entry_line(lib, "widget", "ref: src/widget.py#Widget")


def test_unverified_qualified_refs_anchor_on_their_own_fields(tmp_path):
    """The unverified disposition gets the same per-field anchoring."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    declared_paths_chunk(
        lib,
        "widget",
        code_paths=("acme/hub::src/w.py",),
        code_references=("acme/hub::src/w.py",),
    )

    report = validate(tmp_path)

    assert report.defects == ()
    lines = sorted(entry.line for entry in report.unverified)
    assert lines == [
        entry_line(lib, "widget", "acme/hub::src/w.py", occurrence=1),
        entry_line(lib, "widget", "acme/hub::src/w.py", occurrence=2),
    ]


def test_zero_indent_list_style_anchors_correctly(tmp_path):
    """`ve` itself emits zero-indent list items; the block scanner must not
    treat them as the end of the field."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    directory = lib / "docs" / "chunks" / "widget"
    directory.mkdir(parents=True)
    (directory / "GOAL.md").write_text(
        "---\n"
        "status: ACTIVE\n"
        "code_paths:\n"
        "- src/gone.py\n"
        "code_references:\n"
        "- ref: src/gone.py\n"
        '  implements: "the thing"\n'
        "---\n\n# Goal\n"
        "Prose mentioning src/gone.py must not attract the anchor.\n"
    )

    report = validate(tmp_path)

    defects = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    lines = sorted(d.line for d in defects)
    assert lines == [4, 6]


# ---------------------------------------------------------------------------
# Single-tree parity: directories, code_paths, chunk-status gating
# # Chunk: docs/chunks/crossref_workspace_parity - Workspace/single-tree semantics agree
# ---------------------------------------------------------------------------


def test_code_reference_to_an_existing_directory_is_clean(tmp_path):
    """'This chunk governs that package directory' is a legitimate reference."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    (lib / "src" / "env-config").mkdir(parents=True)
    code_ref_chunk(lib, "widget", "src/env-config")

    report = validate(tmp_path)

    assert report.defects == ()


def test_code_reference_to_a_missing_directory_still_defects(tmp_path):
    """The exists() swap must not weaken detection of genuinely absent paths."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    code_ref_chunk(tmp_path / "packages" / "lib", "widget", "src/gone-dir")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.reference == "src/gone-dir"


def test_symbol_anchor_on_a_directory_target_is_skipped(tmp_path):
    """A symbol cannot be looked up in a directory; the anchor is not a defect."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    (lib / "src" / "pkg").mkdir(parents=True)
    code_ref_chunk(lib, "widget", "src/pkg#Widget")

    report = validate(tmp_path)

    assert report.defects == ()


def test_stale_code_paths_entry_is_unresolvable_frontmatter(tmp_path):
    """code_paths must not rot invisibly in workspace mode."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    declared_paths_chunk(
        tmp_path / "packages" / "lib", "widget", code_paths=("src/gone.py",)
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.path == "packages/lib/docs/chunks/widget/GOAL.md"
    assert defect.reference == "src/gone.py"
    assert "code_paths" in defect.message


def test_code_paths_entry_naming_an_existing_directory_is_clean(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    (lib / "src" / "env-config").mkdir(parents=True)
    declared_paths_chunk(lib, "widget", code_paths=("src/env-config",))

    report = validate(tmp_path)

    assert report.defects == ()


def test_chunk_with_only_code_paths_is_still_scanned(tmp_path):
    """An empty code_references list must not short-circuit code_paths checking."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "widget.py", "class Widget:", "    pass")
    declared_paths_chunk(lib, "widget", code_paths=("src/widget.py",))

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.artifacts_scanned == 1


def test_qualified_code_paths_entry_is_unverified(tmp_path):
    """code_paths entries get the same qualified-reference routing as code_references."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    declared_paths_chunk(
        tmp_path / "packages" / "lib", "widget", code_paths=("acme/hub::src/w.py",)
    )

    report = validate(tmp_path)

    assert report.defects == ()
    (unverified,) = report.unverified
    assert unverified.reference == "acme/hub::src/w.py"


# Chunk: docs/chunks/crossref_glob_refs - Glob file parts error only on empty expansion
def test_matching_glob_code_paths_entry_is_clean(tmp_path):
    """A code_paths glob matching existing files is a verified reference."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    for name in ("alpha", "beta"):
        source(lib / "tasks" / name / "Dockerfile", "FROM scratch")
    declared_paths_chunk(lib, "widget", code_paths=("tasks/*/Dockerfile",))

    report = validate(tmp_path)

    assert report.defects == ()


def test_empty_glob_code_paths_entry_is_unresolvable_frontmatter(tmp_path):
    """A glob matching nothing in the member tree is a defect naming the pattern."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    declared_paths_chunk(
        tmp_path / "packages" / "lib", "widget", code_paths=("tasks/*/Dockerfile",)
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.reference == "tasks/*/Dockerfile"
    assert "glob pattern" in defect.message
    assert "matches nothing" in defect.message


def test_matching_glob_code_reference_is_clean(tmp_path):
    """A code_references file part may be a glob pattern with matches."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "tasks" / "alpha" / "Dockerfile", "FROM scratch")
    code_ref_chunk(lib, "widget", "tasks/*/Dockerfile")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.unverified == ()


def test_empty_glob_code_reference_is_unresolvable_frontmatter(tmp_path):
    """An empty glob expansion in a code_references file part is a defect."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    code_ref_chunk(tmp_path / "packages" / "lib", "widget", "tasks/*/Dockerfile")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.reference == "tasks/*/Dockerfile"
    assert "matches nothing" in defect.message


def test_symbol_anchor_on_glob_pattern_is_unverified(tmp_path):
    """Symbols are not checked across glob expansions: unverified, not passed.

    The anchor must be neither silently passed (hiding a stale symbol) nor
    spuriously failed (the symbol may live in only one of the matches).
    """
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "pkgs" / "alpha" / "handler.py", "class Handler:", "    pass")
    source(lib / "pkgs" / "beta" / "handler.py", "class Other:", "    pass")
    code_ref_chunk(lib, "widget", "pkgs/*/handler.py#Handler")

    report = validate(tmp_path)

    assert report.defects == ()
    (unverified,) = report.unverified
    assert unverified.reference == "pkgs/*/handler.py#Handler"
    assert "glob" in unverified.reason


@pytest.mark.parametrize("status", ["FUTURE", "IMPLEMENTING", "HISTORICAL", "SUPERSEDED"])
def test_non_owning_chunk_statuses_are_exempt_from_path_checks(tmp_path, status):
    """Parity with the single-tree check: FUTURE/IMPLEMENTING chunks list files
    they expect to create, and HISTORICAL/SUPERSEDED chunks keep archaeological
    references. Only ACTIVE/COMPOSITE chunks are held to on-disk existence."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    declared_paths_chunk(
        tmp_path / "packages" / "lib",
        "widget",
        status=status,
        code_paths=("src/gone.py",),
        code_references=("src/also_gone.py#Widget",),
    )

    report = validate(tmp_path)

    assert report.defects == ()


def test_composite_chunk_paths_are_checked(tmp_path):
    """COMPOSITE shares intent ownership, so its declared paths are held to disk."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    declared_paths_chunk(
        tmp_path / "packages" / "lib",
        "widget",
        status="COMPOSITE",
        code_paths=("src/gone.py",),
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.reference == "src/gone.py"


def test_subsystem_code_references_are_checked_regardless_of_status(tmp_path):
    """Subsystem refs document living patterns; no status exemption applies."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    directory = tmp_path / "packages" / "lib" / "docs" / "subsystems" / "baseline"
    directory.mkdir(parents=True)
    (directory / "OVERVIEW.md").write_text(
        "---\n"
        "status: REFACTORING\n"
        "code_references:\n"
        "  - ref: src/gone.py\n"
        '    implements: "the pattern"\n'
        "---\n\n# Baseline\n"
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert defect.reference == "src/gone.py"


# ---------------------------------------------------------------------------
# Manifest health, scanning scope, determinism
# ---------------------------------------------------------------------------


def test_missing_member_path_is_a_manifest_error_and_gates(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    write_workspace_manifest(tmp_path, {"lib": "packages/lib", "gone": "packages/gone"})

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.manifest_errors
    assert not report.ok


def test_nested_members_report_a_defect_exactly_once(tmp_path):
    """Files are scanned once even when one member tree contains another."""
    make_workspace(tmp_path, {"platform": "platform", "lib": "platform/libs/lib"})
    source(
        tmp_path / "platform" / "libs" / "lib" / "a.py",
        "# Chunk: docs/chunks/missing",
    )

    report = validate(tmp_path)

    assert classes(report) == [FixClass.UNRESOLVABLE_BARE]
    assert report.files_scanned == 1


def test_indented_backreferences_are_scanned(tmp_path):
    """A reference inside a class is checked like one at column 0.

    # Chunk: docs/chunks/backref_indented_comments - Interior references are covered
    """
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "class Widget:",
        "    # Chunk: docs/chunks/missing",
        "    def method(self):",
        "        # Chunk: docs/chunks/alsomissing",
        "        return 1",
    )

    report = validate(tmp_path)

    assert report.references_checked == 2
    assert {d.reference for d in report.defects} == {
        "docs/chunks/missing",
        "docs/chunks/alsomissing",
    }
    # The line numbers must point at the indented lines, not the block openers.
    assert sorted(d.line for d in report.defects) == [2, 4]


def test_reference_trailing_after_code_is_not_scanned(tmp_path):
    """The own-line rule survives: indentation is free, trailing is not.

    # Chunk: docs/chunks/backref_indented_comments - Own-line remains the boundary
    """
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "x = 1  # Chunk: docs/chunks/missing",
    )

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.references_checked == 0


def test_report_is_deterministic(tmp_path):
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "chunks", "widget")
    source(tmp_path / "app" / "b.py", "# Chunk: docs/chunks/widget")
    source(tmp_path / "app" / "a.py", "# Chunk: docs/chunks/nowhere")
    pointer(tmp_path / "app", "stale", target_tree="lib", artifact_id="gone")

    first = validate(tmp_path).to_dict()
    second = validate(tmp_path).to_dict()

    assert first == second


def test_defects_are_grouped_by_fix_class_in_declaration_order(tmp_path):
    make_workspace(tmp_path, {"app": "app", "lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "chunks", "widget")
    source(
        tmp_path / "app" / "a.py",
        "# Chunk: bad/docs/chunks/widget",
        "# Chunk: docs/chunks/nowhere",
        "# Chunk: docs/chunks/widget",
    )

    report = validate(tmp_path)

    assert classes(report) == [
        FixClass.UNRESOLVABLE_BARE,
        FixClass.MISROUTED_BARE,
        FixClass.MALFORMED_QUALIFIER,
    ]


def test_validate_workspace_at_finds_the_manifest_from_a_subdirectory(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(tmp_path / "packages" / "lib" / "a.py", "# Chunk: docs/chunks/nowhere")

    report = validate_workspace_at(tmp_path / "packages" / "lib")

    assert report.workspace_root == tmp_path.resolve()
    assert classes(report) == [FixClass.UNRESOLVABLE_BARE]


def test_root_tree_registered_as_a_member_governs_the_files_below_it(tmp_path):
    """The common monorepo shape: the repository root is itself a member tree."""
    make_workspace(tmp_path, {"root": ".", "lib": "packages/lib"})
    artifact(tmp_path, "chunks", "platform_wide")
    source(tmp_path / "scripts" / "deploy.py", "# Chunk: docs/chunks/platform_wide")

    report = validate(tmp_path)

    assert report.defects == ()
    assert report.unregistered_trees == ()


def test_root_tree_has_no_addressing_privilege_over_a_nested_tree(tmp_path):
    """A file inside a nested tree resolves there, not against the root tree."""
    make_workspace(tmp_path, {"root": ".", "lib": "packages/lib"})
    artifact(tmp_path, "chunks", "platform_wide")
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: docs/chunks/platform_wide",
    )

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.MISROUTED_BARE)
    assert [candidate.member for candidate in defect.candidates] == ["root"]
    assert "packages/lib" in defect.message


def test_bare_ref_in_a_pointer_only_tree_resolves_against_the_root_tree(tmp_path):
    """A pointer-only tree does not shadow the governing tree above it."""
    write_workspace_manifest(tmp_path, {"root": ".", "ptr": "packages/ptr"})
    make_ve_tree(tmp_path)
    artifact(tmp_path, "chunks", "platform_wide")
    ptr = tmp_path / "packages" / "ptr"
    pointer(ptr, "borrowed", repo="acme/hub")
    source(ptr / "consumer.py", "# Chunk: docs/chunks/platform_wide")

    report = validate(tmp_path)

    assert report.defects == ()


def test_workspace_with_no_members_reports_nothing(tmp_path):
    write_workspace_manifest(tmp_path, {})

    report = validate(tmp_path)

    assert report.ok
    assert report.defects == ()


def test_index_tree_counts_pointer_stubs_as_present_artifacts(tmp_path):
    """An external.yaml stub is a legitimate backreference target."""
    tree = make_ve_tree(tmp_path / "lib")
    artifact(tree, "chunks", "local")
    pointer(tree, "borrowed", repo="acme/hub")

    index = index_tree(tree)

    assert index.has(ArtifactType.CHUNK, "local")
    assert index.has(ArtifactType.CHUNK, "borrowed")
    assert not index.has(ArtifactType.CHUNK, "absent")
    assert not index.has(ArtifactType.SUBSYSTEM, "local")


# ---------------------------------------------------------------------------
# The case-study shape (GOAL success criterion)
# ---------------------------------------------------------------------------


@pytest.fixture
def case_study(tmp_path):
    """Two governing trees, a docs-tree-less package, and one defect of each class.

    Mirrors the Cloud Capital monorepo diagnosis: a misrouted subsystem ref, a
    born-dangling chunk ref, a legacy prefix-style ref, and a stale pointer.
    """
    make_workspace(
        tmp_path, {"pybusiness": "packages/libs/pybusiness", "architecture": "architecture"}
    )
    pybusiness = tmp_path / "packages" / "libs" / "pybusiness"
    architecture = tmp_path / "architecture"

    artifact(architecture, "subsystems", "commitment_baseline")
    artifact(architecture, "chunks", "rsv2_pybusiness_model")
    artifact(pybusiness, "subsystems", "savings")

    # One file carrying refs into two trees at once.
    source(
        pybusiness / "savings" / "realized.py",
        "# Subsystem: docs/subsystems/savings",
        "# Subsystem: docs/subsystems/commitment_baseline",
        "# Chunk: docs/chunks/run_rate_cloud_capital_split",
        "# Chunk: architecture/docs/chunks/rsv2_pybusiness_model",
    )
    # A direct consumer of cross-tree vocabulary with no docs tree of its own.
    source(
        tmp_path / "backend-api-lib" / "client.py",
        "# Subsystem: architecture::docs/subsystems/commitment_baseline",
    )
    # A pointer whose target was renamed away.
    pointer(pybusiness, "baseline", target_tree="architecture", artifact_id="gone")
    return tmp_path


def test_case_study_reports_each_defect_exactly_once_with_the_right_class(case_study):
    report = validate(case_study)

    by_class = report.by_fix_class()
    assert sorted(by_class) == sorted(
        [
            FixClass.UNRESOLVABLE_BARE,
            FixClass.MISROUTED_BARE,
            FixClass.MISSING_TARGET,
            FixClass.MALFORMED_QUALIFIER,
        ]
    )
    assert len(report.defects) == 4

    (misrouted,) = by_class[FixClass.MISROUTED_BARE]
    assert misrouted.reference == "docs/subsystems/commitment_baseline"
    assert misrouted.line == 2
    assert [candidate.member for candidate in misrouted.candidates] == ["architecture"]

    (dangling,) = by_class[FixClass.UNRESOLVABLE_BARE]
    assert dangling.reference == "docs/chunks/run_rate_cloud_capital_split"
    assert dangling.line == 3

    (legacy,) = by_class[FixClass.MALFORMED_QUALIFIER]
    assert legacy.line == 4

    (stale,) = by_class[FixClass.MISSING_TARGET]
    assert stale.path.endswith("baseline/external.yaml")

    assert not report.ok


def test_case_study_accepts_the_qualified_ref_from_the_tree_less_package(case_study):
    report = validate(case_study)

    assert not any(
        defect.path.startswith("backend-api-lib/") for defect in report.defects
    )


def test_case_study_becomes_clean_once_every_defect_is_fixed(case_study):
    """The report drives to zero, which is what makes the fix loop terminate."""
    realized = case_study / "packages" / "libs" / "pybusiness" / "savings" / "realized.py"
    realized.write_text(
        "# Subsystem: docs/subsystems/savings\n"
        "# Subsystem: architecture::docs/subsystems/commitment_baseline\n"
        "# Chunk: architecture::docs/chunks/rsv2_pybusiness_model\n"
    )
    artifact(case_study / "architecture", "chunks", "gone")

    report = validate(case_study)

    assert report.defects == ()
    assert report.ok


# ---------------------------------------------------------------------------
# `ve workspace validate`
# ---------------------------------------------------------------------------


def test_cli_exits_zero_on_a_clean_workspace(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    artifact(tmp_path / "packages" / "lib", "chunks", "widget")
    source(tmp_path / "packages" / "lib" / "a.py", "# Chunk: docs/chunks/widget")

    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "No reference defects" in result.output


def test_cli_exits_nonzero_and_groups_defects_by_fix_class(case_study):
    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(case_study)]
    )

    assert result.exit_code == 1
    for fix_class in (
        "unresolvable-bare",
        "misrouted-bare",
        "missing-target",
        "malformed-qualifier",
    ):
        assert fix_class in result.output
    assert "realized.py:2" in result.output
    assert "architecture::docs/subsystems/commitment_baseline" in result.output


def test_cli_json_carries_fix_class_location_reference_and_candidates(case_study):
    result = CliRunner().invoke(
        cli,
        ["workspace", "validate", "--workspace-dir", str(case_study), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    misrouted = [
        defect
        for defect in payload["defects"]
        if defect["fix_class"] == "misrouted-bare"
    ]
    assert len(misrouted) == 1
    assert misrouted[0]["path"] == "packages/libs/pybusiness/savings/realized.py"
    assert misrouted[0]["line"] == 2
    assert misrouted[0]["reference"] == "docs/subsystems/commitment_baseline"
    assert misrouted[0]["candidates"] == [
        {"member": "architecture", "path": "architecture", "qualifier": "architecture::"}
    ]


def test_cli_json_is_valid_on_a_clean_workspace(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})

    result = CliRunner().invoke(
        cli,
        ["workspace", "validate", "--workspace-dir", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["defects"] == []


def test_cli_reports_unverified_cross_repo_targets_without_failing(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    source(
        tmp_path / "packages" / "lib" / "a.py",
        "# Chunk: acme/platform::docs/chunks/widget",
    )

    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "not verified" in result.output


def test_cli_states_the_own_line_scanning_limitation(tmp_path):
    """The disclosure tracks the real limit, and never claims the retired one.

    # Chunk: docs/chunks/backref_indented_comments - Disclosure matches behavior
    """
    make_workspace(tmp_path, {"lib": "packages/lib"})

    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(tmp_path)]
    )
    help_result = CliRunner().invoke(cli, ["workspace", "validate", "--help"])

    for output in (result.output, help_result.output):
        assert "own line" in output or "its own line" in output
        # The retired limitation must not be advertised: a caveat that outlives
        # the behavior it describes is worse than none.
        assert "column 0" not in output
        assert "column-0" not in output


def test_cli_errors_without_a_workspace_manifest(tmp_path):
    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 1
    assert "ve workspace init" in result.output


def test_cli_reports_manifest_errors(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    write_workspace_manifest(tmp_path, {"lib": "packages/lib", "gone": "packages/gone"})

    result = CliRunner().invoke(
        cli, ["workspace", "validate", "--workspace-dir", str(tmp_path)]
    )

    assert result.exit_code == 1
    assert "gone" in result.output


# ---------------------------------------------------------------------------
# Re-export-only symbol anchors
# Chunk: docs/chunks/crossref_reexport_absence - Validator treats re-exports as absent
# ---------------------------------------------------------------------------


def test_reexport_only_symbol_is_unresolvable_frontmatter(tmp_path):
    """`from ._impl import Widget  # noqa: F401` no longer makes Widget present."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(
        lib / "src" / "api.py",
        "from ._impl import Widget  # noqa: F401",
    )
    code_ref_chunk(lib, "widget", "src/api.py#Widget")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert "Widget" in defect.message
    assert "another file" in defect.message


def test_dunder_all_only_symbol_is_unresolvable_frontmatter(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(lib / "src" / "api.py", '__all__ = ["Widget"]')
    code_ref_chunk(lib, "widget", "src/api.py#Widget")

    report = validate(tmp_path)

    (defect,) = of_class(report, FixClass.UNRESOLVABLE_FRONTMATTER)
    assert "Widget" in defect.message


def test_reexport_plus_local_definition_is_clean(tmp_path):
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(
        lib / "src" / "api.py",
        "from ._compat import Widget",
        "",
        "",
        "class Widget:",
        "    pass",
    )
    code_ref_chunk(lib, "widget", "src/api.py#Widget")

    report = validate(tmp_path)

    assert report.defects == ()


def test_unparseable_python_keeps_whole_word_presence(tmp_path):
    """Conservatism survives: an unparseable file never gains a new defect."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    source(
        lib / "src" / "api.py",
        "from ._impl import Widget",
        "def broken(:",
    )
    code_ref_chunk(lib, "widget", "src/api.py#Widget")

    report = validate(tmp_path)

    assert report.defects == ()
