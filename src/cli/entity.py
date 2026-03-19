"""Entity command group.

# Chunk: docs/chunks/entity_memory_schema
# Chunk: docs/chunks/entity_startup_skill - Startup and recall CLI commands

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


@entity.command("startup")
@click.argument("name")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def startup(name: str, project_dir: pathlib.Path) -> None:
    """Render the startup payload for a named entity.

    NAME is the entity to wake up. Outputs the full startup context
    including identity, core memories, consolidated memory index,
    and touch protocol instructions.
    """
    entities = Entities(project_dir)
    try:
        payload = entities.startup_payload(name)
        click.echo(payload)
    except ValueError as e:
        raise click.ClickException(str(e))


@entity.command("recall")
@click.argument("name")
@click.argument("query")
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def recall(name: str, query: str, project_dir: pathlib.Path) -> None:
    """Recall memories matching a query for a named entity.

    NAME is the entity to search. QUERY is a case-insensitive
    substring to match against memory titles.
    """
    entities = Entities(project_dir)
    try:
        results = entities.recall_memory(name, query)
    except ValueError as e:
        raise click.ClickException(str(e))

    if not results:
        click.echo(f"No memories matching '{query}'")
        return

    for result in results:
        fm = result["frontmatter"]
        click.echo(f"## {fm['title']}")
        click.echo(f"*Tier: {result['tier']} | Category: {fm['category']}*")
        click.echo("")
        click.echo(result["content"])
        click.echo("")
