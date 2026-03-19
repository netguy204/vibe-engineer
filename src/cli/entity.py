"""Entity command group.

# Chunk: docs/chunks/entity_memory_schema

Commands for managing entities - long-running agent personas with persistent memory.
"""

import pathlib

import click

from entities import Entities


@click.group()
def entity():
    """Manage entities - long-running agent personas with persistent memory."""
    pass


@entity.command("create")
@click.argument("name")
@click.option("--role", default=None, help="Brief description of entity's purpose")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def create(name: str, role: str | None, project_dir: pathlib.Path) -> None:
    """Create a new entity with directory structure and identity file.

    NAME is the entity identifier (lowercase, alphanumeric + underscores).
    """
    entities = Entities(project_dir)
    try:
        entity_path = entities.create_entity(name, role=role)
        click.echo(f"Created entity '{name}' at {entity_path}")
    except ValueError as e:
        raise click.ClickException(str(e))


@entity.command("list")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def list_entities(project_dir: pathlib.Path) -> None:
    """List all entities in the current project."""
    entities = Entities(project_dir)
    names = entities.list_entities()

    if not names:
        click.echo("No entities found")
        return

    for name in names:
        identity = entities.parse_identity(name)
        if identity and identity.role:
            click.echo(f"  {name}  ({identity.role})")
        else:
            click.echo(f"  {name}")
