"""Artifact command group.

Commands for artifact management operations.
"""
# Chunk: docs/chunks/cli_modularize - Artifact CLI commands
# Chunk: docs/chunks/artifact_promote - CLI command ve artifact promote <path> [--name]
# Chunk: docs/chunks/copy_as_external - ve artifact copy-external command
# Chunk: docs/chunks/remove_external_ref - ve artifact remove-external command

import pathlib

import click

from task import (
    promote_artifact,
    TaskPromoteError,
    copy_artifact_as_external,
    TaskCopyExternalError,
)


# Chunk: docs/chunks/artifact_promote - CLI command group for artifact management commands
@click.group()
def artifact():
    """Artifact management commands."""
    pass


@artifact.command()
@click.argument("artifact_path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def promote(artifact_path, new_name, project_dir):
    """Promote a local artifact to the task-level external repository.

    Moves an artifact (chunk, investigation, narrative, or subsystem) from a
    project's docs/ directory to the external artifact repository, leaving
    behind an external reference.

    ARTIFACT_PATH is the path to the local artifact directory to promote.
    """
    # Resolve artifact_path relative to project_dir if needed
    if not artifact_path.is_absolute():
        artifact_path = project_dir / artifact_path

    try:
        result = promote_artifact(artifact_path, new_name=new_name)
    except TaskPromoteError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_artifact_path"]
    external_yaml_path = result["external_yaml_path"]

    click.echo(f"Promoted artifact to external repo: {external_path}")
    click.echo(f"Created external reference: {external_yaml_path}")


# Chunk: docs/chunks/accept_full_artifact_paths - CLI copy-external command using flexible path normalization
@artifact.command("copy-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--name", "new_name", type=str, help="New name for artifact in destination")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def copy_external(artifact_path, target_project, new_name, cwd):
    """Copy an external artifact as a reference in a target project.

    Creates an external.yaml in the target project that references an artifact
    already present in the external artifact repository.

    ARTIFACT_PATH accepts flexible formats: "docs/chunks/my_chunk", "chunks/my_chunk",
    or just "my_chunk" (if unambiguous).

    TARGET_PROJECT accepts flexible formats: "acme/proj" or just "proj" (if unambiguous).
    """
    try:
        result = copy_artifact_as_external(
            task_dir=cwd,
            artifact_path=artifact_path,
            target_project=target_project,
            new_name=new_name,
        )
    except TaskCopyExternalError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created path
    external_yaml_path = result["external_yaml_path"]
    click.echo(f"Created external reference: {external_yaml_path}")


@artifact.command("remove-external")
@click.argument("artifact_path")
@click.argument("target_project")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def remove_external(artifact_path, target_project, cwd):
    """Remove an external artifact reference from a target project.

    Inverse of copy-external. Removes the external.yaml from the target project
    and updates the artifact's dependents list in the external repo.

    ARTIFACT_PATH accepts flexible formats: "docs/chunks/my_chunk", "chunks/my_chunk",
    or just "my_chunk" (if unambiguous).

    TARGET_PROJECT accepts flexible formats: "acme/proj" or just "proj" (if unambiguous).
    """
    from task import remove_artifact_from_external, TaskRemoveExternalError

    try:
        result = remove_artifact_from_external(
            task_dir=cwd,
            artifact_path=artifact_path,
            target_project=target_project,
        )
    except TaskRemoveExternalError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report what was done
    if result["removed"]:
        click.echo(f"Removed external reference for '{artifact_path}' from '{target_project}'")
        if result["directory_cleaned"]:
            click.echo("  (empty directory cleaned up)")
        if result["dependent_removed"]:
            click.echo("  (updated dependents in source artifact)")

        # Warn if artifact is now orphaned
        if result["orphaned"]:
            click.echo(
                "\nWarning: This artifact has no remaining project links. "
                "Consider removing it from the external repository if it's no longer needed."
            )
    else:
        click.echo(f"No external reference found for '{artifact_path}' in '{target_project}' (already removed)")
