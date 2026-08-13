"""Artifact command group.

Commands for artifact management operations.
"""
# Chunk: docs/chunks/cli_modularize - Artifact CLI commands
# Chunk: docs/chunks/artifact_promote - CLI command ve artifact promote <path> [--name]
# Chunk: docs/chunks/copy_as_external - ve artifact copy-external command
# Chunk: docs/chunks/remove_external_ref - ve artifact remove-external command

import json
import pathlib

import click

from task import (
    promote_artifact,
    TaskPromoteError,
    copy_artifact_as_external,
    TaskCopyExternalError,
)
from external_refs import ARTIFACT_DIR_NAME, normalize_artifact_path
from interest import ConsumerReport, InterestEdge, find_consumers
from workspace import WorkspaceError, load_workspace


# Chunk: docs/chunks/artifact_promote - CLI command group for artifact management commands
@click.group()
def artifact():
    """Artifact management commands."""
    pass


@artifact.command()
@click.argument("artifact_path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def promote(artifact_path, new_name, project_dir):
    """Promote a local artifact to the task-level external repository.

    Moves an artifact (chunk, investigation, narrative, or subsystem) from a
    project's docs/ directory to the external artifact repository, leaving
    behind an external reference.

    ARTIFACT_PATH is the path to the local artifact directory to promote.
    """
    # Resolve artifact_path relative to project_dir if needed
    if not artifact_path.is_absolute():
        artifact_path = project_dir / artifact_path

    try:
        result = promote_artifact(artifact_path, new_name=new_name)
    except TaskPromoteError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_artifact_path"]
    external_yaml_path = result["external_yaml_path"]

    click.echo(f"Promoted artifact to external repo: {external_path}")
    click.echo(f"Created external reference: {external_yaml_path}")


# Chunk: docs/chunks/accept_full_artifact_paths - CLI copy-external command using flexible path normalization
@artifact.command("copy-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def copy_external(artifact_path, target_project, new_name, cwd):
    """Copy an external artifact as a reference in a target project.

    Creates an external.yaml in the target project that references an artifact
    already present in the external artifact repository.

    ARTIFACT_PATH accepts flexible formats: "docs/chunks/my_chunk", "chunks/my_chunk",
    or just "my_chunk" (if unambiguous).

    TARGET_PROJECT accepts flexible formats: "acme/proj" or just "proj" (if unambiguous).
    """
    try:
        result = copy_artifact_as_external(
            task_dir=cwd,
            artifact_path=artifact_path,
            target_project=target_project,
            new_name=new_name,
        )
    except TaskCopyExternalError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created path
    external_yaml_path = result["external_yaml_path"]
    click.echo(f"Created external reference: {external_yaml_path}")


@artifact.command("remove-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def remove_external(artifact_path, target_project, cwd):
    """Remove an external artifact reference from a target project.

    Inverse of copy-external. Removes the external.yaml from the target project
    and updates the artifact's dependents list in the external repo.

    ARTIFACT_PATH accepts flexible formats: "docs/chunks/my_chunk", "chunks/my_chunk",
    or just "my_chunk" (if unambiguous).

    TARGET_PROJECT accepts flexible formats: "acme/proj" or just "proj" (if unambiguous).
    """
    from task import remove_artifact_from_external, TaskRemoveExternalError

    try:
        result = remove_artifact_from_external(
            task_dir=cwd,
            artifact_path=artifact_path,
            target_project=target_project,
        )
    except TaskRemoveExternalError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report what was done
    if result["removed"]:
        click.echo(f"Removed external reference for '{artifact_path}' from '{target_project}'")
        if result["directory_cleaned"]:
            click.echo("  (empty directory cleaned up)")
        if result["dependent_removed"]:
            click.echo("  (updated dependents in source artifact)")

        # Warn if artifact is now orphaned
        if result["orphaned"]:
            click.echo(
                "\nWarning: This artifact has no remaining project links. "
                "Consider removing it from the external repository if it's no longer needed."
            )
    else:
        click.echo(f"No external reference found for '{artifact_path}' in '{target_project}' (already removed)")


# Subsystem: docs/subsystems/cross_repo_operations - Interest edges read backwards
# Chunk: docs/chunks/federation_reverse_interest - ve artifact consumers
@artifact.command()
@click.argument("artifact_path")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
    help="The tree that owns the artifact (default: the nearest enclosing tree).",
)
def consumers(artifact_path, json_output, project_dir):
    """List the trees in this workspace that record interest in ARTIFACT_PATH.

    Answers the reverse of an external.yaml pointer: instead of "what does this
    pointer target?", it asks "who points at me?". Ownership stays with the tree
    whose code enforces the intent; this is how that tree finds its readers.

    ARTIFACT_PATH accepts "docs/subsystems/name", "subsystems/name", or just
    "name" when it exists in this tree.

    Peer (`tree:`) pointers are reported when they resolve to exactly this
    artifact directory. Cross-repo (`repo:`) pointers naming the same artifact id
    are reported separately, because nothing here can verify that a repository's
    artifact is this one.
    """
    # Resolve before anything consults the manifest: `Workspace.find_member_for_path`
    # interprets a relative path against the *workspace root*, so the default "."
    # would name the root tree instead of the tree the operator is standing in -
    # the exact class of silent misresolution this narrative exists to remove.
    owner_root = pathlib.Path(project_dir).resolve()

    try:
        ws = load_workspace(owner_root)
    except WorkspaceError as exc:
        click.echo(
            f"Error: {exc}\n"
            f"Reverse interest lookup enumerates the trees a manifest names, so "
            f"without one there is nothing to search; `ve workspace init --scan` "
            f"proposes the trees it finds.",
            err=True,
        )
        raise SystemExit(1)

    try:
        artifact_type, artifact_id = normalize_artifact_path(
            artifact_path, search_path=owner_root
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)

    report = find_consumers(
        ws,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        owner_root=owner_root,
    )

    # A peer pointer addresses a *member*, so an unregistered owning tree cannot
    # be pointed at by anything. Reporting "no consumers" would answer a question
    # that was never askable; report the configuration defect instead.
    if report.owner_member is None:
        enclosing_member = ws.find_member_for_path(owner_root)
        enclosing = (
            f" (it lies inside member '{enclosing_member.name}')"
            if enclosing_member
            else ""
        )
        click.echo(
            f"Error: {owner_root} is not a registered member of the workspace at "
            f"{ws.root}{enclosing}. A peer pointer names a member, so no pointer "
            f"can address this tree's artifacts. Register it with "
            f"`ve workspace add <name> <path>`.",
            err=True,
        )
        raise SystemExit(1)

    if json_output:
        click.echo(json.dumps(_consumers_json(ws, report), indent=2))
        return

    _display_consumer_report(ws, report)


def _edge_row(edge: InterestEdge, width: int, show_target: bool) -> str:
    """Format one inbound edge as an aligned row."""
    row = f"  {edge.member.ljust(width)}  {edge.pointer_rel}"
    if show_target:
        row += f" -> {edge.target_display}"
    if edge.why:
        row += f"\n  {' ' * width}  why: {edge.why}"
    else:
        row += f"\n  {' ' * width}  (no why: recorded)"
    return row


# Chunk: docs/chunks/federation_reverse_interest - Consumer report rendering
def _display_consumer_report(ws, report: ConsumerReport) -> None:
    """Print a consumer report, keeping resolved and id-matched answers apart."""
    owner_member = report.owner_member
    dir_name = ARTIFACT_DIR_NAME[report.artifact_type]
    click.echo(
        f"Artifact: docs/{dir_name}/{report.artifact_id} "
        f"({report.artifact_type.value})"
    )
    click.echo(f"Owner: {owner_member.name} ({owner_member.path})")
    click.echo(f"Workspace: {ws.root}")

    if not report.target_exists:
        click.echo(
            f"Warning: {report.target_dir} does not exist. Any pointer listed "
            f"below cannot resolve.",
            err=True,
        )

    if report.peers:
        width = max(len(edge.member) for edge in report.peers)
        click.echo("")
        click.echo(
            f"Consumers ({len(report.peers)} peer pointer(s) addressing this artifact):"
        )
        for edge in report.peers:
            click.echo(_edge_row(edge, width, show_target=False))
    else:
        click.echo("")
        click.echo(
            f"No consumers: no tree in this workspace holds a peer pointer at "
            f"docs/{dir_name}/{report.artifact_id}."
        )
        click.echo(
            f"A consuming tree records interest with "
            f"`ve external point {owner_member.name} docs/{dir_name}/"
            f"{report.artifact_id} --why '<what it depends on>'`."
        )

    if report.cross_repo:
        width = max(len(edge.member) for edge in report.cross_repo)
        click.echo("")
        click.echo(
            f"Cross-repo pointers naming artifact id '{report.artifact_id}' "
            f"({len(report.cross_repo)}) - matched by artifact id, not verified to "
            f"be this artifact:"
        )
        for edge in report.cross_repo:
            click.echo(_edge_row(edge, width, show_target=True))

    if report.malformed:
        click.echo("")
        click.echo(
            f"Unreadable pointers ({len(report.malformed)}) - these could not be "
            f"parsed, so their interest is unknown:",
            err=True,
        )
        for bad in report.malformed:
            click.echo(f"  {bad.member}  {bad.pointer_rel}: {bad.message}", err=True)


def _consumers_json(ws, report: ConsumerReport) -> dict:
    """Serialize a consumer report.

    Both flavors share one `consumers` array so a caller does not have to know
    the addressing model to enumerate interest, with `flavor` and `verified`
    preserving the distinction the text report makes with sections.
    """
    owner_member = report.owner_member
    dir_name = ARTIFACT_DIR_NAME[report.artifact_type]

    def edge_dict(edge: InterestEdge, verified: bool) -> dict:
        return {
            "member": edge.member,
            "flavor": edge.flavor,
            "verified": verified,
            "pointer": edge.pointer_rel,
            "qualified_pointer": edge.qualified_pointer,
            "target": edge.target_display,
            "artifact_id": edge.ref.artifact_id,
            "why": edge.why,
        }

    return {
        "workspace_root": str(ws.root),
        "artifact_type": report.artifact_type.value,
        "artifact_id": report.artifact_id,
        "artifact_path": f"docs/{dir_name}/{report.artifact_id}",
        "owner": owner_member.name,
        "owner_path": owner_member.path,
        "target_exists": report.target_exists,
        "consumers": [edge_dict(edge, True) for edge in report.peers]
        + [edge_dict(edge, False) for edge in report.cross_repo],
        "unreadable_pointers": [
            {"member": bad.member, "pointer": bad.pointer_rel, "error": bad.message}
            for bad in report.malformed
        ],
    }
