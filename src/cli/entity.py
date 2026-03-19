"""Entity command group.

# Chunk: docs/chunks/entity_memory_schema
# Chunk: docs/chunks/entity_shutdown_skill

Commands for managing entities - long-running agent personas with persistent memory.
"""

import json
import pathlib
import sys

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


# Chunk: docs/chunks/entity_shutdown_skill
@entity.command("shutdown")
@click.argument("name")
@click.option(
    "--memories-file",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
    help="JSON file with extracted memories (alternative to stdin)",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=".",
)
def shutdown(name: str, memories_file: pathlib.Path | None, project_dir: pathlib.Path) -> None:
    """Run the sleep cycle: consolidate extracted memories for an entity.

    Reads extracted journal memories (JSON array) from --memories-file or stdin,
    then runs incremental consolidation against the entity's existing memory tiers.

    NAME is the entity identifier.
    """
    from entity_shutdown import run_consolidation

    entities = Entities(project_dir)

    # Validate entity exists
    if not entities.entity_exists(name):
        raise click.ClickException(f"Entity '{name}' not found")

    # Read memories JSON
    if memories_file is not None:
        memories_json = memories_file.read_text()
    elif not sys.stdin.isatty():
        memories_json = sys.stdin.read()
    else:
        raise click.ClickException(
            "No memories provided. Use --memories-file or pipe JSON to stdin."
        )

    if not memories_json.strip():
        raise click.ClickException("Empty memories input")

    try:
        result = run_consolidation(
            entity_name=name,
            extracted_memories_json=memories_json,
            project_dir=project_dir,
        )
    except Exception as e:
        raise click.ClickException(f"Consolidation failed: {e}")

    # Print summary
    click.echo(f"Shutdown complete for entity '{name}':")
    click.echo(f"  Journals added:  {result['journals_added']}")
    click.echo(f"  Consolidated:    {result['consolidated']}")
    click.echo(f"  Core:            {result['core']}")
