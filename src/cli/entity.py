"""Entity command group.

# Chunk: docs/chunks/entity_memory_schema
# Chunk: docs/chunks/entity_startup_skill - Startup and recall CLI commands
# Chunk: docs/chunks/entity_shutdown_skill
# Chunk: docs/chunks/entity_shutdown_silent_failure - Entity CLI root resolution

Commands for managing entities - long-running agent personas with persistent memory.
"""

import json
import pathlib
import sys

import click

from entities import Entities


# Chunk: docs/chunks/entity_shutdown_silent_failure - Entity CLI root resolution
def resolve_entity_project_dir(explicit_dir: pathlib.Path | None) -> pathlib.Path:
    """Resolve the project directory for entity commands.

    When --project-dir is not provided (None), walks up from CWD to find
    the project root using the same chain as board/orch commands:
    .ve-task.yaml → .git → CWD fallback.
    """
    from board.storage import resolve_project_root
    return resolve_project_root(explicit_dir)


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
    default=None,
)
def create(name: str, role: str | None, project_dir: pathlib.Path) -> None:
    """Create a new entity with directory structure and identity file.

    NAME is the entity identifier (lowercase, alphanumeric + underscores).
    """
    project_dir = resolve_entity_project_dir(project_dir)
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
    default=None,
)
def list_entities(project_dir: pathlib.Path) -> None:
    """List all entities in the current project."""
    project_dir = resolve_entity_project_dir(project_dir)
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
    default=None,
)
def startup(name: str, project_dir: pathlib.Path) -> None:
    """Render the startup payload for a named entity.

    NAME is the entity to wake up. Outputs the full startup context
    including identity, core memories, consolidated memory index,
    and touch protocol instructions.
    """
    project_dir = resolve_entity_project_dir(project_dir)
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
    default=None,
)
def recall(name: str, query: str, project_dir: pathlib.Path) -> None:
    """Recall memories matching a query for a named entity.

    NAME is the entity to search. QUERY is a case-insensitive
    substring to match against memory titles.
    """
    project_dir = resolve_entity_project_dir(project_dir)
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


# Chunk: docs/chunks/entity_touch_command
@entity.command("touch")
@click.argument("name")
@click.argument("memory_id")
@click.argument("reason", required=False, default=None)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, path_type=pathlib.Path),
    default=None,
)
def touch(name: str, memory_id: str, reason: str | None, project_dir: pathlib.Path) -> None:
    """Touch a memory to record runtime reinforcement.

    NAME is the entity identifier.
    MEMORY_ID is the filename stem (without .md) of the memory to touch.
    REASON is an optional description of why the memory was useful.
    """
    project_dir = resolve_entity_project_dir(project_dir)
    entities = Entities(project_dir)
    try:
        event = entities.touch_memory(name, memory_id, reason)
        click.echo(f"Touched '{event.memory_title}' (last_reinforced updated)")
    except ValueError as e:
        raise click.ClickException(str(e))


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
    default=None,
)
def shutdown(name: str, memories_file: pathlib.Path | None, project_dir: pathlib.Path) -> None:
    """Run the sleep cycle: consolidate extracted memories for an entity.

    Reads extracted journal memories (JSON array) from --memories-file or stdin,
    then runs incremental consolidation against the entity's existing memory tiers.

    NAME is the entity identifier.
    """
    from entity_shutdown import run_consolidation

    project_dir = resolve_entity_project_dir(project_dir)
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
        memories_json = "[]"  # Treat truly empty input as empty array

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
    click.echo(f"  Journals processed: {result['journals_consolidated']}")
    click.echo(f"  Consolidated:    {result['consolidated']}")
    click.echo(f"  Core:            {result['core']}")
