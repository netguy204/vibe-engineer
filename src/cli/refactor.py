"""`ve refactor` — evidence-backed refactoring propagation.

# Chunk: docs/chunks/crossref_refactor_move - `ve refactor move` CLI

`move OLD NEW` rewrites every chunk/subsystem frontmatter reference naming
OLD with reviewable evidence (git rename/deletion shas, AST symbol
verification), surfaces `implements:` prose at every ambiguous decision
point, and reports never-existed symbols as a distinct reconstruct-or-drop
disposition instead of a futile rename hunt.
"""

import json
import pathlib

import click

from refactor_move import (
    DISPOSITION_AMBIGUOUS,
    DISPOSITION_NEVER_EXISTED,
    DISPOSITION_REWRITTEN,
    MoveDecision,
    RefactorMoveError,
    execute_move,
)


@click.group()
def refactor():
    """Propagate refactorings (moves, renames) into artifact references."""
    pass


def _echo_entry_header(decision: MoveDecision) -> None:
    entry = decision.entry
    click.echo(f"  {entry.artifact} [{entry.field_name}] {entry.raw}")
    if entry.implements:
        click.echo(f"    implements: {entry.implements}")


@refactor.command("move")
@click.argument("old")
@click.argument("new")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=".",
    help="The VE tree whose references should be rewritten.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Report every disposition without writing anything.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
def move(old, new, project_dir, dry_run, output_format):
    """Rewrite references after code moved from OLD to NEW, with evidence.

    Unambiguous successors are rewritten (git shas and AST verification in
    the report); ambiguous entries are left unchanged and reported with
    their `implements:` prose and candidates; symbols with no successor
    anywhere in scope are reported NEVER_EXISTED (reconstruct or drop —
    record drops with `ve deletion record`). References are never deleted.
    """
    try:
        report = execute_move(project_dir, old, new, apply=not dry_run)
    except RefactorMoveError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    click.echo(f"Move: {report.old} -> {report.new}")
    click.echo(f"Git evidence: {report.git_evidence.summary()}")
    if dry_run:
        click.echo("(dry run — nothing written)")
    click.echo()

    rewritten = report.by_disposition(DISPOSITION_REWRITTEN)
    ambiguous = report.by_disposition(DISPOSITION_AMBIGUOUS)
    never_existed = report.by_disposition(DISPOSITION_NEVER_EXISTED)

    verb = "Would rewrite" if dry_run else "Rewrote"
    click.echo(f"{verb} {len(rewritten)} reference(s):")
    for decision in rewritten:
        entry = decision.entry
        click.echo(
            f"  {entry.artifact} [{entry.field_name}] "
            f"{entry.raw} -> {decision.new_value}"
        )
        for line in decision.evidence:
            click.echo(f"    evidence: {line}")

    if ambiguous:
        click.echo()
        click.echo(
            f"Ambiguous — left unchanged, operator decision needed "
            f"({len(ambiguous)}):"
        )
        for decision in ambiguous:
            _echo_entry_header(decision)
            for line in decision.evidence:
                click.echo(f"    evidence: {line}")
            for candidate in decision.candidates:
                click.echo(f"    candidate: {candidate}")

    if never_existed:
        click.echo()
        click.echo(
            f"Never existed at the destination or anywhere in scope — "
            f"reconstruct or drop ({len(never_existed)}):"
        )
        for decision in never_existed:
            _echo_entry_header(decision)
            for line in decision.evidence:
                click.echo(f"    evidence: {line}")
            if decision.absence_basis:
                counts = decision.absence_basis.get("counts", {})
                scope = decision.absence_basis.get("scope", {})
                click.echo(
                    f"    absence basis: {scope.get('kind')} scope, "
                    f"{counts.get('files_scanned', 0)} files scanned, "
                    f"{counts.get('source_files_scanned', 0)} source files "
                    "scanned"
                )
        click.echo(
            "  (a drop is an operator decision: record it with "
            "`ve deletion record` before removing the reference)"
        )

    click.echo()
    click.echo(
        f"Summary: {len(rewritten)} rewritten, {len(ambiguous)} ambiguous, "
        f"{len(never_existed)} never-existed"
        f" ({len(report.decisions)} matching reference(s) total)"
    )
