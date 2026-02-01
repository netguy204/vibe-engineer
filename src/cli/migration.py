"""Migration command group.

Commands for managing repository migrations.
"""
# Chunk: docs/chunks/cli_modularize - Migration CLI commands

import pathlib

import click


@click.group()
def migration():
    """Commands for managing repository migrations."""
    pass


@migration.command("create")
@click.argument("migration_type", default="chunks_to_subsystems")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_migration(migration_type, project_dir):
    """Create a new migration."""
    from migrations import Migrations

    migrations = Migrations(project_dir)

    try:
        migration_dir = migrations.create_migration(migration_type)

        click.echo(f"Created migration: {migration_type}")
        click.echo(f"  Location: {migration_dir}")

        # Show migration-type-specific information
        if migration_type == "managed_claude_md":
            click.echo()
            click.echo("Run /migrate-managed-claude-md to begin the migration workflow.")
        else:
            source_type = migrations.detect_source_type()
            chunk_count = migrations.count_chunks()
            click.echo(f"  Source type: {source_type.value}")
            if source_type.value == "chunks":
                click.echo(f"  Chunks found: {chunk_count}")
            click.echo()
            click.echo("Run /migrate-to-subsystems to begin the migration workflow.")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@migration.command("status")
@click.argument("migration_type", default="chunks_to_subsystems")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def migration_status(migration_type, project_dir):
    """Show migration status."""
    from migrations import Migrations

    migrations = Migrations(project_dir)

    if not migrations.migration_exists(migration_type):
        click.echo(f"No migration found: {migration_type}")
        click.echo("Run 've migration create' to start a new migration.")
        raise SystemExit(1)

    frontmatter = migrations.parse_migration_frontmatter(migration_type)
    if frontmatter is None:
        click.echo("Error: Could not parse migration frontmatter", err=True)
        raise SystemExit(1)

    click.echo(f"Migration: {migration_type}")
    click.echo(f"  Status: {frontmatter.status.value}")
    if frontmatter.source_type:
        click.echo(f"  Source type: {frontmatter.source_type.value}")
    click.echo(f"  Current phase: {frontmatter.current_phase}")
    click.echo(f"  Phases completed: {frontmatter.phases_completed}")
    click.echo(f"  Started: {frontmatter.started}")
    click.echo()
    if frontmatter.chunks_analyzed > 0:
        click.echo(f"  Chunks analyzed: {frontmatter.chunks_analyzed}")
    click.echo(f"  Subsystems proposed: {frontmatter.subsystems_proposed}")
    click.echo(f"  Subsystems approved: {frontmatter.subsystems_approved}")
    click.echo(f"  Questions pending: {frontmatter.questions_pending}")
    click.echo(f"  Questions resolved: {frontmatter.questions_resolved}")

    if frontmatter.status.value == "PAUSED":
        click.echo()
        click.echo(f"  Pause reason: {frontmatter.pause_reason}")
        click.echo(f"  Resume instructions: {frontmatter.resume_instructions}")


@migration.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_migrations(project_dir):
    """List all migrations."""
    from migrations import Migrations

    migrations = Migrations(project_dir)
    migration_dirs = migrations.enumerate_migrations()

    if not migration_dirs:
        click.echo("No migrations found.")
        return

    click.echo("Migrations:")
    for migration_type in sorted(migration_dirs):
        frontmatter = migrations.parse_migration_frontmatter(migration_type)
        if frontmatter:
            click.echo(f"  {migration_type}: {frontmatter.status.value}")
        else:
            click.echo(f"  {migration_type}: (invalid frontmatter)")


@migration.command("pause")
@click.argument("migration_type", default="chunks_to_subsystems")
@click.option("--reason", help="Reason for pausing")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def pause_migration(migration_type, reason, project_dir):
    """Pause a migration."""
    from migrations import Migrations, MigrationStatus

    migrations = Migrations(project_dir)

    try:
        old_status, new_status = migrations.update_status(
            migration_type,
            MigrationStatus.PAUSED,
            pause_reason=reason or "Paused by operator",
            resume_instructions="Run /migrate-to-subsystems to resume",
        )
        click.echo(f"Migration paused: {old_status.value} → {new_status.value}")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@migration.command("abandon")
@click.argument("migration_type", default="chunks_to_subsystems")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def abandon_migration(migration_type, project_dir):
    """Abandon a migration."""
    from migrations import Migrations, MigrationStatus

    migrations = Migrations(project_dir)

    try:
        old_status, new_status = migrations.update_status(
            migration_type,
            MigrationStatus.ABANDONED,
        )
        click.echo(f"Migration abandoned: {old_status.value} → {new_status.value}")
        click.echo("You can restart with 've migration create' after deleting the migration directory.")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
