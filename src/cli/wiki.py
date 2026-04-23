"""Wiki maintenance commands.

# Chunk: docs/chunks/wiki_reindex_command - wiki CLI command group
"""

import pathlib

import click

from entities import Entities
from entity_repo import reindex_wiki
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
