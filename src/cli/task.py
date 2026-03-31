"""Task command group.

Commands for managing task directories (cross-repository work).
"""
# Chunk: docs/chunks/cli_modularize - Task CLI commands
# Chunk: docs/chunks/artifact_demote_to_project - Demote CLI command

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


# Chunk: docs/chunks/artifact_demote_to_project - CLI command for demoting external artifacts
@task.command()
@click.argument("artifact", required=False)
@click.option("--auto", is_flag=True, help="Scan and list all single-project artifacts eligible for demotion")
@click.option("--apply", is_flag=True, help="Apply auto-demotion (default is dry-run)")
@click.option("--project", default=None, help="Target project for demotion (required if multiple dependents)")
@click.option("--cwd", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def demote(artifact, auto, apply, project, cwd):
    """Demote external artifacts back to project-local.

    Move a task-level artifact from the external repo into the single project
    that references it, replacing the external.yaml pointer with actual files.

    \b
    Examples:
        ve task demote my_chunk              # Demote a single artifact
        ve task demote --auto                # Dry-run: list demotable artifacts
        ve task demote --auto --apply        # Demote all single-project artifacts
    """
    from task import TaskDemoteError
    from task.demote import demote_artifact as _demote_artifact, scan_demotable_artifacts

    if not artifact and not auto:
        click.echo("Error: provide an ARTIFACT name or use --auto to scan", err=True)
        raise SystemExit(1)

    if artifact and auto:
        click.echo("Error: cannot combine ARTIFACT with --auto", err=True)
        raise SystemExit(1)

    if apply and not auto:
        click.echo("Error: --apply requires --auto", err=True)
        raise SystemExit(1)

    try:
        if artifact:
            # Single artifact demotion
            result = _demote_artifact(
                task_dir=cwd,
                artifact_path=artifact,
                target_project=project,
            )
            click.echo(
                f"Demoted {result['artifact_type']} '{result['demoted_artifact']}' "
                f"to {result['target_project']}"
            )
            if result["external_cleaned"]:
                click.echo("  (external artifact is now orphaned — no remaining dependents)")
        elif auto and not apply:
            # Dry-run: list candidates
            candidates = scan_demotable_artifacts(cwd)
            if not candidates:
                click.echo("No artifacts eligible for demotion")
                return

            click.echo(f"Found {len(candidates)} artifact(s) eligible for demotion:\n")
            for c in candidates:
                click.echo(
                    f"  {c['artifact_type']:15s} {c['artifact_id']:30s} → {c['target_project']}"
                )
                click.echo(f"  {'':15s} reason: {c['reason']}")
            click.echo(f"\nRun with --apply to demote all.")
        elif auto and apply:
            # Apply: demote all candidates
            candidates = scan_demotable_artifacts(cwd)
            if not candidates:
                click.echo("No artifacts eligible for demotion")
                return

            demoted = []
            errors = []
            for c in candidates:
                try:
                    result = _demote_artifact(
                        task_dir=cwd,
                        artifact_path=f"docs/{ARTIFACT_DIR_NAMES[c['artifact_type']]}/{c['artifact_id']}",
                        target_project=c["target_project"],
                    )
                    demoted.append(result)
                    click.echo(
                        f"Demoted {result['artifact_type']} '{result['demoted_artifact']}' "
                        f"→ {result['target_project']}"
                    )
                except TaskDemoteError as e:
                    errors.append((c["artifact_id"], str(e)))
                    click.echo(f"Failed to demote '{c['artifact_id']}': {e}", err=True)

            click.echo(f"\nDemoted {len(demoted)} artifact(s), {len(errors)} error(s)")
    except TaskDemoteError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Mapping from artifact type value to directory name for auto-apply path construction
ARTIFACT_DIR_NAMES = {
    "chunk": "chunks",
    "narrative": "narratives",
    "investigation": "investigations",
    "subsystem": "subsystems",
}
