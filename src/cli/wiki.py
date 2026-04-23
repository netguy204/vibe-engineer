"""Wiki command group.

# Chunk: docs/chunks/wiki_rename_command - CLI commands for entity wiki management

Commands for managing entity wiki pages.
"""

import pathlib

import click

import entity_repo
from cli.entity import resolve_entity_project_dir


@click.group()
def wiki():
    """Manage entity wiki pages."""
    pass


# Chunk: docs/chunks/wiki_rename_command - ve wiki rename command
@wiki.command("rename")
@click.argument("entity")
@click.argument("old_path")
@click.argument("new_path")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def rename(
    entity: str,
    old_path: str,
    new_path: str,
    project_dir: pathlib.Path | None,
) -> None:
    """Rename a wiki page and update all inbound wikilinks.

    ENTITY is the entity identifier (subdirectory under .entities/).
    OLD_PATH is the current page path within wiki/ (without .md extension).
    NEW_PATH is the new page path within wiki/ (without .md extension).

    Moves the file, rewrites all [[wikilinks]] that referenced the old path,
    and updates index.md automatically. Reports the number of files updated.

    Examples:

        ve wiki rename skippy domain/world-model domain/world-model-v2

        ve wiki rename skippy techniques/old-sop techniques/updated-sop
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entity_path = project_dir / ".entities" / entity

    if not entity_path.exists():
        raise click.ClickException(f"Entity '{entity}' not found")

    try:
        result = entity_repo.wiki_rename(entity_path, old_path, new_path)
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo(f"Renamed '{old_path}' → '{new_path}'")
    click.echo(f"  Files updated: {result.files_updated}")
