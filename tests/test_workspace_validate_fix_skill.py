"""Tests for the workspace validate-fix loop skill.

# Chunk: docs/chunks/federation_validate_fix_skill - Workspace compliance loop skill

Two layers, because the skill is a document that drives an agent through
machine-checkable surfaces:

1. **Contract tests** assert the document dispatches on every `FixClass` the
   validator can emit and gives every report section a disposition. `FixClass`
   names itself part of a contract with this skill, so a seventh class must fail
   here until the skill handles it.
2. **One skill pass** over a case-study-shaped workspace. `skill_pass` below
   encodes the document's dispatch table and applies it through the real fix
   surfaces; the assertions are the GOAL's criterion — after one pass only the
   deliberately ambiguous defect remains, presented with its candidates.

`commands/workspace-validate-fix.md` is the authority for the rules;
`skill_pass` is a mechanical transcription of them, present to prove they
converge and that they never delete a reference or author a target.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
from click.testing import CliRunner

from conftest import make_ve_tree, make_workspace, write_workspace_manifest
from test_plugin_manifest import REPO_ROOT
from ve import cli
from workspace_validation import FixClass, ValidationReport

SKILL = REPO_ROOT / "commands" / "workspace-validate-fix.md"

# Report sections that need a stated disposition. Defects get fixed or
# escalated; unverified references and unregistered trees get reported without
# being "fixed"; a manifest error gates, so a loop that ignored it could never
# terminate clean.
SECTIONS_REQUIRING_A_DISPOSITION = frozenset(
    {"defects", "unverified", "manifest_errors", "unregistered_trees"}
)


@pytest.fixture(scope="module")
def body() -> str:
    return SKILL.read_text()


# ---------------------------------------------------------------------------
# The document's contract with the validator
# ---------------------------------------------------------------------------


def test_document_dispatches_on_every_fix_class(body):
    """Every class the validator can emit has an entry in the skill."""
    for fix_class in FixClass:
        assert fix_class.value in body, (
            f"{fix_class.value} has no disposition in {SKILL.name}; the fix loop "
            f"dispatches on FixClass, so an unhandled class silently stalls it"
        )


def test_document_gives_every_report_section_a_disposition(body):
    """Defects are not the only thing a run reports."""
    report_keys = set(ValidationReport(workspace_root=pathlib.Path(".")).to_dict())
    assert SECTIONS_REQUIRING_A_DISPOSITION <= report_keys, (
        "the JSON contract changed; update the skill and this test together"
    )
    for section in sorted(SECTIONS_REQUIRING_A_DISPOSITION):
        assert section in body, f"{SKILL.name} says nothing about `{section}`"


def test_document_names_the_json_contract_and_the_fix_surfaces(body):
    """The loop reads JSON and fixes through commands, not by hand-editing YAML."""
    for surface in (
        "ve workspace validate --format json",
        "ve external point",
        "ve workspace add",
        "candidates",
    ):
        assert surface in body, f"{SKILL.name} does not mention {surface}"


def test_document_states_the_three_invariants(body):
    """The GOAL's hard limits are stated as invariants, not implied."""
    for invariant in (
        "Never delete a reference",
        "Never fabricate a target",
        "Never choose between candidates",
    ):
        assert invariant in body, f"{SKILL.name} does not state: {invariant}"


def test_document_prescribes_fix_class_grouped_batches(body):
    """An operator audits all qualifications apart from all new pointers."""
    assert "one commit per fix class" in body


def test_document_terminates_the_loop(body):
    """A loop with no cap and no progress check is not a loop, it is a hang."""
    assert "10 iterations" in body
    assert "no progress" in body


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def artifact(tree: pathlib.Path, kind: str, name: str) -> pathlib.Path:
    """Create a local artifact directory with a main document."""
    directory = tree / "docs" / kind / name
    directory.mkdir(parents=True, exist_ok=True)
    main = "GOAL.md" if kind == "chunks" else "OVERVIEW.md"
    status = "ACTIVE" if kind == "chunks" else "DOCUMENTED"
    (directory / main).write_text(f"---\nstatus: {status}\n---\n\n# {name}\n")
    return directory


def source(path: pathlib.Path, *lines: str) -> pathlib.Path:
    """Write a source file with the given lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines))
    return path


def peer_pointer(
    tree: pathlib.Path, name: str, *, target_tree: str, why: str
) -> pathlib.Path:
    """Create a peer external.yaml pointing at another workspace member."""
    directory = tree / "docs" / "subsystems" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "external.yaml").write_text(
        f"artifact_type: subsystem\nartifact_id: {name}\ntree: {target_tree}\nwhy: {why}\n"
    )
    return directory


def run_ve(*args: str) -> str:
    """Invoke the ve CLI, failing the test on a nonzero exit."""
    result = CliRunner().invoke(cli, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def validate_json(root: pathlib.Path) -> dict:
    """Run `ve workspace validate --format json`, as the skill's step 1 does."""
    result = CliRunner().invoke(
        cli,
        ["workspace", "validate", "--workspace-dir", str(root), "--format", "json"],
    )
    return json.loads(result.output)


def backreference_lines(root: pathlib.Path) -> list[str]:
    """Every backreference comment in the workspace's source files, sorted."""
    return sorted(
        line
        for path in root.rglob("*.py")
        for line in path.read_text().splitlines()
        if line.startswith(("# Chunk:", "# Subsystem:"))
    )


def artifact_directories(root: pathlib.Path) -> dict[str, list[str]]:
    """Every artifact directory in the workspace, by containing docs/ dir."""
    found: dict[str, list[str]] = {}
    for docs_dir in sorted(root.rglob("docs")):
        for kind_dir in sorted(docs_dir.iterdir()):
            if not kind_dir.is_dir() or kind_dir.name == "trunk":
                continue
            key = str(kind_dir.relative_to(root))
            found[key] = sorted(d.name for d in kind_dir.iterdir() if d.is_dir())
    return found


# ---------------------------------------------------------------------------
# The skill's dispatch table, transcribed
# ---------------------------------------------------------------------------


def governing_tree(root: pathlib.Path, rel_path: str) -> pathlib.Path | None:
    """Nearest ancestor of the file holding docs/trunk/ — the skill's probe.

    Which tree governs the file decides whether a peer pointer can fix a bare
    reference at all: a pointer only makes bare references resolve when it lives
    in the governing tree.
    """
    directory = (root / rel_path).parent
    while True:
        if (directory / "docs" / "trunk").is_dir():
            return directory
        if directory == root:
            return None
        directory = directory.parent


def rewrite_reference(
    root: pathlib.Path, rel_path: str, line: int, reference: str, replacement: str
) -> None:
    """Replace one reference in place, touching nothing else on the line.

    The whole of the skill's edit vocabulary: line count and description text are
    preserved, so later defects' line numbers stay valid within a pass.
    """
    path = root / rel_path
    lines = path.read_text().splitlines()
    index = line - 1
    assert reference in lines[index], f"{rel_path}:{line} does not contain {reference}"
    lines[index] = lines[index].replace(reference, replacement, 1)
    path.write_text("".join(f"{text}\n" for text in lines))


def skill_pass(root: pathlib.Path, report: dict) -> list[dict]:
    """Apply the document's mechanical fixes once; return the escalations."""
    escalations: list[dict] = []
    registered = set(report["members"])

    # -- misrouted-bare: qualify one-offs, point when readers multiply --------
    groups: dict[tuple[str, str], list[dict]] = {}
    for defect in report["defects"]:
        if defect["fix_class"] != "misrouted-bare":
            continue
        tree = governing_tree(root, defect["path"])
        groups.setdefault((str(tree), defect["reference"]), []).append(defect)

    for (tree, reference), defects in groups.items():
        candidates = defects[0]["candidates"]
        if len(candidates) != 1:
            escalations.extend(defects)
            continue
        member = candidates[0]["member"]
        if member is None:
            # The target tree is real but unregistered: register it under its
            # directory name, then qualify against the name just registered.
            member = pathlib.PurePosixPath(candidates[0]["path"]).name
            run_ve(
                "workspace", "add", member, candidates[0]["path"],
                "--workspace-dir", str(root),
            )
            registered.add(member)
        if tree != "None" and len(defects) >= 2:
            run_ve(
                "external", "point", member, reference,
                "--why", "read by this tree",
                "--project-dir", tree,
            )
            continue
        for defect in defects:
            rewrite_reference(
                root, defect["path"], defect["line"], reference, f"{member}::{reference}"
            )

    # -- malformed-qualifier: normalize the legacy prefix to `::` -------------
    for defect in report["defects"]:
        if defect["fix_class"] != "malformed-qualifier":
            continue
        prefix, _, tail = defect["reference"].partition("/docs/")
        artifact_path = f"docs/{tail}"
        named = [c["member"] for c in defect["candidates"] if c["member"]]
        if prefix in registered:
            member = prefix
        elif len(named) == 1:
            member = named[0]
        else:
            escalations.append(defect)
            continue
        rewrite_reference(
            root,
            defect["path"],
            defect["line"],
            defect["reference"],
            f"{member}::{artifact_path}",
        )

    # -- missing-target: retarget a pointer whose artifact moved -------------
    for defect in report["defects"]:
        if defect["fix_class"] != "missing-target":
            continue
        named = [c["member"] for c in defect["candidates"] if c["member"]]
        if len(named) != 1 or not defect["path"].endswith("external.yaml"):
            escalations.append(defect)
            continue
        pointer = root / defect["path"]
        stale = defect["reference"].split()[0].removeprefix("tree:")
        pointer.write_text(
            pointer.read_text().replace(f"tree: {stale}", f"tree: {named[0]}")
        )

    # -- unknown-qualifier: register the tree, or correct the qualifier -------
    for defect in report["defects"]:
        if defect["fix_class"] != "unknown-qualifier":
            continue
        named = [c["member"] for c in defect["candidates"] if c["member"]]
        unregistered = [c for c in defect["candidates"] if not c["member"]]
        qualifier = defect["reference"].split("::")[0]
        if len(named) == 1:
            rewrite_reference(
                root,
                defect["path"],
                defect["line"],
                defect["reference"],
                defect["reference"].replace(f"{qualifier}::", f"{named[0]}::", 1),
            )
        elif len(unregistered) == 1:
            # The qualifier names a real tree; register it under the name the
            # reference already uses rather than renaming every reference.
            run_ve(
                "workspace", "add", qualifier, unregistered[0]["path"],
                "--workspace-dir", str(root),
            )
            registered.add(qualifier)
        else:
            escalations.append(defect)

    # -- unresolvable-frontmatter: follow a file that moved -------------------
    for defect in report["defects"]:
        if defect["fix_class"] != "unresolvable-frontmatter":
            continue
        file_part = defect["reference"].split("#")[0]
        tree_root = root / defect["path"].split("/docs/")[0]
        moved = [
            path
            for path in tree_root.rglob(pathlib.PurePosixPath(file_part).name)
            if path.is_file()
        ]
        if len(moved) != 1:
            escalations.append(defect)
            continue
        new_path = moved[0].relative_to(tree_root).as_posix()
        rewrite_reference(
            root, defect["path"], defect["line"], file_part, new_path
        )

    # -- manifest_errors: a member whose tree moved --------------------------
    for message in report["manifest_errors"]:
        name, stale = re.findall(r"'([^']*)'", message)[:2]
        found = [
            path
            for path in root.rglob(pathlib.PurePosixPath(stale).name)
            if (path / "docs").is_dir()
        ]
        if len(found) != 1:
            escalations.append({"fix_class": "manifest", "message": message})
            continue
        manifest = root / ".ve-workspace.yaml"
        manifest.write_text(
            manifest.read_text().replace(
                f"{name}: {stale}", f"{name}: {found[0].relative_to(root).as_posix()}"
            )
        )

    # -- the class the document never fixes mechanically ---------------------
    escalations.extend(
        defect
        for defect in report["defects"]
        if defect["fix_class"] == "unresolvable-bare"
    )
    return escalations


# ---------------------------------------------------------------------------
# The case-study-shaped workspace
# ---------------------------------------------------------------------------


@pytest.fixture
def compliance_case(tmp_path):
    """A workspace with one defect per mechanical class and one real ambiguity.

    Shaped after the Cloud Capital diagnosis: a library tree whose files
    reference an architecture tree's vocabulary, a package with no docs tree of
    its own that consumes the same vocabulary, a legacy prefix-style ref, a tree
    nobody registered, and a pointer whose target moved.
    """
    make_workspace(
        tmp_path,
        {
            "pybusiness": "packages/libs/pybusiness",
            "architecture": "architecture",
            "viz": "apps/viz",
        },
    )
    make_ve_tree(tmp_path / "packages" / "libs" / "platform")

    pybusiness = tmp_path / "packages" / "libs" / "pybusiness"
    architecture = tmp_path / "architecture"

    artifact(architecture, "subsystems", "commitment_baseline")
    artifact(architecture, "subsystems", "pricing_rules")
    artifact(architecture, "chunks", "rsv2_pybusiness_model")
    artifact(architecture, "subsystems", "rounding")
    artifact(pybusiness, "subsystems", "savings")
    artifact(pybusiness, "subsystems", "rounding")
    artifact(tmp_path / "packages" / "libs" / "platform", "subsystems", "tenancy")
    artifact(tmp_path / "apps" / "viz", "subsystems", "rate_card")

    # Two files in one tree reading the same foreign subsystem: the case for a
    # peer pointer rather than two qualifications.
    source(
        pybusiness / "savings" / "realized.py",
        "# Subsystem: docs/subsystems/savings",
        "# Subsystem: docs/subsystems/commitment_baseline",
        "# Subsystem: docs/subsystems/pricing_rules",
        "# Chunk: architecture/docs/chunks/rsv2_pybusiness_model",
        "# Subsystem: docs/subsystems/tenancy",
    )
    source(
        pybusiness / "savings" / "forecast.py",
        "# Subsystem: docs/subsystems/commitment_baseline",
    )
    # A consumer with no docs tree at all, naming an artifact two trees own.
    source(
        tmp_path / "backend-api-lib" / "client.py",
        "# Subsystem: docs/subsystems/rounding",
    )
    peer_pointer(
        pybusiness, "rate_card", target_tree="architecture", why="prices come from here"
    )
    return tmp_path


def test_case_study_reports_one_defect_per_mechanical_class_plus_one_ambiguity(
    compliance_case,
):
    """The fixture is the shape the skill claims to bring into compliance."""
    report = validate_json(compliance_case)

    by_class: dict[str, list[dict]] = {}
    for defect in report["defects"]:
        by_class.setdefault(defect["fix_class"], []).append(defect)

    assert sorted(by_class) == ["malformed-qualifier", "misrouted-bare", "missing-target"]
    assert report["unregistered_trees"] == ["packages/libs/platform"]

    references = {d["reference"] for d in by_class["misrouted-bare"]}
    assert references == {
        "docs/subsystems/commitment_baseline",  # two files -> peer pointer
        "docs/subsystems/pricing_rules",  # one file -> qualify
        "docs/subsystems/tenancy",  # candidate tree unregistered -> register
        "docs/subsystems/rounding",  # two candidates -> escalate
    }
    ambiguous = [
        d for d in by_class["misrouted-bare"] if d["reference"].endswith("rounding")
    ]
    assert [c["member"] for c in ambiguous[0]["candidates"]] == [
        "pybusiness",
        "architecture",
    ]


def test_one_skill_pass_leaves_only_the_ambiguous_defect(compliance_case):
    """The GOAL's criterion: mechanical fixes converge in a single pass."""
    before = validate_json(compliance_case)

    escalations = skill_pass(compliance_case, before)

    after = validate_json(compliance_case)
    assert [d["location"] for d in after["defects"]] == ["backend-api-lib/client.py:1"]
    assert after["defects"][0]["reference"] == "docs/subsystems/rounding"
    assert [d["location"] for d in escalations] == [
        d["location"] for d in after["defects"]
    ], "the surviving defect must be the one the pass escalated, not a new one"
    assert after["unregistered_trees"] == []
    assert len(after["defects"]) == 1
    assert not after["ok"]


def test_the_surviving_defect_is_escalated_with_both_candidates(compliance_case):
    """An ambiguity is handed to the operator with the options, never guessed."""
    (escalation,) = skill_pass(compliance_case, validate_json(compliance_case))

    qualified = [
        f"{c['qualifier']}{escalation['reference']}" for c in escalation["candidates"]
    ]
    assert qualified == [
        "pybusiness::docs/subsystems/rounding",
        "architecture::docs/subsystems/rounding",
    ]


def test_the_pass_qualifies_points_normalizes_and_retargets(compliance_case):
    """Each mechanical action is demonstrated, and each takes the documented form."""
    pybusiness = compliance_case / "packages" / "libs" / "pybusiness"

    skill_pass(compliance_case, validate_json(compliance_case))

    realized = (pybusiness / "savings" / "realized.py").read_text().splitlines()
    # Qualified in place, and the ref that already resolved is untouched.
    assert realized[0] == "# Subsystem: docs/subsystems/savings"
    assert realized[2] == "# Subsystem: architecture::docs/subsystems/pricing_rules"
    # Legacy prefix-style normalized to the `::` form.
    assert realized[3] == "# Chunk: architecture::docs/chunks/rsv2_pybusiness_model"
    # The unregistered tree was registered, then qualified against.
    assert realized[4] == "# Subsystem: platform::docs/subsystems/tenancy"
    assert "platform" in run_ve(
        "workspace", "list", "--workspace-dir", str(compliance_case)
    )
    # Two readers in one tree got a peer pointer, and the refs stayed bare.
    assert realized[1] == "# Subsystem: docs/subsystems/commitment_baseline"
    pointer = pybusiness / "docs" / "subsystems" / "commitment_baseline" / "external.yaml"
    assert "tree: architecture" in pointer.read_text()
    # The stale pointer was retargeted to the tree that now holds the artifact,
    # and its interest note survived.
    retargeted = (
        pybusiness / "docs" / "subsystems" / "rate_card" / "external.yaml"
    ).read_text()
    assert "tree: viz" in retargeted
    assert "why: prices come from here" in retargeted


def test_the_pass_deletes_no_reference_and_authors_no_prose(compliance_case):
    """The two invariants, checked against the filesystem."""
    references_before = backreference_lines(compliance_case)
    artifacts_before = artifact_directories(compliance_case)

    skill_pass(compliance_case, validate_json(compliance_case))

    references_after = backreference_lines(compliance_case)
    # Every reference survives, addressing the same artifact as before: the
    # edits only add or normalize a qualifier, so the artifact each line names
    # is unchanged and none is dropped.
    assert sorted(line.split("docs/")[-1] for line in references_after) == sorted(
        line.split("docs/")[-1] for line in references_before
    )

    artifacts_after = artifact_directories(compliance_case)
    new = {
        kind: sorted(set(names) - set(artifacts_before.get(kind, [])))
        for kind, names in artifacts_after.items()
    }
    assert {kind: names for kind, names in new.items() if names} == {
        "packages/libs/pybusiness/docs/subsystems": ["commitment_baseline"]
    }, "the only new artifact directory may be the pointer the skill created"
    created = (
        compliance_case
        / "packages/libs/pybusiness/docs/subsystems/commitment_baseline"
    )
    assert sorted(p.name for p in created.iterdir()) == ["external.yaml"], (
        "a pointer records interest; authoring an OVERVIEW.md would fabricate intent"
    )


# ---------------------------------------------------------------------------
# The remaining mechanical branches
# ---------------------------------------------------------------------------
#
# The GOAL enumerates five actions; the document claims three more, because a
# loop that cannot fix them cannot reach a clean report at all. Each is
# demonstrated here so no promise in the document is untested.


def chunk_with_code_reference(tree: pathlib.Path, name: str, ref: str) -> pathlib.Path:
    """Create a chunk whose frontmatter names one code reference."""
    directory = tree / "docs" / "chunks" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "GOAL.md").write_text(
        "---\n"
        "status: ACTIVE\n"
        "code_references:\n"
        f"- ref: {ref}\n"
        "  implements: the widget\n"
        "---\n\n"
        f"# {name}\n"
    )
    return directory


def test_unknown_qualifier_registers_the_tree_the_reference_already_names(tmp_path):
    """A reference qualified against a real but unlisted tree needs no rewrite."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    make_ve_tree(tmp_path / "packages" / "platform")
    artifact(tmp_path / "packages" / "platform", "chunks", "tenancy_model")
    source(
        tmp_path / "packages" / "lib" / "tenant.py",
        "# Chunk: platform::docs/chunks/tenancy_model",
    )

    before = validate_json(tmp_path)
    assert [d["fix_class"] for d in before["defects"]] == ["unknown-qualifier"]

    assert skill_pass(tmp_path, before) == []

    after = validate_json(tmp_path)
    assert after["ok"], after["defects"]
    assert "platform" in after["members"]
    # The reference itself was never touched: the workspace grew to match it.
    assert (tmp_path / "packages" / "lib" / "tenant.py").read_text() == (
        "# Chunk: platform::docs/chunks/tenancy_model\n"
    )


def test_unresolvable_frontmatter_follows_a_file_that_moved(tmp_path):
    """A rotted code_references path is corrected, never removed."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    lib = tmp_path / "packages" / "lib"
    chunk_with_code_reference(lib, "widget", "src/widget.py#Widget")
    source(lib / "src" / "widget" / "widget.py", "class Widget:", "    pass")

    before = validate_json(tmp_path)
    assert [d["fix_class"] for d in before["defects"]] == ["unresolvable-frontmatter"]

    assert skill_pass(tmp_path, before) == []

    after = validate_json(tmp_path)
    assert after["ok"], after["defects"]
    goal = (lib / "docs" / "chunks" / "widget" / "GOAL.md").read_text()
    assert "- ref: src/widget/widget.py#Widget" in goal
    assert "implements: the widget" in goal, "the entry is retargeted, not dropped"


def test_manifest_error_repoints_a_member_whose_tree_moved(tmp_path):
    """A member path that no longer exists gates `ok`, so the loop must fix it."""
    make_workspace(tmp_path, {"lib": "packages/lib"})
    write_workspace_manifest(tmp_path, {"lib": "packages/lib", "viz": "apps/viz"})
    make_ve_tree(tmp_path / "apps" / "dashboards" / "viz")

    before = validate_json(tmp_path)
    assert len(before["manifest_errors"]) == 1
    assert not before["ok"]

    assert skill_pass(tmp_path, before) == []

    after = validate_json(tmp_path)
    assert after["manifest_errors"] == []
    assert after["ok"]
    assert "apps/dashboards/viz" in (tmp_path / ".ve-workspace.yaml").read_text()
