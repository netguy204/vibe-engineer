"""`ve deletion` — operator-authorized reference-deletion grants.

# Chunk: docs/chunks/crossref_absence_evidence - ve deletion CLI commands

`record` writes a grant into the governing tree's `docs/trunk/DELETIONS.md`
before a reference is removed, so the deletion and its authorization land in
the same diff. `list` shows the grants. Neither command touches git
(DEC-005).
"""

import json
import pathlib

import click

from deletions import DeletionLedger, DeletionLedgerError


project_dir_option = click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=".",
    help="The VE tree that governed the deleted reference.",
)


@click.group()
def deletion():
    """Operator-authorized reference-deletion grants (docs/trunk/DELETIONS.md)."""
    pass


@deletion.command("record")
@click.argument("reference")
@click.option(
    "--location",
    required=True,
    help="Where the reference is being deleted from, as `file:line`.",
)
@click.option(
    "--by",
    "authorized_by",
    required=True,
    help="The operator who authorized this deletion.",
)
@click.option(
    "--reason",
    required=True,
    help="Why deleting the reference is correct (e.g. the code was "
    "deliberately deleted).",
)
@click.option(
    "--evidence",
    default=None,
    help="Absence evidence backing the grant — typically the summary line of "
    "`ve exists <name>`.",
)
@project_dir_option
def record(reference, location, authorized_by, reason, evidence, project_dir):
    """Record an operator grant to delete REFERENCE.

    Run this BEFORE removing the reference, so the grant and the deletion
    land in the same diff and a reviewer can see the authorization. A
    reference deletion without a recorded grant remains out of vocabulary
    for validation fix loops.
    """
    ledger = DeletionLedger(pathlib.Path(project_dir))
    try:
        entry_id = ledger.record(
            reference=reference,
            location=location,
            authorized_by=authorized_by,
            reason=reason,
            evidence=evidence,
        )
    except DeletionLedgerError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)

    click.echo(
        f"Recorded {entry_id}: `{reference}` (deleted from {location}, "
        f"authorized by {authorized_by}) in {ledger.path}"
    )


@deletion.command("list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@project_dir_option
def list_grants(output_format, project_dir):
    """List every recorded deletion grant in this tree."""
    grants = DeletionLedger(pathlib.Path(project_dir)).entries()

    if output_format == "json":
        click.echo(json.dumps([grant.to_dict() for grant in grants], indent=2))
        return

    if not grants:
        click.echo("No deletion grants recorded.")
        return
    for grant in grants:
        click.echo(
            f"{grant.id}  {grant.date}  `{grant.reference}` "
            f"deleted from {grant.location} — authorized by {grant.authorized_by}"
        )
        click.echo(f"      Reason: {grant.reason}")
        if grant.evidence:
            click.echo(f"      Evidence: {grant.evidence}")
