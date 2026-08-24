"""Vibe Engineer CLI - modular command structure.

This package organizes the CLI into logical command groups for maintainability.
Each submodule contains a command group that is registered with the main cli.
"""
# Chunk: docs/chunks/cli_modularize - Main CLI assembly point
# Chunk: docs/chunks/cli_dotenv_loading - Wires dotenv loading into CLI startup

import click

from cli.dotenv_loader import load_dotenv_from_project_root


# Chunk: docs/chunks/plugin_session_hooks - ve --version sources the installed
# package version so the plugin SessionStart hook can check compatibility (DEC-011)
@click.group()
@click.version_option(package_name="vibe-engineer", prog_name="ve")
def cli():
    """Vibe Engineer"""
    load_dotenv_from_project_root()


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
from cli.board import board
from cli.entity import entity
from cli.wiki import wiki
from cli.plugin import plugin
# Chunk: docs/chunks/federation_workspace_manifest - `ve workspace` manifest commands
from cli.workspace import workspace
# Chunk: docs/chunks/federation_template_pointers - `ve package scaffold` pointer-only members
from cli.package import package
# Chunk: docs/chunks/entity_config_toml - Operator-level `~/.ve-config.toml` and `ve config show`
from cli.config import config
# Chunk: docs/chunks/hooks_lifecycle_fragments - `ve hooks show|list` for docs/hooks/ fragments
from cli.hooks import hooks
# Chunk: docs/chunks/crossref_absence_evidence - `ve exists` and `ve deletion`
from cli.exists_cmd import exists
from cli.deletion import deletion
# Chunk: docs/chunks/crossref_refactor_move - `ve refactor move` evidence-backed rename propagation
from cli.refactor import refactor
# Chunk: docs/chunks/plugin_local_skills - `ve skills` opt-in local reification
from cli.skills import skills

# Add top-level commands
cli.add_command(init)
cli.add_command(validate)
cli.add_command(exists)

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
cli.add_command(board)
cli.add_command(entity)
cli.add_command(wiki)
cli.add_command(plugin)
cli.add_command(workspace)
cli.add_command(package)
cli.add_command(config)
cli.add_command(hooks)
cli.add_command(deletion)
cli.add_command(refactor)
cli.add_command(skills)

# Chunk: docs/chunks/federation_tree_discovery - Resolve --project-dir to the nearest enclosing VE tree
# KEEP THIS LAST: the installer walks the command tree as it exists when called,
# so a group registered after this line would silently miss tree discovery.
# New cli.add_command(...) calls belong above.
from cli.tree_discovery import install_tree_discovery

install_tree_discovery(cli)
