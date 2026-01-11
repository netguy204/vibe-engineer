"""Vibe Engineer CLI - view layer for chunk management."""
# Chunk: docs/chunks/implement_chunk_start - Core CLI and chunk start
# Chunk: docs/chunks/chunk_list_command - List chunks command
# Chunk: docs/chunks/project_init_command - Project init command
# Chunk: docs/chunks/chunk_overlap_command - Chunk overlap command
# Chunk: docs/chunks/chunk_validate - Chunk validate command
# Chunk: docs/chunks/narrative_cli_commands - Narrative commands
# Chunk: docs/chunks/task_init - Task init command
# Chunk: docs/chunks/chunk_create_task_aware - Task-aware chunk creation
# Chunk: docs/chunks/future_chunk_creation - Future chunks and activate
# Chunk: docs/chunks/subsystem_cli_scaffolding - Subsystem commands
# Chunk: docs/chunks/bidirectional_refs - Subsystem validation
# Chunk: docs/chunks/subsystem_status_transitions - Status transitions
# Chunk: docs/chunks/subsystem_impact_resolution - Subsystem overlap
# Chunk: docs/chunks/investigation_commands - Investigation commands
# Chunk: docs/chunks/external_resolve - External resolve command

import pathlib

import click

from chunks import Chunks
from investigations import Investigations
from narratives import Narratives
from project import Project
from subsystems import Subsystems
from models import SubsystemStatus, InvestigationStatus, ChunkStatus, NarrativeStatus, ArtifactType
from task_init import TaskInit
from task_utils import (
    is_task_directory,
    create_task_chunk,
    list_task_chunks,
    get_current_task_chunk,
    TaskChunkError,
    create_task_narrative,
    list_task_narratives,
    TaskNarrativeError,
    create_task_subsystem,
    list_task_subsystems,
    TaskSubsystemError,
)
from sync import (
    sync_task_directory,
    sync_single_repo,
    find_external_refs,
)
from external_resolve import (
    resolve_artifact_task_directory,
    resolve_artifact_single_repo,
    resolve_task_directory,
    resolve_single_repo as resolve_single_repo_external,
    ResolveResult,
)
from external_refs import ARTIFACT_MAIN_FILE, detect_artifact_type_from_path
from validation import validate_identifier


# Chunk: docs/chunks/implement_chunk_start - Validate short name input
def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


# Chunk: docs/chunks/implement_chunk_start - Validate ticket ID input
def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


@click.group()
def cli():
    """Vibe Engineer"""
    pass


# Chunk: docs/chunks/project_init_command - Project initialization command
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


# Chunk: docs/chunks/implement_chunk_start - Create new chunk command
# Chunk: docs/chunks/future_chunk_creation - Future chunks support
# Chunk: docs/chunks/rename_chunk_start_to_create - Rename start to create
@chunk.command("create")
@click.argument("short_name")
@click.argument("ticket_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--future", is_flag=True, help="Create chunk with FUTURE status instead of IMPLEMENTING")
def create(short_name, ticket_id, project_dir, yes, future):
    """Create a new chunk."""
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


# Chunk: docs/chunks/rename_chunk_start_to_create - Backward compatibility alias
chunk.add_command(create, name="start")


# Chunk: docs/chunks/chunk_create_task_aware - Task directory chunk creation
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


# Chunk: docs/chunks/chunk_list_command - List all chunks
# Chunk: docs/chunks/future_chunk_creation - Current chunk filtering
# Chunk: docs/chunks/list_task_aware - Task-aware chunk listing
# Chunk: docs/chunks/artifact_list_ordering - Use ArtifactIndex for causal ordering
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


# Chunk: docs/chunks/list_task_aware - Task directory chunk listing handler
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
                    # Format dependents as: repo (artifact_id), repo (artifact_id)
                    dep_strs = [f"{d['repo']} ({d['artifact_id']})" for d in dependents]
                    click.echo(f"  dependents: {', '.join(dep_strs)}")
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/proposed_chunks_frontmatter - List proposed chunks command
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


# Chunk: docs/chunks/future_chunk_creation - Activate FUTURE chunk
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


# Chunk: docs/chunks/valid_transitions - Status command
@chunk.command()
@click.argument("chunk_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(chunk_id, new_status, project_dir):
    """Show or update chunk status."""
    from models import extract_short_name

    chunks = Chunks(project_dir)

    # Resolve chunk_id
    resolved_id = chunks.resolve_chunk_id(chunk_id)
    if resolved_id is None:
        click.echo(f"Error: Chunk '{chunk_id}' not found", err=True)
        raise SystemExit(1)

    # Extract shortname for display
    shortname = extract_short_name(resolved_id)

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = chunks.get_status(resolved_id)
            click.echo(f"{shortname}: {current_status.value}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid ChunkStatus value
    try:
        new_status_enum = ChunkStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in ChunkStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = chunks.update_status(resolved_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/chunk_overlap_command - Find overlapping chunks
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


# Chunk: docs/chunks/chunk_validate - Validate chunk for completion
# Chunk: docs/chunks/bidirectional_refs - Subsystem ref validation
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


# Chunk: docs/chunks/narrative_cli_commands - Narrative command group
@cli.group()
def narrative():
    """Narrative commands"""
    pass


# Chunk: docs/chunks/narrative_cli_commands - Create narrative command
# Chunk: docs/chunks/task_aware_narrative_cmds - Task-aware narrative creation
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

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_narrative(project_dir, short_name)
        return

    # Single-repo mode
    narratives = Narratives(project_dir)
    narrative_path = narratives.create_narrative(short_name)

    # Show path relative to project_dir
    relative_path = narrative_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


# Chunk: docs/chunks/task_aware_narrative_cmds - Task directory narrative creation
def _create_task_narrative(task_dir: pathlib.Path, short_name: str):
    """Handle narrative creation in task directory (cross-repo mode)."""
    try:
        result = create_task_narrative(task_dir, short_name)
    except TaskNarrativeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_narrative_path"]
    click.echo(f"Created narrative in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the narrative directory, not the yaml file
        narrative_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {narrative_dir.relative_to(task_dir)}/")


# Chunk: docs/chunks/artifact_list_ordering - List narratives command
# Chunk: docs/chunks/task_aware_narrative_cmds - Task-aware narrative listing
@narrative.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_narratives(project_dir):
    """List all narratives."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_narratives(project_dir)
        return

    # Single-repo mode
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


# Chunk: docs/chunks/task_aware_narrative_cmds - Task directory narrative listing handler
def _list_task_narratives(task_dir: pathlib.Path):
    """Handle narrative listing in task directory (cross-repo mode)."""
    try:
        narrative_list = list_task_narratives(task_dir)
        if not narrative_list:
            click.echo("No narratives found", err=True)
            raise SystemExit(1)

        for narrative_info in narrative_list:
            name = narrative_info["name"]
            status = narrative_info["status"]
            dependents = narrative_info["dependents"]

            click.echo(f"docs/narratives/{name} [{status}]")
            if dependents:
                # Format dependents as: repo (artifact_id), repo (artifact_id)
                dep_strs = [f"{d['repo']} ({d['artifact_id']})" for d in dependents]
                click.echo(f"  dependents: {', '.join(dep_strs)}")
    except TaskNarrativeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/valid_transitions - Status command
@narrative.command()
@click.argument("narrative_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(narrative_id, new_status, project_dir):
    """Show or update narrative status."""
    from models import extract_short_name

    narratives = Narratives(project_dir)

    # Extract shortname for display
    shortname = extract_short_name(narrative_id)

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = narratives.get_status(narrative_id)
            click.echo(f"{shortname}: {current_status.value}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid NarrativeStatus value
    try:
        new_status_enum = NarrativeStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in NarrativeStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = narratives.update_status(narrative_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/task_init - Task command group
@cli.group()
def task():
    """Task directory commands."""
    pass


# Chunk: docs/chunks/task_init - Initialize task directory
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


# Chunk: docs/chunks/subsystem_cli_scaffolding - Subsystem command group
@cli.group()
def subsystem():
    """Subsystem commands"""
    pass


# Chunk: docs/chunks/subsystem_cli_scaffolding - List subsystems command
# Chunk: docs/chunks/artifact_list_ordering - Use ArtifactIndex for causal ordering
# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem listing
@subsystem.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_subsystems(project_dir):
    """List all subsystems."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_subsystems(project_dir)
        return

    # Single-repo mode
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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Task directory subsystem listing handler
def _list_task_subsystems(task_dir: pathlib.Path):
    """Handle subsystem listing in task directory (cross-repo mode)."""
    try:
        subsystem_list = list_task_subsystems(task_dir)
        if not subsystem_list:
            click.echo("No subsystems found", err=True)
            raise SystemExit(1)

        for subsystem_info in subsystem_list:
            name = subsystem_info["name"]
            status = subsystem_info["status"]
            dependents = subsystem_info["dependents"]

            click.echo(f"docs/subsystems/{name} [{status}]")
            if dependents:
                # Format dependents as: repo (artifact_id), repo (artifact_id)
                dep_strs = [f"{d['repo']} ({d['artifact_id']})" for d in dependents]
                click.echo(f"  dependents: {', '.join(dep_strs)}")
    except TaskSubsystemError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/subsystem_cli_scaffolding - Create subsystem command
# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem discovery
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

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_subsystem(project_dir, shortname)
        return

    # Single-repo mode
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


# Chunk: docs/chunks/task_aware_subsystem_cmds - Task directory subsystem creation handler
def _create_task_subsystem(task_dir: pathlib.Path, short_name: str):
    """Handle subsystem creation in task directory (cross-repo mode)."""
    try:
        result = create_task_subsystem(task_dir, short_name)
    except TaskSubsystemError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_subsystem_path"]
    click.echo(f"Created subsystem in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the subsystem directory, not the yaml file
        subsystem_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {subsystem_dir.relative_to(task_dir)}/")


# Chunk: docs/chunks/bidirectional_refs - Validate subsystem command
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


# Chunk: docs/chunks/subsystem_status_transitions - Status command
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


# Chunk: docs/chunks/subsystem_impact_resolution - Subsystem overlap command
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


# Chunk: docs/chunks/investigation_commands - Investigation command group
@cli.group()
def investigation():
    """Investigation commands"""
    pass


# Chunk: docs/chunks/investigation_commands - Create investigation command
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


# Chunk: docs/chunks/investigation_commands - List investigations command
# Chunk: docs/chunks/artifact_list_ordering - Use ArtifactIndex for causal ordering
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


# Chunk: docs/chunks/valid_transitions - Status command
@investigation.command()
@click.argument("investigation_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(investigation_id, new_status, project_dir):
    """Show or update investigation status."""
    from models import extract_short_name

    investigations = Investigations(project_dir)

    # Extract shortname for display
    shortname = extract_short_name(investigation_id)

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = investigations.get_status(investigation_id)
            click.echo(f"{shortname}: {current_status.value}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid InvestigationStatus value
    try:
        new_status_enum = InvestigationStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in InvestigationStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = investigations.update_status(investigation_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/ve_sync_command - Sync external references
# Chunk: docs/chunks/sync_all_workflows - Extended to all workflow artifact types
@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would be updated without making changes")
@click.option("--project", "projects", multiple=True, help="Sync only specified project(s) (task directory only)")
@click.option("--chunk", "chunks", multiple=True, help="Sync only specified chunk(s) (deprecated, use --artifact)")
@click.option("--artifact", "artifacts", multiple=True, help="Sync only specified artifact(s)")
@click.option(
    "--type", "artifact_type",
    type=click.Choice(["chunk", "narrative", "investigation", "subsystem"]),
    help="Sync only specified artifact type"
)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def sync(dry_run, projects, chunks, artifacts, artifact_type, project_dir):
    """Sync external artifact references to current repository state.

    Searches for external.yaml files in docs/chunks/, docs/narratives/,
    docs/investigations/, and docs/subsystems/ directories, then updates
    their pinned SHA to match the current state of the external repository.
    """
    # Convert filter tuples to lists (or None if empty)
    project_filter = list(projects) if projects else None

    # Combine --chunk and --artifact filters for backward compatibility
    artifact_filter = list(artifacts) if artifacts else []
    if chunks:
        artifact_filter.extend(chunks)
    artifact_filter = artifact_filter if artifact_filter else None

    # Convert artifact type string to ArtifactType
    artifact_types = None
    if artifact_type:
        artifact_types = [ArtifactType(artifact_type)]

    # Check if we're in a task directory
    if is_task_directory(project_dir):
        _sync_task_directory(project_dir, dry_run, project_filter, artifact_filter, artifact_types)
    else:
        # Single repo mode
        if project_filter:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _sync_single_repo(project_dir, dry_run, artifact_filter, artifact_types)


def _sync_task_directory(
    task_dir: pathlib.Path,
    dry_run: bool,
    project_filter: list[str] | None,
    artifact_filter: list[str] | None,
    artifact_types: list[ArtifactType] | None,
):
    """Handle sync in task directory mode."""
    try:
        results = sync_task_directory(
            task_dir,
            dry_run=dry_run,
            project_filter=project_filter,
            artifact_filter=artifact_filter,
            artifact_types=artifact_types,
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
    artifact_filter: list[str] | None,
    artifact_types: list[ArtifactType] | None,
):
    """Handle sync in single repo mode."""
    # Check if there are any external refs
    external_refs = find_external_refs(repo_path, artifact_types=artifact_types)
    if not external_refs:
        click.echo("No external references found")
        return

    results = sync_single_repo(
        repo_path,
        dry_run=dry_run,
        artifact_filter=artifact_filter,
        artifact_types=artifact_types,
    )

    _display_sync_results(results, dry_run)


def _display_sync_results(results: list, dry_run: bool):
    """Display sync results to the user."""
    updated_count = 0
    error_count = 0
    prefix = "[dry-run] " if dry_run else ""

    for result in results:
        # Format the display ID to include artifact type
        display_id = f"{result.artifact_type.value}:{result.artifact_id}"

        if result.error:
            click.echo(f"{prefix}Error syncing {display_id}: {result.error}", err=True)
            error_count += 1
        elif result.updated:
            old_abbrev = result.old_sha[:7] if result.old_sha else "(none)"
            new_abbrev = result.new_sha[:7] if result.new_sha else "(none)"
            verb = "Would update" if dry_run else "Updated"
            click.echo(f"{prefix}{display_id}: {old_abbrev} -> {new_abbrev} ({verb})")
            updated_count += 1
        else:
            old_abbrev = result.old_sha[:7] if result.old_sha else "(none)"
            click.echo(f"{prefix}{display_id}: {old_abbrev} (already current)")

    # Summary
    total = len(results)
    verb = "Would update" if dry_run else "Updated"
    click.echo(f"\n{prefix}{verb} {updated_count} of {total} external reference(s)")

    if error_count > 0:
        click.echo(f"{error_count} error(s) occurred", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/external_resolve - External command group
# Chunk: docs/chunks/external_resolve_all_types - Extended to all artifact types
@cli.group()
def external():
    """External artifact reference commands."""
    pass


# Chunk: docs/chunks/external_resolve - Resolve external chunk command
# Chunk: docs/chunks/external_resolve_all_types - Extended to all artifact types
@external.command()
@click.argument("local_artifact_id")
@click.option("--at-pinned", is_flag=True, help="Show content at pinned SHA instead of current HEAD")
@click.option("--main-only", is_flag=True, help="Show only main file content (GOAL.md for chunks, OVERVIEW.md for others)")
@click.option("--secondary-only", is_flag=True, help="Show only secondary file content (PLAN.md for chunks only)")
@click.option("--goal-only", is_flag=True, hidden=True, help="Alias for --main-only (backward compatibility)")
@click.option("--plan-only", is_flag=True, hidden=True, help="Alias for --secondary-only (backward compatibility)")
@click.option("--project", type=str, default=None, help="Specify project for disambiguation (task directory only)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def resolve(local_artifact_id, at_pinned, main_only, secondary_only, goal_only, plan_only, project, project_dir):
    """Display external artifact content.

    Resolves an external artifact reference and displays its content.
    Auto-detects artifact type from the path (chunks, narratives, investigations, subsystems).

    For chunks: displays GOAL.md and PLAN.md
    For other types: displays OVERVIEW.md

    Works in both task directory mode (using local worktrees) and single repo mode
    (using the repo cache).
    """
    # Handle backward-compatible aliases
    if goal_only:
        main_only = True
    if plan_only:
        secondary_only = True

    # Validate mutually exclusive options
    if main_only and secondary_only:
        click.echo("Error: --main-only and --secondary-only are mutually exclusive", err=True)
        raise SystemExit(1)

    # Determine mode and resolve
    if is_task_directory(project_dir):
        _resolve_external_task_directory(
            project_dir, local_artifact_id, at_pinned, main_only, secondary_only, project
        )
    else:
        if project:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _resolve_external_single_repo(
            project_dir, local_artifact_id, at_pinned, main_only, secondary_only
        )


# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
def _detect_artifact_type_from_id(project_path: pathlib.Path, local_artifact_id: str) -> ArtifactType:
    """Detect artifact type by searching for the artifact in project directories.

    Args:
        project_path: Path to the project directory
        local_artifact_id: Local artifact ID to find

    Returns:
        The detected ArtifactType

    Raises:
        TaskChunkError: If artifact is not found in any artifact directory
    """
    from external_refs import ARTIFACT_DIR_NAME

    for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
        artifacts_dir = project_path / "docs" / dir_name
        if not artifacts_dir.exists():
            continue
        for artifact_dir in artifacts_dir.iterdir():
            if artifact_dir.is_dir():
                if artifact_dir.name == local_artifact_id or artifact_dir.name.startswith(f"{local_artifact_id}-"):
                    return artifact_type

    raise TaskChunkError(f"Artifact '{local_artifact_id}' not found in any artifact directory")


def _resolve_external_task_directory(
    task_dir: pathlib.Path,
    local_artifact_id: str,
    at_pinned: bool,
    main_only: bool,
    secondary_only: bool,
    project_filter: str | None,
):
    """Handle resolve in task directory mode."""
    from external_refs import ARTIFACT_DIR_NAME
    from task_utils import load_task_config, resolve_repo_directory

    # Parse project:artifact format if present
    if ":" in local_artifact_id:
        parts = local_artifact_id.split(":", 1)
        project_filter = parts[0]
        local_artifact_id = parts[1]

    config = load_task_config(task_dir)

    # Filter projects to search
    projects_to_search = config.projects
    if project_filter:
        matching = [p for p in config.projects if p == project_filter or p.endswith(f"/{project_filter}")]
        if not matching:
            click.echo(f"Error: Project '{project_filter}' not found in task configuration", err=True)
            raise SystemExit(1)
        projects_to_search = matching

    # Find artifact and detect type
    artifact_type = None
    for project_ref in projects_to_search:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            artifact_type = _detect_artifact_type_from_id(project_path, local_artifact_id)
            break
        except (FileNotFoundError, TaskChunkError):
            continue

    if artifact_type is None:
        click.echo(f"Error: Artifact '{local_artifact_id}' not found", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_task_directory(
            task_dir,
            local_artifact_id,
            artifact_type,
            at_pinned=at_pinned,
            project_filter=project_filter,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


def _resolve_external_single_repo(
    repo_path: pathlib.Path,
    local_artifact_id: str,
    at_pinned: bool,
    main_only: bool,
    secondary_only: bool,
):
    """Handle resolve in single repo mode."""
    # Detect artifact type from the repo
    try:
        artifact_type = _detect_artifact_type_from_id(repo_path, local_artifact_id)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_single_repo(
            repo_path,
            local_artifact_id,
            artifact_type,
            at_pinned=at_pinned,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


# Chunk: docs/chunks/external_resolve_all_types - Type-aware display
def _display_resolve_result(result: ResolveResult, main_only: bool, secondary_only: bool):
    """Display the resolve result to the user."""
    # Header with metadata
    artifact_type_display = result.artifact_type.value.capitalize()
    click.echo(f"External {artifact_type_display} Reference")
    click.echo("=" * (len(f"External {artifact_type_display} Reference")))
    click.echo(f"Repository: {result.repo}")
    click.echo(f"{artifact_type_display}: {result.artifact_id}")
    click.echo(f"Track: {result.track}")
    click.echo(f"SHA: {result.resolved_sha}")
    click.echo("")

    # Determine file names based on artifact type
    main_file = ARTIFACT_MAIN_FILE[result.artifact_type]
    secondary_file = "PLAN.md" if result.artifact_type == ArtifactType.CHUNK else None

    # Content
    if not secondary_only:
        click.echo(f"--- {main_file} ---")
        if result.main_content:
            click.echo(result.main_content)
        else:
            click.echo("(not found)")

    # Only show secondary file section for chunks
    if secondary_file and not main_only:
        if not secondary_only:
            click.echo("")
        click.echo(f"--- {secondary_file} ---")
        if result.secondary_content:
            click.echo(result.secondary_content)
        else:
            click.echo("(not found)")


if __name__ == "__main__":
    cli()
