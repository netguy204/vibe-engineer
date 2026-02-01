"""Top-level CLI commands: init and validate.

These are direct commands on the root cli group, not part of a command group.
"""
# Chunk: docs/chunks/cli_modularize - Top-level CLI commands
# Chunk: docs/chunks/project_init_command - CLI init command implementation
# Chunk: docs/chunks/integrity_validate - Project-wide referential integrity validation
# Chunk: docs/chunks/validate_external_chunks - External chunk skip reporting in verbose output

import pathlib

import click

from project import Project


@click.command()
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


@click.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed statistics")
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def validate(project_dir, verbose, strict):
    """Validate referential integrity across all artifacts.

    Checks that all cross-artifact references are valid:
    - Chunk references to narratives, investigations, subsystems, friction entries
    - Code backreferences (# Chunk: and # Subsystem: comments)
    - Proposed chunks in narratives, investigations, and friction log

    Returns non-zero exit code if errors are found.
    """
    from integrity import IntegrityValidator

    validator = IntegrityValidator(project_dir)
    result = validator.validate()

    # Show statistics if verbose
    if verbose:
        click.echo("Scanning artifacts...")
        click.echo(f"  Chunks: {result.chunks_scanned}")
        if result.external_chunks_skipped > 0:
            click.echo(f"  External chunks skipped: {result.external_chunks_skipped}")
        click.echo(f"  Narratives: {result.narratives_scanned}")
        click.echo(f"  Investigations: {result.investigations_scanned}")
        click.echo(f"  Subsystems: {result.subsystems_scanned}")
        click.echo("Scanning code backreferences...")
        click.echo(f"  Files scanned: {result.files_scanned}")
        click.echo(f"  Chunk backrefs: {result.chunk_backrefs_found}")
        click.echo(f"  Subsystem backrefs: {result.subsystem_backrefs_found}")
        click.echo("")

    # Report errors
    for error in result.errors:
        click.echo(f"Error: [{error.link_type}] {error.source} -> {error.target}", err=True)
        click.echo(f"       {error.message}", err=True)

    # Report warnings
    for warning in result.warnings:
        prefix = "Error" if strict else "Warning"
        click.echo(f"{prefix}: [{warning.link_type}] {warning.source} -> {warning.target}", err=True)
        click.echo(f"       {warning.message}", err=True)

    # Summary
    error_count = len(result.errors)
    warning_count = len(result.warnings)

    if strict:
        error_count += warning_count
        warning_count = 0

    if error_count > 0:
        click.echo(f"\nValidation failed: {error_count} error(s) found", err=True)
        raise SystemExit(1)

    if warning_count > 0:
        click.echo(f"Validation passed with {warning_count} warning(s)")
    else:
        click.echo("Validation passed")
