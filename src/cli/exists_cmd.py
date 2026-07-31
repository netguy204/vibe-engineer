"""`ve exists` — evidence-of-absence query.

# Chunk: docs/chunks/crossref_absence_evidence - ve exists CLI command

Answers "does this name (path or symbol) exist anywhere I can see?" and, when
the answer is no, states exactly what was scanned so absence is a fact rather
than silence. Exit code is grep-shaped — 0 when anything matched, 1 when
absent — so fix-loop skills and scripts can branch on it.
"""

import json
import pathlib

import click

from absence import ExistenceQuery, resolve_scope, search_existence

# Text output shows at most this many rows per section; the JSON report is
# always complete.
_TEXT_SECTION_CAP = 20


def _render_section(title: str, rows: list[str]) -> None:
    """Print one match section, capped for readability."""
    if not rows:
        return
    click.echo(f"{title} ({len(rows)}):")
    for row in rows[:_TEXT_SECTION_CAP]:
        click.echo(f"  {row}")
    if len(rows) > _TEXT_SECTION_CAP:
        click.echo(
            f"  … and {len(rows) - _TEXT_SECTION_CAP} more "
            f"(use --format json for the full list)"
        )


@click.command("exists")
@click.argument("name")
@click.option(
    "--dir",
    "start_dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=".",
    help="Directory to resolve visibility from: the workspace found upward, "
    "else the nearest enclosing VE tree, else this directory itself.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format. `json` is the machine-readable form the "
    "validate-fix skills consume.",
)
def exists(name, start_dir, output_format):
    """Report whether NAME (a path or symbol) exists anywhere visible.

    NAME may be a path (`src/mod.py`), a bare symbol (`RealThing`), or a
    `file#symbol` reference fragment (`src/mod.py#RealThing::compute`).
    Matches are reported in three classes: path matches ("still there"),
    same-name-elsewhere matches ("moved"), and symbol matches in source
    content. Absence is reported with the scanned scope and file counts, so
    "not found" is evidence, not silence.

    Exits 0 when anything matched, 1 when absent.
    """
    scope = resolve_scope(start_dir)
    query = ExistenceQuery.parse(name)
    report = search_existence(scope, query)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Query: {report.query}")
        click.echo(f"Scope: {scope.describe()}")
        click.echo()
        _render_section(
            "Path matches",
            [f"{m.path} ({m.kind})" for m in report.path_matches],
        )
        _render_section(
            "Elsewhere with the same name (moved?)",
            [f"{m.path} ({m.kind})" for m in report.basename_matches],
        )
        _render_section(
            "Symbol matches",
            [f"{m.path}:{m.line}  {m.text}" for m in report.symbol_matches],
        )
        if not report.found:
            click.echo(f"Absent: 0 matches for '{report.query}'.")
        click.echo()
        click.echo(
            f"Scanned {report.files_scanned} files "
            f"({report.source_files_scanned} source files searched for symbols) "
            f"rooted at {scope.root}."
        )

    if not report.found:
        raise SystemExit(1)
