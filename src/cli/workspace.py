"""Workspace command group.

# Chunk: docs/chunks/federation_workspace_manifest - ve workspace CLI commands
# Chunk: docs/chunks/federation_global_validator - ve workspace validate

Commands that operate on a whole repository of VE trees: `init`/`add`/`list`
manage the `.ve-workspace.yaml` manifest that names them, and `validate` checks
that every reference across them resolves.

All commands take `--workspace-dir` (default ".") and search upward from it for
the manifest, so they work from anywhere inside the workspace. That option is
deliberately distinct from `--project-dir`, which identifies a single tree rather
than the workspace containing many.
"""

import json
import pathlib
import textwrap

import click

from workspace import (
    WORKSPACE_MANIFEST_NAME,
    Workspace,
    WorkspaceError,
    WorkspaceManifestError,
    add_member,
    find_workspace_root,
    is_ve_tree,
    load_workspace,
    relativize_to_workspace,
    save_workspace,
    scan_for_trees,
    suggest_member_names,
    write_manifest,
)
from models.workspace import WorkspaceManifest
from workspace_validation import ValidationReport, validate_workspace


workspace_dir_option = click.option(
    "--workspace-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=".",
    help="Directory to search upward from for the workspace manifest.",
)


@click.group()
def workspace():
    """Workspace manifest commands (multiple VE trees in one repository)."""
    pass


def _load_or_exit(workspace_dir: pathlib.Path) -> Workspace:
    """Load the workspace or exit nonzero with an actionable message."""
    try:
        return load_workspace(workspace_dir)
    except WorkspaceError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/federation_workspace_manifest - ve workspace list
@workspace.command("list")
@workspace_dir_option
def list_members(workspace_dir):
    """List the VE trees registered in the workspace."""
    ws = _load_or_exit(workspace_dir)

    click.echo(f"Workspace: {ws.root}")
    if not ws.members:
        click.echo("No members registered. Add one with `ve workspace add <name> <path>`.")
        return

    width = max(len(member.name) for member in ws.members)
    for member in ws.members:
        path = ws.member_path(member)
        if not path.exists():
            marker = "  [missing: path does not exist]"
        elif not is_ve_tree(path):
            marker = "  [missing: no VE tree at this path]"
        else:
            marker = ""
        click.echo(f"  {member.name.ljust(width)}  {member.path}{marker}")


# Chunk: docs/chunks/federation_workspace_manifest - ve workspace add
@workspace.command()
@click.argument("name")
@click.argument("path")
@workspace_dir_option
def add(name, path, workspace_dir):
    """Register a VE tree as workspace member NAME at PATH.

    PATH may be absolute or relative to the workspace root. It must exist and
    contain a VE tree (a docs/ directory with at least one artifact directory).
    """
    ws = _load_or_exit(workspace_dir)

    try:
        relative = relativize_to_workspace(ws.root, path)
        updated = add_member(ws, name, relative)
    except WorkspaceManifestError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)

    save_workspace(updated)
    click.echo(f"Registered member '{name}' -> {updated.manifest.get(name).path}")


# Chunk: docs/chunks/federation_workspace_manifest - ve workspace init with scan bootstrap
@workspace.command()
@click.option(
    "--scan",
    is_flag=True,
    help="Discover candidate VE trees (directories containing docs/trunk/) and "
         "propose them for registration.",
)
@click.option(
    "--exclude",
    multiple=True,
    metavar="GLOB",
    help="Glob matched against a candidate's relative path and directory name; "
         "matching directories are skipped along with everything beneath them. "
         "Repeatable.",
)
@click.option("-y", "--yes", is_flag=True, help="Skip the confirmation prompt.")
@workspace_dir_option
def init(scan, exclude, yes, workspace_dir):
    """Create a workspace manifest at WORKSPACE_DIR.

    Without --scan, writes an empty manifest for you to populate with
    `ve workspace add`. With --scan, proposes the VE trees found beneath the
    directory and writes them once you confirm.

    A scan is a bootstrap aid, not the authority: it cannot tell an intentional
    tree from an accidental one (a scaffolding template that ships its own docs
    tree looks identical), so candidates are always presented for confirmation.
    """
    root = workspace_dir.resolve()

    existing = root / WORKSPACE_MANIFEST_NAME
    if existing.exists():
        click.echo(
            f"Error: {existing} already exists. Use `ve workspace add` to register "
            f"more trees, or delete the file to start over.",
            err=True,
        )
        raise SystemExit(1)

    enclosing = find_workspace_root(root)
    if enclosing is not None:
        click.echo(
            f"Warning: {enclosing} is already a workspace root. Nesting workspaces "
            f"is not supported; consider `ve workspace add` there instead.",
            err=True,
        )

    if not scan:
        write_manifest(root, WorkspaceManifest())
        click.echo(f"Created {root / WORKSPACE_MANIFEST_NAME} with no members.")
        click.echo("Register trees with `ve workspace add <name> <path>`.")
        return

    candidates = suggest_member_names(scan_for_trees(root, exclude), root=root)

    if not candidates:
        write_manifest(root, WorkspaceManifest())
        click.echo(f"No VE trees found under {root} (looked for docs/trunk/).")
        click.echo(f"Created {root / WORKSPACE_MANIFEST_NAME} with no members.")
        return

    click.echo(f"Discovered {len(candidates)} candidate VE tree(s) under {root}:")
    width = max(len(name) for name, _ in candidates)
    for name, rel_path in candidates:
        click.echo(f"  {name.ljust(width)}  {rel_path}")
    click.echo(
        "Re-run with --exclude '<glob>' to drop candidates that are not real "
        "trees (for example a scaffolding template that ships a docs/ tree)."
    )

    if not yes and not click.confirm(f"Register these {len(candidates)} tree(s)?"):
        click.echo("Aborted. No manifest written.", err=True)
        raise SystemExit(1)

    manifest = WorkspaceManifest.model_validate(
        {"members": {name: rel_path for name, rel_path in candidates}}
    )
    write_manifest(root, manifest)
    click.echo(f"Created {root / WORKSPACE_MANIFEST_NAME} with {len(candidates)} member(s).")


# Chunk: docs/chunks/federation_global_validator - Coverage caveats printed with every report
# Stated on every run, clean or not. The case study's damage was silent
# misresolution, so a report that implied total coverage would recreate the
# failure it exists to prevent.
SCAN_CAVEAT = (
    "Note: only backreference comments starting at column 0 are scanned, so "
    "indented\n      comments inside classes and functions are invisible to this "
    "report. A clean\n      run means every column 0 reference resolves, not every "
    "reference."
)


# Chunk: docs/chunks/federation_global_validator - Human-readable report rendering
def _render_report(report: ValidationReport) -> None:
    """Print a validation report grouped by fix class."""
    click.echo(f"Workspace: {report.workspace_root}")
    click.echo(f"Members:   {', '.join(report.members) or '(none)'}")
    click.echo(
        f"Scanned {report.files_scanned} file(s), {report.references_checked} "
        f"reference(s), {report.artifacts_scanned} artifact(s), "
        f"{report.pointers_checked} pointer(s)."
    )

    grouped = report.by_fix_class()
    for fix_class, defects in grouped.items():
        click.echo(f"\n{fix_class.value} ({len(defects)})")
        for defect in defects:
            click.echo(f"  {defect.location}")
            click.echo(f"    ref: {defect.reference}")
            # Wrapped: on a monorepo this report is long, and a defect whose
            # explanation runs off the terminal is a defect nobody reads. Long
            # words are never broken — a split path or qualifier is not
            # copy-pasteable, which is the whole point of printing it.
            click.echo(
                textwrap.fill(
                    defect.message,
                    width=84,
                    initial_indent="    ",
                    subsequent_indent="    ",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )

    if report.manifest_errors:
        click.echo(f"\nmanifest ({len(report.manifest_errors)})")
        for message in report.manifest_errors:
            click.echo(f"  {message}")

    click.echo("")
    if report.defects:
        click.echo(
            f"{len(report.defects)} reference defect(s) in {len(grouped)} fix class(es)."
        )
    elif not report.manifest_errors:
        click.echo("No reference defects found.")

    if report.unverified:
        click.echo(
            f"{len(report.unverified)} reference(s) not verified: cross-repository "
            f"targets are not resolved offline."
        )

    if report.unregistered_trees:
        click.echo(
            f"Note: {len(report.unregistered_trees)} VE tree(s) are not workspace "
            f"members: {', '.join(report.unregistered_trees)}.\n"
            f"      Their references resolve, but nothing can be qualified against "
            f"them until\n      you `ve workspace add` them."
        )

    click.echo(SCAN_CAVEAT)


# Chunk: docs/chunks/federation_global_validator - ve workspace validate
@workspace.command("validate")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format. `json` is the machine-readable form the validate-fix "
         "skill consumes.",
)
@workspace_dir_option
def validate(output_format, workspace_dir):
    """Validate every reference in the workspace and report all defects.

    Walks every source file in the workspace and every registered member's
    artifacts, reporting each defect with its `path:line`, the failing
    reference, and a fix class: unresolvable-bare, misrouted-bare,
    unknown-qualifier, missing-target, malformed-qualifier, or
    unresolvable-frontmatter. Exits nonzero on any defect, so CI can gate on it.

    Two limits are deliberate. Only backreference comments starting at column 0
    are scanned, so indented comments are not covered — a clean run means every
    column 0 reference resolves, not every reference. And `org/repo` targets are
    reported as unverified rather than checked, because resolving them needs
    network or cache state, and a gate whose verdict depends on a warm cache is
    not a gate.
    """
    ws = _load_or_exit(workspace_dir)
    report = validate_workspace(ws)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        _render_report(report)

    if not report.ok:
        raise SystemExit(1)
