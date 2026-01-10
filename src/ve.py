"""Vibe Engineer CLI - view layer for chunk management."""
# Chunk: docs/chunks/0001-implement_chunk_start - Core CLI and chunk start
# Chunk: docs/chunks/0002-chunk_list_command - List chunks command
# Chunk: docs/chunks/0003-project_init_command - Project init command
# Chunk: docs/chunks/0004-chunk_overlap_command - Chunk overlap command
# Chunk: docs/chunks/0005-chunk_validate - Chunk validate command
# Chunk: docs/chunks/0006-narrative_cli_commands - Narrative commands
# Chunk: docs/chunks/0009-task_init - Task init command
# Chunk: docs/chunks/0010-chunk_create_task_aware - Task-aware chunk creation
# Chunk: docs/chunks/0013-future_chunk_creation - Future chunks and activate
# Chunk: docs/chunks/0016-subsystem_cli_scaffolding - Subsystem commands
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/0019-subsystem_status_transitions - Status transitions
# Chunk: docs/chunks/0022-subsystem_impact_resolution - Subsystem overlap
# Chunk: docs/chunks/0029-investigation_commands - Investigation commands
# Chunk: docs/chunks/0035-external_resolve - External resolve command

import pathlib

import click

from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from project import Project
from subsystems import Subsystems
from models import SubsystemStatus, InvestigationStatus
from task_init import TaskInit
from task_utils import (
    is_task_directory,
    create_task_chunk,
    list_task_chunks,
    get_current_task_chunk,
    TaskChunkError,
)
from sync import (
    sync_task_directory,
    sync_single_repo,
    find_external_refs,
)
from external_resolve import (
    resolve_task_directory,
    resolve_single_repo as resolve_single_repo_external,
    ResolveResult,
)
from validation import validate_identifier


# Chunk: docs/chunks/0001-implement_chunk_start - Validate short name input
def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


# Chunk: docs/chunks/0001-implement_chunk_start - Validate ticket ID input
def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


@click.group()
def cli():
    """Vibe Engineer"""
    pass


# Chunk: docs/chunks/0003-project_init_command - Project initialization command
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


# Chunk: docs/chunks/0001-implement_chunk_start - Create new chunk command
# Chunk: docs/chunks/0013-future_chunk_creation - Future chunks support
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


# Chunk: docs/chunks/0010-chunk_create_task_aware - Task directory chunk creation
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


# Chunk: docs/chunks/0002-chunk_list_command - List all chunks
# Chunk: docs/chunks/0013-future_chunk_creation - Current chunk filtering
# Chunk: docs/chunks/0033-list_task_aware - Task-aware chunk listing
# Chunk: docs/chunks/0041-artifact_list_ordering - Use ArtifactIndex for causal ordering
@chunk.command("list")
@click.option("--latest", is_flag=True, help="Output only the current IMPLEMENTING chunk")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_chunks(latest, project_dir):
    """List all chunks."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_chunks(latest, project_dir)
        return

    # Single-repo mode
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
        # Get tips for indicator display
        artifact_index = ArtifactIndex(project_dir)
        tips = set(artifact_index.find_tips(ArtifactType.CHUNK))

        for chunk_name in chunk_list:
            frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
            tip_indicator = " *" if chunk_name in tips else ""
            click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/0033-list_task_aware - Task directory chunk listing handler
def _list_task_chunks(latest: bool, task_dir: pathlib.Path):
    """Handle chunk listing in task directory (cross-repo mode)."""
    try:
        if latest:
            current_chunk = get_current_task_chunk(task_dir)
            if current_chunk is None:
                click.echo("No implementing chunk found", err=True)
                raise SystemExit(1)
            click.echo(f"docs/chunks/{current_chunk}")
        else:
            chunk_list = list_task_chunks(task_dir)
            if not chunk_list:
                click.echo("No chunks found", err=True)
                raise SystemExit(1)

            for chunk_info in chunk_list:
                name = chunk_info["name"]
                status = chunk_info["status"]
                dependents = chunk_info["dependents"]

                click.echo(f"docs/chunks/{name} [{status}]")
                if dependents:
                    # Format dependents as: repo (chunk_id), repo (chunk_id)
                    dep_strs = [f"{d['repo']} ({d['chunk']})" for d in dependents]
                    click.echo(f"  dependents: {', '.join(dep_strs)}")
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - List proposed chunks command
@chunk.command("list-proposed")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_proposed_chunks(project_dir):
    """List all proposed chunks that haven't been created yet."""
    chunks = Chunks(project_dir)
    investigations = Investigations(project_dir)
    narratives = Narratives(project_dir)
    subsystems = Subsystems(project_dir)

    proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems)

    if not proposed:
        click.echo("No proposed chunks found", err=True)
        raise SystemExit(0)

    # Group by source
    by_source: dict[str, list[dict]] = {}
    for item in proposed:
        source_key = f"docs/{item['source_type']}s/{item['source_id']}"
        if source_key not in by_source:
            by_source[source_key] = []
        by_source[source_key].append(item)

    # Output grouped by source
    for source_path, items in sorted(by_source.items()):
        click.echo(f"From {source_path}:")
        for item in items:
            # Truncate long prompts for display
            prompt = item["prompt"]
            if len(prompt) > 80:
                prompt = prompt[:77] + "..."
            click.echo(f"  - {prompt}")


# Chunk: docs/chunks/0013-future_chunk_creation - Activate FUTURE chunk
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


# Chunk: docs/chunks/0004-chunk_overlap_command - Find overlapping chunks
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


# Chunk: docs/chunks/0005-chunk_validate - Validate chunk for completion
# Chunk: docs/chunks/0018-bidirectional_refs - Subsystem ref validation
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


# Chunk: docs/chunks/0006-narrative_cli_commands - Narrative command group
@cli.group()
def narrative():
    """Narrative commands"""
    pass


# Chunk: docs/chunks/0006-narrative_cli_commands - Create narrative command
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


# Chunk: docs/chunks/0041-artifact_list_ordering - List narratives command
@narrative.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_narratives(project_dir):
    """List all narratives."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    narratives = Narratives(project_dir)
    artifact_index = ArtifactIndex(project_dir)

    # Get narratives in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.NARRATIVE)
    narrative_list = list(reversed(ordered))

    if not narrative_list:
        click.echo("No narratives found", err=True)
        raise SystemExit(1)

    # Get tips for indicator display
    tips = set(artifact_index.find_tips(ArtifactType.NARRATIVE))

    for narrative_name in narrative_list:
        frontmatter = narratives.parse_narrative_frontmatter(narrative_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        tip_indicator = " *" if narrative_name in tips else ""
        click.echo(f"docs/narratives/{narrative_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/0009-task_init - Task command group
@cli.group()
def task():
    """Task directory commands."""
    pass


# Chunk: docs/chunks/0009-task_init - Initialize task directory
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


# Chunk: docs/chunks/0016-subsystem_cli_scaffolding - Subsystem command group
@cli.group()
def subsystem():
    """Subsystem commands"""
    pass


# Chunk: docs/chunks/0016-subsystem_cli_scaffolding - List subsystems command
# Chunk: docs/chunks/0041-artifact_list_ordering - Use ArtifactIndex for causal ordering
@subsystem.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_subsystems(project_dir):
    """List all subsystems."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    subsystems = Subsystems(project_dir)
    artifact_index = ArtifactIndex(project_dir)

    # Get subsystems in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.SUBSYSTEM)
    subsystem_list = list(reversed(ordered))

    if not subsystem_list:
        click.echo("No subsystems found", err=True)
        raise SystemExit(1)

    # Get tips for indicator display
    tips = set(artifact_index.find_tips(ArtifactType.SUBSYSTEM))

    for subsystem_name in subsystem_list:
        frontmatter = subsystems.parse_subsystem_frontmatter(subsystem_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        tip_indicator = " *" if subsystem_name in tips else ""
        click.echo(f"docs/subsystems/{subsystem_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/0016-subsystem_cli_scaffolding - Create subsystem command
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


# Chunk: docs/chunks/0018-bidirectional_refs - Validate subsystem command
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


# Chunk: docs/chunks/0019-subsystem_status_transitions - Status command
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


# Chunk: docs/chunks/0022-subsystem_impact_resolution - Subsystem overlap command
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


# Chunk: docs/chunks/0029-investigation_commands - Investigation command group
@cli.group()
def investigation():
    """Investigation commands"""
    pass


# Chunk: docs/chunks/0029-investigation_commands - Create investigation command
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


# Chunk: docs/chunks/0029-investigation_commands - List investigations command
# Chunk: docs/chunks/0041-artifact_list_ordering - Use ArtifactIndex for causal ordering
@investigation.command("list")
@click.option("--state", type=str, default=None, help="Filter by investigation state")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_investigations(state, project_dir):
    """List all investigations."""
    from artifact_ordering import ArtifactIndex, ArtifactType

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
    artifact_index = ArtifactIndex(project_dir)

    # Get investigations in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.INVESTIGATION)
    investigation_list = list(reversed(ordered))

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

    # Get tips for indicator display
    tips = set(artifact_index.find_tips(ArtifactType.INVESTIGATION))

    for inv_name in investigation_list:
        frontmatter = investigations.parse_investigation_frontmatter(inv_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        tip_indicator = " *" if inv_name in tips else ""
        click.echo(f"docs/investigations/{inv_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/0034-ve_sync_command - Sync external references
@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("--project", "projects", multiple=True, help="Sync only specified project(s) (task directory only)")
@click.option("--chunk", "chunks", multiple=True, help="Sync only specified chunk(s)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def sync(dry_run, projects, chunks, project_dir):
    """Sync external chunk references to current repository state."""
    # Convert filter tuples to lists (or None if empty)
    project_filter = list(projects) if projects else None
    chunk_filter = list(chunks) if chunks else None

    # Check if we're in a task directory
    if is_task_directory(project_dir):
        _sync_task_directory(project_dir, dry_run, project_filter, chunk_filter)
    else:
        # Single repo mode
        if project_filter:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _sync_single_repo(project_dir, dry_run, chunk_filter)


def _sync_task_directory(
    task_dir: pathlib.Path,
    dry_run: bool,
    project_filter: list[str] | None,
    chunk_filter: list[str] | None,
):
    """Handle sync in task directory mode."""
    try:
        results = sync_task_directory(
            task_dir,
            dry_run=dry_run,
            project_filter=project_filter,
            chunk_filter=chunk_filter,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not results:
        click.echo("No external references found")
        return

    _display_sync_results(results, dry_run)


def _sync_single_repo(
    repo_path: pathlib.Path,
    dry_run: bool,
    chunk_filter: list[str] | None,
):
    """Handle sync in single repo mode."""
    # Check if there are any external refs
    external_refs = find_external_refs(repo_path)
    if not external_refs:
        click.echo("No external references found")
        return

    results = sync_single_repo(
        repo_path,
        dry_run=dry_run,
        chunk_filter=chunk_filter,
    )

    _display_sync_results(results, dry_run)


def _display_sync_results(results: list, dry_run: bool):
    """Display sync results to the user."""
    updated_count = 0
    error_count = 0
    prefix = "[dry-run] " if dry_run else ""

    for result in results:
        if result.error:
            click.echo(f"{prefix}Error syncing {result.chunk_id}: {result.error}", err=True)
            error_count += 1
        elif result.updated:
            old_abbrev = result.old_sha[:7] if result.old_sha else "(none)"
            new_abbrev = result.new_sha[:7] if result.new_sha else "(none)"
            verb = "Would update" if dry_run else "Updated"
            click.echo(f"{prefix}{result.chunk_id}: {old_abbrev} -> {new_abbrev} ({verb})")
            updated_count += 1
        else:
            old_abbrev = result.old_sha[:7] if result.old_sha else "(none)"
            click.echo(f"{prefix}{result.chunk_id}: {old_abbrev} (already current)")

    # Summary
    total = len(results)
    verb = "Would update" if dry_run else "Updated"
    click.echo(f"\n{prefix}{verb} {updated_count} of {total} external reference(s)")

    if error_count > 0:
        click.echo(f"{error_count} error(s) occurred", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/0035-external_resolve - External command group
@cli.group()
def external():
    """External chunk reference commands."""
    pass


# Chunk: docs/chunks/0035-external_resolve - Resolve external chunk command
@external.command()
@click.argument("local_chunk_id")
@click.option("--at-pinned", is_flag=True, help="Show content at pinned SHA instead of current HEAD")
@click.option("--goal-only", is_flag=True, help="Show only GOAL.md content")
@click.option("--plan-only", is_flag=True, help="Show only PLAN.md content")
@click.option("--project", type=str, default=None, help="Specify project for disambiguation (task directory only)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def resolve(local_chunk_id, at_pinned, goal_only, plan_only, project, project_dir):
    """Display external chunk content.

    Resolves an external chunk reference and displays its GOAL.md and PLAN.md content.
    Works in both task directory mode (using local worktrees) and single repo mode
    (using the repo cache).
    """
    # Validate mutually exclusive options
    if goal_only and plan_only:
        click.echo("Error: --goal-only and --plan-only are mutually exclusive", err=True)
        raise SystemExit(1)

    # Determine mode and resolve
    if is_task_directory(project_dir):
        _resolve_external_task_directory(
            project_dir, local_chunk_id, at_pinned, goal_only, plan_only, project
        )
    else:
        if project:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _resolve_external_single_repo(
            project_dir, local_chunk_id, at_pinned, goal_only, plan_only
        )


def _resolve_external_task_directory(
    task_dir: pathlib.Path,
    local_chunk_id: str,
    at_pinned: bool,
    goal_only: bool,
    plan_only: bool,
    project_filter: str | None,
):
    """Handle resolve in task directory mode."""
    try:
        result = resolve_task_directory(
            task_dir,
            local_chunk_id,
            at_pinned=at_pinned,
            project_filter=project_filter,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, goal_only, plan_only)


def _resolve_external_single_repo(
    repo_path: pathlib.Path,
    local_chunk_id: str,
    at_pinned: bool,
    goal_only: bool,
    plan_only: bool,
):
    """Handle resolve in single repo mode."""
    try:
        result = resolve_single_repo_external(
            repo_path,
            local_chunk_id,
            at_pinned=at_pinned,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, goal_only, plan_only)


def _display_resolve_result(result: ResolveResult, goal_only: bool, plan_only: bool):
    """Display the resolve result to the user."""
    # Header with metadata
    click.echo("External Chunk Reference")
    click.echo("========================")
    click.echo(f"Repository: {result.repo}")
    click.echo(f"Chunk: {result.external_chunk_id}")
    click.echo(f"Track: {result.track}")
    click.echo(f"SHA: {result.resolved_sha}")
    click.echo("")

    # Content
    if not plan_only:
        click.echo("--- GOAL.md ---")
        if result.goal_content:
            click.echo(result.goal_content)
        else:
            click.echo("(not found)")

    if not goal_only:
        if not plan_only:
            click.echo("")
        click.echo("--- PLAN.md ---")
        if result.plan_content:
            click.echo(result.plan_content)
        else:
            click.echo("(not found)")


if __name__ == "__main__":
    cli()
