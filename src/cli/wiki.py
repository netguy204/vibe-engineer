"""Wiki maintenance commands.

# Chunk: docs/chunks/wiki_reindex_command - wiki CLI command group
# Chunk: docs/chunks/wiki_lint_command - wiki lint subcommand
"""

import pathlib

import click

from entities import Entities
from entity_repo import reindex_wiki
import entity_repo
from cli.entity import resolve_entity_project_dir


@click.group()
def wiki():
    """Wiki maintenance commands for entity knowledge bases."""
    pass


@wiki.command("reindex")
@click.argument("entity")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="Project directory containing .entities/ (default: auto-detected)",
)
def reindex(entity: str, project_dir: pathlib.Path | None) -> None:
    """Regenerate wiki/index.md from page frontmatter.

    Scans all wiki pages for ENTITY and rewrites index.md, grouping
    pages by directory (domain, techniques, projects, relationships)
    and sorting alphabetically. Existing summaries are preserved.
    """
    project = resolve_entity_project_dir(project_dir)
    entities = Entities(project)

    if not entities.entity_exists(entity):
        raise click.ClickException(f"Entity '{entity}' not found")
    if not entities.has_wiki(entity):
        raise click.ClickException(
            f"Entity '{entity}' does not have a wiki/ directory"
        )

    wiki_dir = entities.entity_dir(entity) / "wiki"
    result = reindex_wiki(wiki_dir, entity_name=entity)

    click.echo(
        f"Reindexed wiki for '{entity}': "
        f"{result.pages_total} page(s) across {result.directories_scanned} section(s)"
    )


@wiki.command("lint")
@click.argument("entity_name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="Project directory (default: auto-detected from CWD)",
)
def wiki_lint(entity_name: str, project_dir: pathlib.Path | None) -> None:
    """Check wiki integrity for an entity.

    # Chunk: docs/chunks/wiki_lint_command - Wiki lint CLI command

    Checks for dead wikilinks, frontmatter errors, pages missing from
    the index, and orphan pages. Exits 0 if clean, 1 if issues found.

    Output format: one issue per line:
      <file>: [<type>] <detail>
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)

    if not entities.entity_exists(entity_name):
        raise click.ClickException(f"Entity '{entity_name}' not found")

    if not entities.has_wiki(entity_name):
        raise click.ClickException(
            f"Entity '{entity_name}' has no wiki directory. "
            "Only wiki-based entities can be linted."
        )

    wiki_dir = entities.entity_dir(entity_name) / "wiki"
    result = entity_repo.lint_wiki(wiki_dir)

    for issue in result.issues:
        click.echo(f"{issue.file}: [{issue.issue_type}] {issue.detail}")

    if not result.ok:
        raise SystemExit(1)
