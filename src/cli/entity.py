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


# Chunk: docs/chunks/entity_touch_command
@entity.command("touch")
@click.argument("name")
@click.argument("memory_id")
@click.argument("reason", required=False, default=None)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def touch(name: str, memory_id: str, reason: str | None, project_dir: pathlib.Path) -> None:
    """Touch a memory to record runtime reinforcement.

    NAME is the entity identifier.
    MEMORY_ID is the filename stem (without .md) of the memory to touch.
    REASON is an optional description of why the memory was useful.
    """
    entities = Entities(project_dir)
    try:
        event = entities.touch_memory(name, memory_id, reason)
        click.echo(f"Touched '{event.memory_title}' (last_reinforced updated)")
    except ValueError as e:
        raise click.ClickException(str(e))
