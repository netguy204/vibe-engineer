"""Vibe Engineer CLI - modular command structure.

This package organizes the CLI into logical command groups for maintainability.
Each submodule contains a command group that is registered with the main cli.
"""
# Chunk: docs/chunks/cli_modularize - Main CLI assembly point

import click


@click.group()
def cli():
    """Vibe Engineer"""
    pass


# Import and register command groups
# Each module defines its command group which gets added to the main cli

from cli.init_cmd import init, validate
from cli.chunk import chunk
from cli.narrative import narrative
from cli.task import task
from cli.subsystem import subsystem
from cli.investigation import investigation
from cli.external import external
from cli.artifact import artifact
from cli.orch import orch
from cli.friction import friction
from cli.migration import migration
from cli.reviewer import reviewer

# Add top-level commands
cli.add_command(init)
cli.add_command(validate)

# Add command groups
cli.add_command(chunk)
cli.add_command(narrative)
cli.add_command(task)
cli.add_command(subsystem)
cli.add_command(investigation)
cli.add_command(external)
cli.add_command(artifact)
cli.add_command(orch)
cli.add_command(friction)
cli.add_command(migration)
cli.add_command(reviewer)
