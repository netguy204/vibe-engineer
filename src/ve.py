"""Vibe Engineer CLI - view layer for chunk management."""

import pathlib
import re

import click

from chunks import Chunks
from project import Project


def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    errors = []

    if " " in short_name:
        errors.append("short_name cannot contain spaces")

    if not re.match(r'^[a-zA-Z0-9_-]+$', short_name):
        invalid_chars = re.sub(r'[a-zA-Z0-9_-]', '', short_name)
        errors.append(f"short_name contains invalid characters: {invalid_chars!r}")

    if len(short_name) >= 32:
        errors.append(f"short_name must be less than 32 characters (got {len(short_name)})")

    return errors


def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    errors = []

    if " " in ticket_id:
        errors.append("ticket_id cannot contain spaces")

    if not re.match(r'^[a-zA-Z0-9_-]+$', ticket_id):
        invalid_chars = re.sub(r'[a-zA-Z0-9_-]', '', ticket_id)
        errors.append(f"ticket_id contains invalid characters: {invalid_chars!r}")

    return errors


@click.group()
def cli():
    """Vibe Engineer"""
    pass


@cli.command()
@click.option("--project-dir", type=click.Path(path_type=pathlib.Path), default=".")
def init(project_dir):
    """Initialize the Vibe Engineer document store."""
    project = Project(project_dir)
    result = project.init()

    for path in result.created:
        click.echo(f"Created {path}")

    if result.skipped:
        click.echo(f"Skipped {len(result.skipped)} existing file(s)")

    for warning in result.warnings:
        click.echo(f"Warning: {warning}", err=True)


@cli.group()
def chunk():
    """Chunk commands"""
    pass


@chunk.command()
@click.argument("short_name")
@click.argument("ticket_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def start(short_name, ticket_id, project_dir, yes):
    """Start a new chunk."""
    errors = validate_short_name(short_name)
    if ticket_id:
        errors.extend(validate_ticket_id(ticket_id))

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()
    if ticket_id:
        ticket_id = ticket_id.lower()

    chunks = Chunks(project_dir)

    # Check for duplicates
    duplicates = chunks.find_duplicates(short_name, ticket_id)
    if duplicates and not yes:
        click.echo(f"Chunk with short_name '{short_name}' and ticket_id '{ticket_id}' already exists:")
        for dup in duplicates:
            click.echo(f"  - {dup}")
        if not click.confirm("Create another chunk with the same name?"):
            raise SystemExit(1)

    chunk_path = chunks.create_chunk(ticket_id, short_name)
    # Show path relative to project_dir
    relative_path = chunk_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


@chunk.command("list")
@click.option("--latest", is_flag=True, help="Output only the most recent chunk")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_chunks(latest, project_dir):
    """List all chunks."""
    chunks = Chunks(project_dir)
    chunk_list = chunks.list_chunks()

    if not chunk_list:
        click.echo("No chunks found", err=True)
        raise SystemExit(1)

    if latest:
        latest_chunk = chunks.get_latest_chunk()
        click.echo(f"docs/chunks/{latest_chunk}")
    else:
        for _, chunk_name in chunk_list:
            click.echo(f"docs/chunks/{chunk_name}")


@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find chunks with overlapping code references."""
    chunks = Chunks(project_dir)

    try:
        affected = chunks.find_overlapping_chunks(chunk_id)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    for name in affected:
        click.echo(f"docs/chunks/{name}")


@chunk.command()
@click.argument("chunk_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def complete(chunk_id, project_dir):
    """Validate chunk is ready for completion."""
    chunks = Chunks(project_dir)
    result = chunks.validate_chunk_complete(chunk_id)

    if not result.success:
        for error in result.errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    click.echo(f"Chunk {result.chunk_name} is ready for completion")


if __name__ == "__main__":
    cli()
