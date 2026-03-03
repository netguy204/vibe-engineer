"""Task command group.

Commands for managing task directories (cross-repository work).
"""
# Chunk: docs/chunks/cli_modularize - Task CLI commands

import pathlib

import click

from task_init import TaskInit


@click.group()
def task():
    """Manage task directories - cross-repository work coordination.

    Task directories enable working across multiple repositories with
    shared artifacts stored in an external repository.
    """
    pass


@task.command()
@click.option(
    "--external",
    required=True,
    type=click.Path(),
    help="External chunk repository directory",
)
@click.option(
    "--project",
    "projects",
    required=True,
    multiple=True,
    type=click.Path(),
    help="Participating repository directory",
)
def init(external, projects):
    """Initialize a task directory for cross-repository work."""
    cwd = pathlib.Path.cwd()
    task_init = TaskInit(cwd=cwd, external=external, projects=list(projects))

    errors = task_init.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    result = task_init.execute()
    click.echo(f"Created {result.config_path.name}")
    click.echo(f"  External: {result.external_repo}")
    click.echo(f"  Projects: {', '.join(result.projects)}")
