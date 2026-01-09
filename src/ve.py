"""Vibe Engineer CLI - view layer for chunk management."""

import pathlib

import click

from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from project import Project
from subsystems import Subsystems
from models import SubsystemStatus, InvestigationStatus
from task_init import TaskInit
from task_utils import is_task_directory, create_task_chunk, TaskChunkError
from validation import validate_identifier


def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


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
@click.option("--future", is_flag=True, help="Create chunk with FUTURE status instead of IMPLEMENTING")
def start(short_name, ticket_id, project_dir, yes, future):
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

    # Determine status based on --future flag
    status = "FUTURE" if future else "IMPLEMENTING"

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _start_task_chunk(project_dir, short_name, ticket_id, status)
        return

    # Single-repo mode
    chunks = Chunks(project_dir)

    # Check for duplicates
    duplicates = chunks.find_duplicates(short_name, ticket_id)
    if duplicates and not yes:
        click.echo(f"Chunk with short_name '{short_name}' and ticket_id '{ticket_id}' already exists:")
        for dup in duplicates:
            click.echo(f"  - {dup}")
        if not click.confirm("Create another chunk with the same name?"):
            raise SystemExit(1)

    chunk_path = chunks.create_chunk(ticket_id, short_name, status=status)
    # Show path relative to project_dir
    relative_path = chunk_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


def _start_task_chunk(
    task_dir: pathlib.Path, short_name: str, ticket_id: str | None, status: str = "IMPLEMENTING"
):
    """Handle chunk creation in task directory (cross-repo mode)."""
    try:
        result = create_task_chunk(task_dir, short_name, ticket_id, status=status)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_chunk_path"]
    click.echo(f"Created chunk in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the chunk directory, not the yaml file
        chunk_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {chunk_dir.relative_to(task_dir)}/")


@chunk.command("list")
@click.option("--latest", is_flag=True, help="Output only the current IMPLEMENTING chunk")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_chunks(latest, project_dir):
    """List all chunks."""
    chunks = Chunks(project_dir)
    chunk_list = chunks.list_chunks()

    if not chunk_list:
        click.echo("No chunks found", err=True)
        raise SystemExit(1)

    if latest:
        current_chunk = chunks.get_current_chunk()
        if current_chunk is None:
            click.echo("No implementing chunk found", err=True)
            raise SystemExit(1)
        click.echo(f"docs/chunks/{current_chunk}")
    else:
        for _, chunk_name in chunk_list:
            frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
            status = frontmatter.get("status", "UNKNOWN") if frontmatter else "UNKNOWN"
            click.echo(f"docs/chunks/{chunk_name} [{status}]")


@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def activate(chunk_id, project_dir):
    """Activate a FUTURE chunk by changing its status to IMPLEMENTING."""
    chunks = Chunks(project_dir)

    try:
        activated = chunks.activate_chunk(chunk_id)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Activated docs/chunks/{activated}")


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
def validate(chunk_id, project_dir):
    """Validate chunk is ready for completion."""
    chunks = Chunks(project_dir)
    result = chunks.validate_chunk_complete(chunk_id)

    if not result.success:
        for error in result.errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Display warnings (but still succeed)
    for warning in result.warnings:
        click.echo(warning, err=True)

    click.echo(f"Chunk {result.chunk_name} is ready for completion")


@cli.group()
def narrative():
    """Narrative commands"""
    pass


@narrative.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_narrative(short_name, project_dir):
    """Create a new narrative."""
    errors = validate_short_name(short_name)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()

    narratives = Narratives(project_dir)
    narrative_path = narratives.create_narrative(short_name)

    # Show path relative to project_dir
    relative_path = narrative_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


@cli.group()
def task():
    """Task directory commands."""
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


@cli.group()
def subsystem():
    """Subsystem commands"""
    pass


@subsystem.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_subsystems(project_dir):
    """List all subsystems."""
    subsystems = Subsystems(project_dir)
    subsystem_list = subsystems.enumerate_subsystems()

    if not subsystem_list:
        click.echo("No subsystems found", err=True)
        raise SystemExit(1)

    # Sort subsystems (ascending order by directory name)
    sorted_subsystems = sorted(subsystem_list)

    for subsystem_name in sorted_subsystems:
        frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        click.echo(f"docs/subsystems/{subsystem_name} [{status}]")


@subsystem.command()
@click.argument("shortname")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def discover(shortname, project_dir):
    """Create a new subsystem."""
    errors = validate_short_name(shortname)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    shortname = shortname.lower()

    subsystems = Subsystems(project_dir)

    # Check for duplicates
    existing = subsystems.find_by_shortname(shortname)
    if existing:
        click.echo(f"Error: Subsystem '{shortname}' already exists at docs/subsystems/{existing}", err=True)
        raise SystemExit(1)

    # Create the subsystem
    subsystem_path = subsystems.create_subsystem(shortname)

    # Show path relative to project_dir
    relative_path = subsystem_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


@subsystem.command()
@click.argument("subsystem_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def validate(subsystem_id, project_dir):
    """Validate subsystem frontmatter and chunk references."""
    subsystems = Subsystems(project_dir)

    # Check if subsystem exists
    frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_id)
    if frontmatter is None:
        click.echo(f"Error: Subsystem '{subsystem_id}' not found or has invalid frontmatter", err=True)
        raise SystemExit(1)

    # Validate chunk references
    errors = subsystems.validate_chunk_refs(subsystem_id)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    click.echo(f"Subsystem {subsystem_id} validation passed")


@subsystem.command()
@click.argument("subsystem_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(subsystem_id, new_status, project_dir):
    """Show or update subsystem status."""
    subsystems = Subsystems(project_dir)

    # Resolve subsystem_id (could be shortname or full ID)
    resolved_id = subsystem_id
    if not subsystems.is_subsystem_dir(subsystem_id):
        # Try to resolve as shortname
        found = subsystems.find_by_shortname(subsystem_id)
        if found:
            resolved_id = found
        # If not found, keep the original ID for error message

    # Extract shortname for display
    if "-" in resolved_id:
        shortname = resolved_id.split("-", 1)[1]
    else:
        shortname = resolved_id

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = subsystems.get_status(resolved_id)
            click.echo(f"{shortname}: {current_status.value}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid SubsystemStatus value
    try:
        new_status_enum = SubsystemStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in SubsystemStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = subsystems.update_status(resolved_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@subsystem.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find subsystems with code references overlapping a chunk's changes."""
    subsystems = Subsystems(project_dir)
    chunks = Chunks(project_dir)

    try:
        overlapping = subsystems.find_overlapping_subsystems(chunk_id, chunks)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    for item in overlapping:
        click.echo(f"docs/subsystems/{item['subsystem_id']} [{item['status']}]")


@cli.group()
def investigation():
    """Investigation commands"""
    pass


@investigation.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_investigation(short_name, project_dir):
    """Create a new investigation."""
    errors = validate_short_name(short_name)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()

    investigations = Investigations(project_dir)
    investigation_path = investigations.create_investigation(short_name)

    # Show path relative to project_dir
    relative_path = investigation_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


@investigation.command("list")
@click.option("--state", type=str, default=None, help="Filter by investigation state")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_investigations(state, project_dir):
    """List all investigations."""
    # Validate state filter if provided
    if state is not None:
        try:
            state_filter = InvestigationStatus(state)
        except ValueError:
            valid_states = ", ".join(s.value for s in InvestigationStatus)
            click.echo(
                f"Error: Invalid state '{state}'. Valid states: {valid_states}",
                err=True
            )
            raise SystemExit(1)
    else:
        state_filter = None

    investigations = Investigations(project_dir)
    investigation_list = investigations.enumerate_investigations()

    # Filter by state if requested
    if state_filter is not None:
        filtered_list = []
        for inv_name in investigation_list:
            frontmatter = investigations.parse_investigation_frontmatter(inv_name)
            if frontmatter and frontmatter.status == state_filter:
                filtered_list.append(inv_name)
        investigation_list = filtered_list

    if not investigation_list:
        click.echo("No investigations found", err=True)
        raise SystemExit(1)

    # Sort investigations (ascending order by directory name)
    sorted_investigations = sorted(investigation_list)

    for inv_name in sorted_investigations:
        frontmatter = investigations.parse_investigation_frontmatter(inv_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        click.echo(f"docs/investigations/{inv_name} [{status}]")


if __name__ == "__main__":
    cli()
