"""Vibe Engineer CLI - view layer for chunk management."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering
# Chunk: docs/chunks/copy_as_external - ve artifact copy-external command
# Chunk: docs/chunks/explicit_deps_batch_inject - Batch injection with dependency ordering
# Chunk: docs/chunks/explicit_deps_null_inject - Null vs empty depends_on handling in orch inject
# Chunk: docs/chunks/external_resolve - ve external resolve command
# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
# Chunk: docs/chunks/external_resolve_enhance - Enhanced resolve output format
# Chunk: docs/chunks/external_artifact_unpin - Removed sync command and pinning
# Chunk: docs/chunks/orch_tcp_port - ve orch start with --port and --host options
# Chunk: docs/chunks/orch_url_command - ve orch url command for getting orchestrator endpoint
# Chunk: docs/chunks/project_init_command - ve init command for project initialization
# Chunk: docs/chunks/remove_external_ref - ve artifact remove-external command
# Chunk: docs/chunks/rename_chunk_start_to_create - ve chunk create command with start alias

import pathlib

import click

from chunks import Chunks
from external_refs import strip_artifact_path_prefix, is_external_artifact, load_external_ref
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
    create_task_investigation,
    list_task_investigations,
    TaskInvestigationError,
    create_task_narrative,
    list_task_narratives,
    TaskNarrativeError,
    create_task_subsystem,
    list_task_subsystems,
    TaskSubsystemError,
    promote_artifact,
    TaskPromoteError,
    list_task_artifacts_grouped,
    TaskArtifactListError,
    list_task_proposed_chunks,
    copy_artifact_as_external,
    TaskCopyExternalError,
    parse_projects_option,
    load_task_config,
    check_task_project_context,
    TaskProjectContext,
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
from cluster_analysis import check_cluster_size, format_cluster_warning
from chunks import get_chunk_prefix
from artifact_ordering import ArtifactIndex, ArtifactType


def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


# Chunk: docs/chunks/chunknaming_drop_ticket - Validation simplified to check only short_name length
def validate_combined_chunk_name(short_name: str, ticket_id: str | None) -> list[str]:
    """Validate the chunk directory name length.

    Since ticket_id no longer affects the directory name (it's stored only in
    frontmatter), we only validate the short_name length. The directory name
    is just {short_name} and must not exceed 31 characters to match the
    ExternalArtifactRef.artifact_id limit.

    Args:
        short_name: The short name of the chunk.
        ticket_id: Optional ticket ID (kept for backward compatibility but
                   not used - ticket_id no longer affects directory names).

    Returns:
        List of error messages (empty if valid).
    """
    # ticket_id no longer affects directory name, so only validate short_name
    combined_name = short_name

    if len(combined_name) > 31:
        return [
            f"Chunk name '{combined_name}' is {len(combined_name)} characters, "
            f"exceeds limit of 31 characters"
        ]
    return []


def warn_task_project_context(context: TaskProjectContext | None, artifact_type: str) -> None:
    """Emit a warning if running an artifact command from within a task's project.

    This warning helps prevent the common mistake of creating local artifacts
    when cross-repo artifacts were intended.

    Args:
        context: TaskProjectContext from check_task_project_context(), or None.
        artifact_type: Human-readable name of the artifact type (e.g., "chunk", "narrative").
    """
    if context is None:
        return

    click.echo(
        f"Warning: You are creating a local {artifact_type} in project '{context.project_ref}', "
        f"which is part of a task. To create a cross-repo {artifact_type}, run this command from "
        f"the task directory instead.",
        err=True,
    )


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


# Chunk: docs/chunks/integrity_validate - Project-wide referential integrity validation
@cli.command()
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


@cli.group()
def chunk():
    """Chunk commands"""
    pass


@chunk.command("create")
@click.argument("short_names", nargs=-1, required=True)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--future", is_flag=True, help="Create chunk with FUTURE status instead of IMPLEMENTING")
@click.option("--ticket", default=None, help="Ticket ID to apply to all chunks")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
# Chunk: docs/chunks/chunk_batch_create - CLI command accepting variadic chunk names with batch creation logic
def create(short_names, project_dir, yes, future, ticket, projects):
    """Create a new chunk (or multiple chunks).

    Creates chunks in docs/chunks/. Task context routes to task-scoped storage.

    Single chunk: ve chunk create my_feature [TICKET_ID]
    Multiple chunks: ve chunk create chunk_a chunk_b chunk_c --future [--ticket TICKET_ID]

    When creating multiple chunks, use --ticket flag for ticket ID.
    """
    # Legacy mode: "ve chunk create my_feature VE-001" (single chunk with positional ticket)
    # Batch mode: "ve chunk create chunk_a chunk_b chunk_c --future" (multiple chunks)
    #
    # Heuristic for backward compatibility:
    # - If --ticket flag is provided: batch mode (all args are chunk names)
    # - If exactly 2 args without --ticket AND second arg looks like a ticket (contains '-'):
    #   legacy mode (first is short_name, second is ticket_id)
    # - Otherwise: batch mode (all args are chunk names)
    #
    # The '-' heuristic works because:
    # - Ticket IDs commonly use dashes (e.g., "VE-001", "JIRA-123")
    # - Chunk names typically use underscores (e.g., "my_feature", "chunk_a")
    # - Users who want 2-chunk batch with dashed names can use: --ticket "" or 3+ chunks
    ticket_id = ticket  # Start with flag value
    names_to_create = list(short_names)

    if len(short_names) == 2 and ticket_id is None:
        second_arg = short_names[1]
        # Treat as legacy mode only if second arg looks like a ticket (contains dash)
        if "-" in second_arg:
            ticket_errors = validate_ticket_id(second_arg)
            if not ticket_errors:
                ticket_id = second_arg.lower()
                names_to_create = [short_names[0]]

    # Check for duplicate names in the input
    seen_names = set()
    duplicate_names = []
    for name in names_to_create:
        lower_name = name.lower()
        if lower_name in seen_names:
            duplicate_names.append(name)
        seen_names.add(lower_name)

    if duplicate_names:
        click.echo(f"Error: Duplicate chunk names provided: {', '.join(duplicate_names)}", err=True)
        raise SystemExit(1)

    # Validate all names upfront and collect errors per name
    validation_errors = {}  # name -> list of errors
    valid_names = []

    for name in names_to_create:
        errors = validate_short_name(name)
        errors.extend(validate_combined_chunk_name(name.lower(), ticket_id))
        if errors:
            validation_errors[name] = errors
        else:
            valid_names.append(name.lower())

    # Validate ticket_id if provided
    if ticket_id:
        ticket_errors = validate_ticket_id(ticket_id)
        if ticket_errors:
            for error in ticket_errors:
                click.echo(f"Error: {error}", err=True)
            raise SystemExit(1)
        ticket_id = ticket_id.lower()

    # Report validation errors
    for name, errors in validation_errors.items():
        for error in errors:
            click.echo(f"Error ({name}): {error}", err=True)

    # If no valid names, exit early
    if not valid_names:
        raise SystemExit(1)

    # Determine status based on --future flag
    status = "FUTURE" if future else "IMPLEMENTING"

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _start_task_chunks(project_dir, valid_names, ticket_id, status, projects)
        # If there were validation errors, exit with error code
        if validation_errors:
            raise SystemExit(1)
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "chunk")

    # Single-repo mode - create in docs/chunks/
    chunks_manager = Chunks(project_dir)

    # For non-FUTURE status, check the IMPLEMENTING guard once upfront
    if status != "FUTURE":
        current = chunks_manager.get_current_chunk()
        if current is not None:
            click.echo(
                f"Error: Cannot create: chunk '{current}' is already IMPLEMENTING. "
                f"Run 've chunk complete' first.",
                err=True,
            )
            raise SystemExit(1)

    # Create each chunk, collecting results
    created_paths = []
    creation_errors = {}  # name -> error message

    for name in valid_names:
        try:
            chunk_path = chunks_manager.create_chunk(ticket_id, name, status=status)
            created_paths.append(chunk_path)
        except ValueError as e:
            creation_errors[name] = str(e)

    # Report results
    for chunk_path in created_paths:
        relative_path = chunk_path.relative_to(project_dir)
        click.echo(f"Created {relative_path}")

    for name, error in creation_errors.items():
        click.echo(f"Error ({name}): {error}", err=True)

    # Check cluster size warnings (once at end, for all created chunks)
    # Chunk: docs/chunks/cluster_subsystem_prompt - Cluster size warning after chunk creation
    if created_paths:
        prefixes_seen = set()
        for chunk_path in created_paths:
            prefix = get_chunk_prefix(chunk_path.name)
            if prefix and prefix not in prefixes_seen:
                prefixes_seen.add(prefix)
                warning = check_cluster_size(prefix, project_dir, include_new_chunk=False)
                if warning.should_warn:
                    click.echo(f"Note: {format_cluster_warning(warning)}")

    # Exit with error if there were any validation or creation errors
    if validation_errors or creation_errors:
        raise SystemExit(1)


chunk.add_command(create, name="start")


# Chunk: docs/chunks/chunk_create_task_aware - CLI handler for cross-repo mode output
def _start_task_chunk(
    task_dir: pathlib.Path,
    short_name: str,
    ticket_id: str | None,
    status: str = "IMPLEMENTING",
    projects_input: str | None = None,
):
    """Handle chunk creation in task directory (cross-repo mode)."""
    # Parse and validate projects option
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = create_task_chunk(task_dir, short_name, ticket_id, status=status, projects=projects)
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


# Chunk: docs/chunks/chunk_batch_create - Batch chunk creation handler for task directory mode
def _start_task_chunks(
    task_dir: pathlib.Path,
    short_names: list[str],
    ticket_id: str | None,
    status: str = "IMPLEMENTING",
    projects_input: str | None = None,
):
    """Handle batch chunk creation in task directory (cross-repo mode)."""
    # Parse and validate projects option once
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Create each chunk, collecting results and errors
    creation_errors = {}

    for short_name in short_names:
        try:
            result = create_task_chunk(task_dir, short_name, ticket_id, status=status, projects=projects)
            # Report created paths for this chunk
            external_path = result["external_chunk_path"]
            click.echo(f"Created chunk in external repo: {external_path.relative_to(task_dir)}/")

            for project_ref, yaml_path in result["project_refs"].items():
                chunk_dir = yaml_path.parent
                click.echo(f"Created reference in {project_ref}: {chunk_dir.relative_to(task_dir)}/")
        except TaskChunkError as e:
            creation_errors[short_name] = str(e)

    # Report any creation errors
    for name, error in creation_errors.items():
        click.echo(f"Error ({name}): {error}", err=True)

    if creation_errors:
        raise SystemExit(1)


def _parse_status_filters(
    status_option: tuple[str, ...],
    future_flag: bool,
    active_flag: bool,
    implementing_flag: bool,
) -> tuple[set[ChunkStatus] | None, str | None]:
    """Parse and validate status filters from CLI options.

    Args:
        status_option: Tuple of status strings from --status option (may include comma-separated)
        future_flag: Whether --future flag was set
        active_flag: Whether --active flag was set
        implementing_flag: Whether --implementing flag was set

    Returns:
        Tuple of (status_set, error_message). status_set is None if no filtering requested,
        or a set of ChunkStatus values. error_message is None on success, or contains
        the error message with valid options listed.
    """
    statuses: set[ChunkStatus] = set()

    # Add statuses from convenience flags
    if future_flag:
        statuses.add(ChunkStatus.FUTURE)
    if active_flag:
        statuses.add(ChunkStatus.ACTIVE)
    if implementing_flag:
        statuses.add(ChunkStatus.IMPLEMENTING)

    # Parse statuses from --status option (handles comma-separated and multiple options)
    for status_str in status_option:
        # Split by comma to handle --status FUTURE,ACTIVE
        parts = [s.strip() for s in status_str.split(",") if s.strip()]
        for part in parts:
            # Case-insensitive lookup
            upper_part = part.upper()
            try:
                statuses.add(ChunkStatus(upper_part))
            except ValueError:
                valid_statuses = ", ".join(s.value for s in ChunkStatus)
                return None, f"Invalid status '{part}'. Valid statuses: {valid_statuses}"

    # Return None if no filtering requested (empty set means show all)
    if not statuses:
        return None, None

    return statuses, None


@chunk.command("list")
@click.option("--current", is_flag=True, help="Output only the current IMPLEMENTING chunk")
@click.option("--last-active", is_flag=True, help="Output only the most recently completed ACTIVE chunk")
@click.option("--recent", is_flag=True, help="Output the 10 most recently created ACTIVE chunks")
@click.option(
    "--status",
    "status_filter",
    multiple=True,
    help="Filter by status (case-insensitive). Can specify multiple times or comma-separated. "
    "Valid statuses: FUTURE, IMPLEMENTING, ACTIVE, SUPERSEDED, HISTORICAL",
)
@click.option("--future", "future_flag", is_flag=True, help="Show only FUTURE chunks (shortcut for --status FUTURE)")
@click.option("--active", "active_flag", is_flag=True, help="Show only ACTIVE chunks (shortcut for --status ACTIVE)")
@click.option(
    "--implementing",
    "implementing_flag",
    is_flag=True,
    help="Show only IMPLEMENTING chunks (shortcut for --status IMPLEMENTING)",
)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
# Chunk: docs/chunks/artifact_list_ordering - CLI command with tip indicator display using ArtifactIndex
# Chunk: docs/chunks/chunk_list_command-ve-002 - CLI command ve chunk list with --latest, --last-active, and --project-dir options
# Chunk: docs/chunks/chunk_list_flags - CLI command with renamed --current flag and new --recent flag
# Chunk: docs/chunks/chunk_last_active - CLI handler with --last-active flag and mutual exclusivity check
# Chunk: docs/chunks/chunklist_status_filter - Status filter parsing and handling
# Chunk: docs/chunks/chunklist_external_status - External chunk status display in list output
def list_chunks(current, last_active, recent, status_filter, future_flag, active_flag, implementing_flag, project_dir):
    """List all chunks.

    Lists chunks from docs/chunks/. Task context lists from task-scoped storage.

    Status filtering: Use --status to filter by chunk lifecycle state.
    Multiple statuses can be specified with multiple --status options or
    comma-separated values (e.g., --status FUTURE,ACTIVE). Status values
    are case-insensitive.

    Convenience flags: --future, --active, --implementing are shortcuts
    for the corresponding --status values.

    Note: --status filters and convenience flags are mutually exclusive
    with --current, --last-active, and --recent.
    """
    # Parse status filters
    status_set, error = _parse_status_filters(status_filter, future_flag, active_flag, implementing_flag)
    if error:
        click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Check mutual exclusivity of output modes
    has_status_filter = status_set is not None
    # Count how many exclusive output modes are set
    exclusive_modes = [current, last_active, recent]
    exclusive_count = sum(1 for mode in exclusive_modes if mode)
    if exclusive_count > 1:
        click.echo(
            "Error: --current, --last-active, and --recent are mutually exclusive. Cannot use more than one.",
            err=True,
        )
        raise SystemExit(1)
    if has_status_filter and current:
        click.echo(
            "Error: Status filters (--status, --future, --active, --implementing) are "
            "mutually exclusive with --current.",
            err=True,
        )
        raise SystemExit(1)
    if has_status_filter and last_active:
        click.echo(
            "Error: Status filters (--status, --future, --active, --implementing) are "
            "mutually exclusive with --last-active.",
            err=True,
        )
        raise SystemExit(1)
    if has_status_filter and recent:
        click.echo(
            "Error: Status filters (--status, --future, --active, --implementing) are "
            "mutually exclusive with --recent.",
            err=True,
        )
        raise SystemExit(1)

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_chunks(current, last_active, recent, status_set, project_dir)
        return

    # Single-repo mode - list from docs/chunks/
    chunks = Chunks(project_dir)

    if current:
        current_chunk = chunks.get_current_chunk()
        if current_chunk is None:
            click.echo("No implementing chunk found", err=True)
            raise SystemExit(1)
        click.echo(f"docs/chunks/{current_chunk}")
    elif last_active:
        active_chunk = chunks.get_last_active_chunk()
        if active_chunk is None:
            click.echo("No active tip chunk found", err=True)
            raise SystemExit(1)
        click.echo(f"docs/chunks/{active_chunk}")
    elif recent:
        recent_chunks = chunks.get_recent_active_chunks(limit=10)
        if not recent_chunks:
            click.echo("No active chunks found", err=True)
            raise SystemExit(1)
        for chunk_name in recent_chunks:
            click.echo(f"docs/chunks/{chunk_name}")
    else:
        chunk_list = chunks.list_chunks()
        if not chunk_list:
            click.echo("No chunks found", err=True)
            raise SystemExit(1)

        artifact_index = ArtifactIndex(project_dir)
        tips = set(artifact_index.find_tips(ArtifactType.CHUNK))

        # Track if any chunks pass the filter
        filtered_count = 0

        for chunk_name in chunk_list:
            chunk_path = project_dir / "docs" / "chunks" / chunk_name
            # Check for external artifact reference before parsing frontmatter
            if is_external_artifact(chunk_path, ArtifactType.CHUNK):
                external_ref = load_external_ref(chunk_path)
                # External chunks have no parseable status - skip when filtering
                if status_set is not None:
                    continue
                status = f"EXTERNAL: {external_ref.repo}"
            else:
                frontmatter, errors = chunks.parse_chunk_frontmatter_with_errors(chunk_name)
                if frontmatter:
                    chunk_status = frontmatter.status
                    # Apply status filter if specified
                    if status_set is not None and chunk_status not in status_set:
                        continue
                    status = chunk_status.value
                elif errors:
                    # Chunks with parse errors - skip when filtering
                    if status_set is not None:
                        continue
                    # Show first error for brevity
                    first_error = errors[0]
                    status = f"PARSE ERROR: {first_error}"
                else:
                    # Unknown status - skip when filtering
                    if status_set is not None:
                        continue
                    status = "UNKNOWN"
            filtered_count += 1
            tip_indicator = " *" if chunk_name in tips else ""
            click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")

        # Handle case where all chunks were filtered out
        if filtered_count == 0:
            if status_set is not None:
                status_names = ", ".join(s.value for s in status_set)
                click.echo(f"No chunks found matching status: {status_names}", err=True)
            else:
                click.echo("No chunks found", err=True)
            raise SystemExit(1)


@chunk.command("complete")
@click.argument("chunk_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def complete_chunk(chunk_id, project_dir):
    """Complete a chunk by updating its status to ACTIVE.

    If no CHUNK_ID is provided, completes the current IMPLEMENTING chunk.
    """
    from task_utils import update_frontmatter_field

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        click.echo("Error: complete command not supported in task context", err=True)
        raise SystemExit(1)

    # Single-repo mode - complete in docs/chunks/
    chunks = Chunks(project_dir)

    if chunk_id is None:
        chunk_id = chunks.get_current_chunk()
        if chunk_id is None:
            click.echo("No implementing chunk found", err=True)
            raise SystemExit(1)

    chunk_name = chunks.resolve_chunk_id(chunk_id)
    if chunk_name is None:
        click.echo(f"Chunk '{chunk_id}' not found", err=True)
        raise SystemExit(1)

    goal_path = project_dir / "docs" / "chunks" / chunk_name / "GOAL.md"
    update_frontmatter_field(goal_path, "status", "ACTIVE")
    click.echo(f"Completed docs/chunks/{chunk_name}")


def _format_grouped_artifact_list(
    grouped_data: dict,
    artifact_type_dir: str,
    status_set: set[ChunkStatus] | None = None,
) -> None:
    """Format and display grouped artifact listing output.

    Args:
        grouped_data: Dict from list_task_artifacts_grouped with external and projects keys
        artifact_type_dir: Directory name for the artifact type (e.g., "chunks", "narratives")
        status_set: If provided, filter to only artifacts with matching status (chunks only)
    """
    external = grouped_data["external"]
    projects = grouped_data["projects"]

    # Apply status filtering if specified (only applies to chunks)
    def status_matches(status_str: str) -> bool:
        """Check if an artifact's status string matches the filter."""
        if status_set is None:
            return True
        # Try to convert status string to ChunkStatus
        try:
            artifact_status = ChunkStatus(status_str.upper())
            return artifact_status in status_set
        except ValueError:
            # Status doesn't match any ChunkStatus (e.g., EXTERNAL, PARSE ERROR)
            # Exclude when filtering
            return False

    # Filter external artifacts
    filtered_external = [a for a in external["artifacts"] if status_matches(a["status"])]

    # Filter project artifacts
    filtered_projects = []
    for project in projects:
        filtered_artifacts = [a for a in project["artifacts"] if status_matches(a["status"])]
        filtered_projects.append({**project, "artifacts": filtered_artifacts})

    # Check if there are any artifacts after filtering
    has_external = bool(filtered_external)
    has_projects = any(p["artifacts"] for p in filtered_projects)

    if not has_external and not has_projects:
        if status_set is not None:
            status_names = ", ".join(s.value for s in status_set)
            click.echo(f"No {artifact_type_dir} found matching status: {status_names}", err=True)
        else:
            click.echo(f"No {artifact_type_dir} found", err=True)
        raise SystemExit(1)

    # Display external artifacts
    if filtered_external:
        click.echo(f"# External Artifacts ({external['repo']})")
        for artifact in filtered_external:
            name = artifact["name"]
            status = artifact["status"]
            is_tip = artifact.get("is_tip", False)
            tip_indicator = " (tip)" if is_tip else ""

            click.echo(f"{name} [{status}]{tip_indicator}")

            # Show dependents for external artifacts
            dependents = artifact.get("dependents", [])
            if dependents:
                repos = sorted(set(d["repo"] for d in dependents))
                click.echo(f"  → referenced by: {', '.join(repos)}")
        click.echo()

    # Display each project's local artifacts
    for project in filtered_projects:
        if project["artifacts"]:
            click.echo(f"# {project['repo']} (local)")
            for artifact in project["artifacts"]:
                name = artifact["name"]
                status = artifact["status"]
                is_tip = artifact.get("is_tip", False)
                tip_indicator = " (tip)" if is_tip else ""

                click.echo(f"{name} [{status}]{tip_indicator}")
            click.echo()


# Chunk: docs/chunks/chunk_list_repo_source - Format output as {external_repo}::docs/chunks/{chunk_name} in --latest mode
# Chunk: docs/chunks/chunk_last_active - Cross-repo (task context) support for --last-active
def _list_task_chunks(
    current: bool,
    last_active: bool,
    recent: bool,
    status_set: set[ChunkStatus] | None,
    task_dir: pathlib.Path,
):
    """Handle chunk listing in task directory (cross-repo mode).

    Args:
        current: If True, output only the current IMPLEMENTING chunk
        last_active: If True, output only the most recently completed ACTIVE chunk
        recent: If True, output the 10 most recently created ACTIVE chunks
        status_set: If provided, filter to only chunks with matching status
        task_dir: Path to the task directory
    """
    try:
        if current:
            current_chunk, external_repo = get_current_task_chunk(task_dir)
            if current_chunk is None:
                click.echo("No implementing chunk found", err=True)
                raise SystemExit(1)
            click.echo(f"{external_repo}::docs/chunks/{current_chunk}")
        elif last_active:
            # For task context, get the last active chunk from the external artifacts repo
            from task_utils import resolve_repo_directory, load_task_config

            config = load_task_config(task_dir)
            external_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            active_chunk = external_chunks.get_last_active_chunk()
            if active_chunk is None:
                click.echo("No active tip chunk found", err=True)
                raise SystemExit(1)
            click.echo(f"{config.external_artifact_repo}::docs/chunks/{active_chunk}")
        elif recent:
            # For task context, get recent active chunks from the external artifacts repo
            from task_utils import resolve_repo_directory, load_task_config

            config = load_task_config(task_dir)
            external_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            recent_chunks = external_chunks.get_recent_active_chunks(limit=10)
            if not recent_chunks:
                click.echo("No active chunks found", err=True)
                raise SystemExit(1)
            for chunk_name in recent_chunks:
                click.echo(f"{config.external_artifact_repo}::docs/chunks/{chunk_name}")
        else:
            grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.CHUNK)
            _format_grouped_artifact_list(grouped_data, "chunks", status_set)
    except (TaskChunkError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _format_proposed_chunks_by_source(proposed: list[dict]) -> None:
    """Format proposed chunks grouped by source artifact.

    Args:
        proposed: List of proposed chunk dicts with source_type and source_id keys
    """
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


def _format_grouped_proposed_chunks(grouped_data: dict) -> None:
    """Format and display grouped proposed chunk listing output.

    Args:
        grouped_data: Dict from list_task_proposed_chunks with external and projects keys
    """
    external = grouped_data["external"]
    projects = grouped_data["projects"]

    # Check if there are any proposed chunks at all
    has_external = bool(external["proposed_chunks"])
    has_projects = any(p["proposed_chunks"] for p in projects)

    if not has_external and not has_projects:
        click.echo("No proposed chunks found", err=True)
        raise SystemExit(0)

    # Display external artifacts section
    click.echo(f"# External Artifacts ({external['repo']})")
    if external["proposed_chunks"]:
        _format_proposed_chunks_by_source(external["proposed_chunks"])
    else:
        click.echo("No proposed chunks")
    click.echo()

    # Display each project's proposed chunks
    for project in projects:
        click.echo(f"# {project['repo']} (local)")
        if project["proposed_chunks"]:
            _format_proposed_chunks_by_source(project["proposed_chunks"])
        else:
            click.echo("No proposed chunks")
        click.echo()


def _list_task_proposed_chunks(task_dir: pathlib.Path):
    """Handle proposed chunk listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_proposed_chunks(task_dir)
        _format_grouped_proposed_chunks(grouped_data)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@chunk.command("list-proposed")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_proposed_chunks_cmd(project_dir):
    """List all proposed chunks that haven't been created yet."""
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_proposed_chunks(project_dir)
        return

    # Single-repo mode
    chunks = Chunks(project_dir)
    investigations = Investigations(project_dir)
    narratives = Narratives(project_dir)
    subsystems = Subsystems(project_dir)

    proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems)

    if not proposed:
        click.echo("No proposed chunks found", err=True)
        raise SystemExit(0)

    _format_proposed_chunks_by_source(proposed)


# Chunk: docs/chunks/accept_full_artifact_paths - CLI command using strip_artifact_path_prefix
@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def activate(chunk_id, project_dir):
    """Activate a FUTURE chunk by changing its status to IMPLEMENTING.

    When run in task context (directory with .ve-task.yaml), searches for
    the chunk across the external repo and all project repos.
    """
    from task_utils import (
        is_task_directory,
        find_task_directory,
        activate_task_chunk,
        TaskActivateError,
    )

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    # Detect task context
    task_dir = None
    if is_task_directory(project_dir):
        task_dir = project_dir
    else:
        task_dir = find_task_directory(project_dir)

    if task_dir is not None:
        # Task context: search across all repos
        try:
            repo_ref, activated = activate_task_chunk(task_dir, chunk_id)
        except (TaskActivateError, ValueError) as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        click.echo(f"Activated {repo_ref}:docs/chunks/{activated}")
    else:
        # Single repo context
        chunks = Chunks(project_dir)

        try:
            activated = chunks.activate_chunk(chunk_id)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        click.echo(f"Activated docs/chunks/{activated}")


# Chunk: docs/chunks/accept_full_artifact_paths - CLI chunk status command using strip_artifact_path_prefix
@chunk.command()
@click.argument("chunk_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(chunk_id, new_status, project_dir):
    """Show or update chunk status."""
    from models import extract_short_name

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

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


# Chunk: docs/chunks/chunk_overlap_command - CLI command for finding overlapping chunks
# Chunk: docs/chunks/accept_full_artifact_paths - CLI chunk overlap command using strip_artifact_path_prefix
@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find chunks with overlapping code references.

    When run in task context (directory with .ve-task.yaml), searches for
    overlapping chunks across the external repo and all project repos.
    Supports project-qualified code references (e.g., "project::src/foo.py#Bar").
    """
    from task_utils import (
        is_task_directory,
        find_task_directory,
        find_task_overlapping_chunks,
        TaskOverlapError,
    )

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    # Detect task context
    task_dir = None
    if is_task_directory(project_dir):
        task_dir = project_dir
    else:
        task_dir = find_task_directory(project_dir)

    if task_dir is not None:
        # Task context: use cross-repo overlap detection
        try:
            result = find_task_overlapping_chunks(task_dir, chunk_id)
        except (TaskOverlapError, ValueError) as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        for repo_ref, name in result.overlapping_chunks:
            click.echo(f"{repo_ref}:docs/chunks/{name}")
    else:
        # Single repo context
        chunks = Chunks(project_dir)

        try:
            affected = chunks.find_overlapping_chunks(chunk_id)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        for name in affected:
            click.echo(f"docs/chunks/{name}")


# Chunk: docs/chunks/cluster_prefix_suggest - CLI command for prefix suggestion
# Chunk: docs/chunks/accept_full_artifact_paths - CLI suggest-prefix command using strip_artifact_path_prefix
@chunk.command("suggest-prefix")
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--threshold", type=float, default=0.4, help="Minimum similarity threshold (default: 0.4)")
@click.option("--top-k", type=int, default=5, help="Number of similar chunks to consider (default: 5)")
def suggest_prefix_cmd(chunk_id, project_dir, threshold, top_k):
    """Suggest a prefix for a chunk based on similarity to existing chunks.

    Computes TF-IDF similarity between the target chunk's GOAL.md and all other
    chunks. If the most similar chunks share a common prefix, suggests using
    that prefix for better semantic clustering.
    """
    from chunks import suggest_prefix

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    result = suggest_prefix(project_dir, chunk_id, threshold=threshold, top_k=top_k)

    if result.suggested_prefix is None and not result.similar_chunks:
        # Chunk not found or error
        click.echo(f"Error: {result.reason}", err=True)
        raise SystemExit(1)

    if result.suggested_prefix:
        click.echo(f"Suggested prefix: {result.suggested_prefix}")
        click.echo("")
        click.echo("Similar chunks (informing this suggestion):")
        for name, similarity in result.similar_chunks:
            click.echo(f"  - {name} (similarity: {similarity:.2f})")
    else:
        click.echo("No prefix suggestion.")
        click.echo(f"Reason: {result.reason}")
        if result.similar_chunks:
            click.echo("")
            click.echo("Most similar chunks:")
            for name, similarity in result.similar_chunks:
                click.echo(f"  - {name} (similarity: {similarity:.2f})")


@chunk.command("backrefs")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--threshold", type=int, default=5, help="Minimum unique chunk refs to display (default: 5)")
@click.option("--pattern", multiple=True, help="Glob patterns to search (default: src/**/*.py)")
def backrefs(project_dir, threshold, pattern):
    """Analyze backreference distribution across source files.

    Scans source files for `# Chunk:`, `# Narrative:`, and `# Subsystem:`
    comments and displays files exceeding the threshold.

    This helps identify code areas with excessive chunk backreferences
    that may benefit from consolidation into a narrative.
    """
    from chunks import count_backreferences

    # Use default patterns if none provided
    patterns = list(pattern) if pattern else None

    results = count_backreferences(project_dir, source_patterns=patterns)

    # Filter by threshold
    above_threshold = [r for r in results if r.unique_chunk_count >= threshold]

    if not above_threshold:
        if results:
            click.echo(f"No files with {threshold}+ unique chunk backreferences found.")
            max_refs = max(r.unique_chunk_count for r in results)
            click.echo(f"Maximum found: {max_refs} unique refs.")
        else:
            click.echo("No chunk backreferences found in source files.")
        return

    click.echo(f"Files with {threshold}+ chunk backreferences:")
    click.echo("")
    for info in above_threshold:
        rel_path = info.file_path.relative_to(project_dir)
        unique = info.unique_chunk_count
        total = info.total_chunk_count
        click.echo(f"  {rel_path}: {unique} unique chunks ({total} total refs)")

        # Show narrative/subsystem context if present
        if info.narrative_refs:
            click.echo(f"    Already has {len(set(info.narrative_refs))} narrative ref(s)")
        if info.subsystem_refs:
            click.echo(f"    Has {len(set(info.subsystem_refs))} subsystem ref(s)")

    click.echo("")
    click.echo(f"Total: {len(above_threshold)} file(s) above threshold")


@chunk.command("cluster")
@click.argument("chunk_ids", nargs=-1)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--min-similarity", type=float, default=0.3, help="Minimum similarity to cluster (default: 0.3)")
@click.option("--all", "cluster_all", is_flag=True, help="Cluster all ACTIVE chunks")
def cluster(chunk_ids, project_dir, min_similarity, cluster_all):
    """Cluster chunks by content similarity for narrative consolidation.

    Groups related chunks based on TF-IDF similarity of their GOAL.md content.
    Use this to identify candidate chunks for consolidation into a narrative.

    Examples:
        ve chunk cluster --all                    # Cluster all ACTIVE chunks
        ve chunk cluster chunk1 chunk2 chunk3    # Cluster specific chunks
    """
    from chunks import cluster_chunks

    # Determine which chunks to cluster
    if cluster_all:
        target_chunks = None  # cluster_chunks will use all ACTIVE
    elif chunk_ids:
        # Normalize chunk IDs to strip path prefixes
        target_chunks = [strip_artifact_path_prefix(cid, ArtifactType.CHUNK) for cid in chunk_ids]
    else:
        click.echo("Error: Provide chunk IDs or use --all to cluster all ACTIVE chunks", err=True)
        raise SystemExit(1)

    result = cluster_chunks(project_dir, chunk_ids=target_chunks, min_similarity=min_similarity)

    if not result.clusters:
        click.echo("No clusters found.")
        if result.unclustered:
            click.echo(f"\nUnclustered chunks ({len(result.unclustered)}):")
            for name in result.unclustered:
                click.echo(f"  - {name}")
        return

    # Display clusters
    click.echo(f"Found {len(result.clusters)} cluster(s):\n")
    for i, (cluster, theme) in enumerate(zip(result.clusters, result.cluster_themes), 1):
        click.echo(f"Cluster {i}: {theme}")
        for name in cluster:
            click.echo(f"  - {name}")
        click.echo("")

    if result.unclustered:
        click.echo(f"Unclustered chunks ({len(result.unclustered)}):")
        for name in result.unclustered:
            click.echo(f"  - {name}")


# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/chunk_validate - CLI command for chunk validation
# Chunk: docs/chunks/orch_inject_validate - --injectable flag for injection validation
# Chunk: docs/chunks/accept_full_artifact_paths - CLI chunk validate command using strip_artifact_path_prefix
# Chunk: docs/chunks/task_chunk_validation - CLI command with task context detection
@chunk.command()
@click.argument("chunk_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--injectable", is_flag=True, help="Validate for injection into orchestrator work pool")
def validate(chunk_id, project_dir, injectable):
    """Validate chunk is ready for completion (or injection).

    Supports validating chunks in task context, including external chunks
    and cross-project code references.

    With --injectable: validates chunk can be injected into the orchestrator,
    checking status-content consistency (e.g., IMPLEMENTING/ACTIVE status
    requires a populated PLAN.md).
    """
    from task_utils import find_task_directory, is_task_directory

    # Normalize chunk_id to strip path prefixes (if provided)
    if chunk_id is not None:
        chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    # Detect task context
    # If project_dir is a task directory, use it directly
    # Otherwise, try to find a task directory above the project_dir
    task_dir = None
    if is_task_directory(project_dir):
        task_dir = project_dir
    else:
        task_dir = find_task_directory(project_dir)

    # Determine which project directory to use for chunks
    # If we're in a task directory directly, we need to find the external repo
    if task_dir is not None and is_task_directory(project_dir):
        from task_utils import load_task_config, resolve_repo_directory

        try:
            config = load_task_config(task_dir)
            # Use external repo as the primary project for chunk operations
            project_dir = resolve_repo_directory(task_dir, config.external_artifact_repo)
        except (FileNotFoundError, ValueError):
            # Can't resolve external repo, continue with project_dir
            pass

    chunks = Chunks(project_dir)

    # Choose validation mode
    if injectable:
        result = chunks.validate_chunk_injectable(chunk_id)
        success_message = f"Chunk {result.chunk_name} is ready for injection"
    else:
        result = chunks.validate_chunk_complete(chunk_id, task_dir=task_dir)
        success_message = f"Chunk {result.chunk_name} is ready for completion"

    if not result.success:
        for error in result.errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Display warnings (but still succeed)
    for warning in result.warnings:
        click.echo(warning, err=True)

    click.echo(success_message)


# Chunk: docs/chunks/cluster_rename - CLI command for batch chunk renaming
@chunk.command("cluster-rename")
@click.argument("old_prefix")
@click.argument("new_prefix")
@click.option("--execute", is_flag=True, help="Apply changes (default is dry-run)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def cluster_rename_cmd(old_prefix, new_prefix, execute, project_dir):
    """Rename all chunks matching OLD_PREFIX_ to NEW_PREFIX_.

    By default, shows what would change without making modifications.
    Use --execute to apply the changes.

    Examples:

        ve chunk cluster-rename task chunk_task

        ve chunk cluster-rename old_name new_name --execute
    """
    from cluster_rename import cluster_rename, format_dry_run_output

    try:
        result = cluster_rename(project_dir, old_prefix, new_prefix, execute=execute)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    preview = result.preview

    # Informative warning if git working tree is dirty
    if result.git_dirty:
        click.echo("Note: Git working tree has uncommitted changes.", err=True)
        click.echo("")

    # Format and display output
    output = format_dry_run_output(preview, project_dir)
    click.echo(output)

    # Summary
    num_dirs = len(preview.directories)
    num_frontmatter = len(preview.frontmatter_updates)
    num_backrefs = len(preview.backreference_updates)
    num_prose = len(preview.prose_references)

    if execute:
        click.echo("")
        click.echo(f"Renamed {num_dirs} directories")
        click.echo(f"Updated {num_frontmatter} frontmatter references")
        click.echo(f"Updated {num_backrefs} code backreferences")
        if num_prose > 0:
            click.echo(f"")
            click.echo(f"NOTE: {num_prose} prose references require manual review (shown above)")
    else:
        click.echo("")
        click.echo(f"Would rename {num_dirs} directories")
        click.echo(f"Would update {num_frontmatter} frontmatter references")
        click.echo(f"Would update {num_backrefs} code backreferences")
        if num_prose > 0:
            click.echo(f"")
            click.echo(f"NOTE: {num_prose} prose references would require manual review")
        click.echo("")
        click.echo("Run with --execute to apply these changes.")


# Chunk: docs/chunks/cluster_list_command - CLI command for cluster analysis
@chunk.command("cluster-list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--suggest-merges", is_flag=True, help="Suggest singleton merges based on semantic similarity")
def cluster_list_cmd(project_dir, suggest_merges):
    """List prefix clusters and identify singletons/superclusters.

    Groups chunks by their alphabetical prefix (first word before underscore)
    and categorizes clusters by size:

    \b
    - Superclusters (>8 chunks): Too large, prefix becomes noise
    - Healthy (3-8 chunks): Optimal for filesystem navigation
    - Small (2 chunks): Minimal grouping benefit
    - Singletons (1 chunk): No grouping benefit

    Use --suggest-merges to identify singletons that could be renamed into
    existing clusters based on semantic similarity (uses TF-IDF analysis).

    Examples:

    \b
        ve chunk cluster-list
        ve chunk cluster-list --suggest-merges
    """
    from cluster_analysis import (
        get_chunk_clusters,
        categorize_clusters,
        suggest_singleton_merges,
        format_cluster_output,
    )

    clusters = get_chunk_clusters(project_dir)

    if not clusters:
        click.echo("No chunks found.")
        return

    categories = categorize_clusters(clusters)

    merge_suggestions = None
    if suggest_merges:
        merge_suggestions = suggest_singleton_merges(project_dir, clusters)

    output = format_cluster_output(categories, merge_suggestions)
    click.echo(output)


@cli.group()
def narrative():
    """Narrative commands"""
    pass


# Subsystem: docs/subsystems/workflow_artifacts - Narrative commands
@narrative.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def create_narrative(short_name, project_dir, projects):
    """Create a new narrative.

    In task directory mode, creates narrative in the external artifact repo.
    In single-repo mode, creates narrative in docs/narratives/.
    """
    errors = validate_short_name(short_name)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _start_task_narrative(project_dir, short_name, projects)
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "narrative")

    # Single-repo mode - create in docs/narratives/
    narratives = Narratives(project_dir)

    try:
        narrative_path = narratives.create_narrative(short_name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    relative_path = narrative_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


def _start_task_narrative(
    task_dir: pathlib.Path,
    short_name: str,
    projects_input: str | None = None,
):
    """Handle narrative creation in task directory (cross-repo mode)."""
    # Parse projects option
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = create_task_narrative(task_dir, short_name, projects=projects)
    except TaskNarrativeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_narrative_path"]
    click.echo(f"Created narrative in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the narrative directory, not the yaml file
        narrative_dir = yaml_path.parent
        click.echo(f"  {project_ref}: {narrative_dir.relative_to(task_dir)}/")


# Subsystem: docs/subsystems/workflow_artifacts - Narrative commands
@narrative.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_narratives(project_dir):
    """List all narratives.

    In task directory mode, lists narratives from the external artifact repo.
    In single-repo mode, lists narratives from docs/narratives/.
    """
    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_narratives_cmd(project_dir)
        return

    # Single-repo mode - list from docs/narratives/
    narratives = Narratives(project_dir)
    narrative_list = narratives.enumerate_narratives()

    if not narrative_list:
        click.echo("No narratives found", err=True)
        raise SystemExit(1)

    # Use ArtifactIndex for causal ordering and tip detection
    artifact_index = ArtifactIndex(project_dir)
    ordered = artifact_index.get_ordered(ArtifactType.NARRATIVE)
    tips = set(artifact_index.find_tips(ArtifactType.NARRATIVE))

    # Reverse for newest first (ArtifactIndex returns oldest first)
    for narrative_name in reversed(ordered):
        frontmatter = narratives.parse_narrative_frontmatter(narrative_name)
        status = frontmatter.status.value if frontmatter else "UNKNOWN"
        tip_indicator = " *" if narrative_name in tips else ""
        click.echo(f"docs/narratives/{narrative_name} [{status}]{tip_indicator}")


def _list_task_narratives_cmd(task_dir: pathlib.Path):
    """Handle narrative listing in task directory (cross-repo mode)."""
    try:
        narratives = list_task_narratives(task_dir)
    except TaskNarrativeError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not narratives:
        click.echo("No narratives found", err=True)
        raise SystemExit(1)

    for narrative in narratives:
        click.echo(f"{narrative['name']} [{narrative['status']}]")
        if narrative.get("dependents"):
            for dep in narrative["dependents"]:
                click.echo(f"  → {dep}")


# Subsystem: docs/subsystems/workflow_artifacts - Narrative commands
@narrative.command()
@click.argument("narrative_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(narrative_id, new_status, project_dir):
    """Show or update narrative status."""
    # Normalize narrative_id to strip path prefixes
    if "/" in narrative_id:
        narrative_id = narrative_id.rsplit("/", 1)[-1]

    # Use in-repo Narratives class
    narratives = Narratives(project_dir)

    # Display mode: just show current status
    if new_status is None:
        fm = narratives.parse_narrative_frontmatter(narrative_id)
        if fm is None:
            click.echo(f"Error: Narrative '{narrative_id}' not found", err=True)
            raise SystemExit(1)
        click.echo(f"{narrative_id}: {fm.status.value}")
        return

    # Transition mode: validate and update status
    try:
        new_status_enum = NarrativeStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in NarrativeStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the update
    try:
        old_status, updated_status = narratives.update_status(narrative_id, new_status_enum)
        click.echo(f"{narrative_id}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Subsystem: docs/subsystems/workflow_artifacts - Narrative commands
@narrative.command("compact")
@click.argument("chunk_ids", nargs=-1, required=True)
@click.option("--name", required=True, help="Short name for the consolidated narrative")
@click.option("--description", default="Consolidated narrative", help="Description for the narrative")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def compact(chunk_ids, name, description, project_dir):
    """Consolidate multiple chunks into a single narrative.

    Creates a narrative that references the given chunks.
    The narrative is stored in docs/narratives/ and serves as a
    grouping mechanism for related work.

    Example:
        ve narrative compact chunk_a chunk_b chunk_c --name my_narrative
    """
    import re
    import yaml

    if len(chunk_ids) < 2:
        click.echo("Error: Need at least 2 chunks to consolidate", err=True)
        raise SystemExit(1)

    # Validate chunk IDs exist
    chunks = Chunks(project_dir)
    available_chunks = set(chunks.enumerate_chunks())
    normalized_ids = []

    for chunk_id in chunk_ids:
        # Strip any path prefixes the user might have included
        normalized = chunk_id.rsplit("/", 1)[-1] if "/" in chunk_id else chunk_id
        if normalized not in available_chunks:
            click.echo(f"Error: Chunk '{normalized}' not found in docs/chunks/", err=True)
            raise SystemExit(1)
        normalized_ids.append(normalized)

    # Create the narrative
    narratives = Narratives(project_dir)

    try:
        narrative_path = narratives.create_narrative(name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Update OVERVIEW.md with chunk references
    overview_path = narrative_path / "OVERVIEW.md"
    content = overview_path.read_text()

    # Parse existing frontmatter
    match = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
    if match:
        frontmatter = yaml.safe_load(match.group(2))
        if not isinstance(frontmatter, dict):
            frontmatter = {}

        # Add proposed_chunks listing the consolidated chunks
        frontmatter["proposed_chunks"] = [
            {"prompt": f"Consolidated from {chunk_id}", "chunk_directory": chunk_id}
            for chunk_id in normalized_ids
        ]
        frontmatter["advances_trunk_goal"] = description

        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        rest_of_file = content[match.end():]
        overview_path.write_text(f"---\n{new_frontmatter}---{rest_of_file}")

    relative_path = narrative_path.relative_to(project_dir)
    click.echo(f"Created narrative: {relative_path}")
    click.echo("")
    click.echo(f"Consolidated {len(normalized_ids)} chunks:")
    for chunk_name in normalized_ids:
        click.echo(f"  - {chunk_name}")


# Subsystem: docs/subsystems/workflow_artifacts - Narrative commands
@narrative.command("update-refs")
@click.argument("narrative_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--dry-run", is_flag=True, help="Show what would be changed without modifying files")
@click.option("--file", "file_path", type=click.Path(exists=True, path_type=pathlib.Path), help="Update only this specific file")
def update_refs(narrative_id, project_dir, dry_run, file_path):
    """Update code backreferences to point to a narrative.

    Finds files containing chunk backreferences for chunks consolidated into
    the specified narrative and replaces them with a single narrative reference.

    Example:
        ve narrative update-refs my_narrative
        ve narrative update-refs my_narrative --dry-run
    """
    from chunks import update_backreferences, count_backreferences

    # Normalize narrative_id
    narrative_id = strip_artifact_path_prefix(narrative_id, ArtifactType.NARRATIVE)

    narratives = Narratives(project_dir)

    # Parse narrative frontmatter to get consolidated chunk IDs
    frontmatter = narratives.parse_narrative_frontmatter(narrative_id)
    if frontmatter is None:
        click.echo(f"Error: Narrative '{narrative_id}' not found", err=True)
        raise SystemExit(1)

    # Get chunk IDs from proposed_chunks
    chunk_ids = []
    for proposed in frontmatter.proposed_chunks:
        if proposed.chunk_directory:
            chunk_ids.append(proposed.chunk_directory)

    if not chunk_ids:
        click.echo(f"Narrative '{narrative_id}' has no consolidated chunks")
        return

    # Find files with backreferences to these chunks
    backref_results = count_backreferences(project_dir)
    files_to_process = []

    for info in backref_results:
        # Check if this file has any of our target chunk refs
        matching_refs = [ref for ref in set(info.chunk_refs) if ref in chunk_ids]
        if matching_refs:
            if file_path is None or info.file_path == file_path:
                files_to_process.append((info.file_path, matching_refs))

    if not files_to_process:
        click.echo("No files found with backreferences to update")
        return

    total_replaced = 0
    files_updated = []

    for fpath, refs in files_to_process:
        count = update_backreferences(
            project_dir,
            file_path=fpath,
            chunk_ids_to_replace=refs,
            narrative_id=narrative_id,
            narrative_description=frontmatter.advances_trunk_goal or "Consolidated narrative",
            dry_run=dry_run,
        )
        if count > 0:
            total_replaced += count
            rel_path = fpath.relative_to(project_dir)
            files_updated.append((rel_path, count))

    if dry_run:
        click.echo("Dry run - no files modified")
        click.echo("")
        click.echo(f"Would update {len(files_updated)} file(s):")
        for rel_path, count in files_updated:
            click.echo(f"  - {rel_path}: {count} chunk refs -> 1 narrative ref")
    else:
        click.echo(f"Updated backreferences in {len(files_updated)} file(s):")
        for rel_path, count in files_updated:
            click.echo(f"  - {rel_path}: replaced {count} chunk refs with 1 narrative ref")


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


def _list_task_subsystems(task_dir: pathlib.Path):
    """Handle subsystem listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.SUBSYSTEM)
        _format_grouped_artifact_list(grouped_data, "subsystems")
    except (TaskSubsystemError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@subsystem.command()
@click.argument("shortname")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def discover(shortname, project_dir, projects):
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
        _create_task_subsystem(project_dir, shortname, projects)
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "subsystem")

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


def _create_task_subsystem(task_dir: pathlib.Path, short_name: str, projects_input: str | None = None):
    """Handle subsystem creation in task directory (cross-repo mode)."""
    # Parse and validate projects option
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = create_task_subsystem(task_dir, short_name, projects=projects)
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


# Chunk: docs/chunks/bidirectional_refs - Subsystem validate CLI command for chunk ref validation
@subsystem.command()
@click.argument("subsystem_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def validate(subsystem_id, project_dir):
    """Validate subsystem frontmatter and chunk references."""
    # Normalize subsystem_id to strip path prefixes
    subsystem_id = strip_artifact_path_prefix(subsystem_id, ArtifactType.SUBSYSTEM)

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
    # Normalize subsystem_id to strip path prefixes
    subsystem_id = strip_artifact_path_prefix(subsystem_id, ArtifactType.SUBSYSTEM)

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
    """Find subsystems with code references overlapping a chunk's changes.

    When run in task context (directory with .ve-task.yaml), searches for
    the chunk across the external repo and all project repos, then checks
    for overlapping subsystems in the same repo where the chunk was found.
    """
    from task_utils import (
        is_task_directory,
        find_task_directory,
        load_task_config,
        resolve_repo_directory,
    )

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    # Detect task context
    task_dir = None
    if is_task_directory(project_dir):
        task_dir = project_dir
    else:
        task_dir = find_task_directory(project_dir)

    if task_dir is not None:
        # Task context: resolve chunk across external and project repos
        try:
            config = load_task_config(task_dir)
        except FileNotFoundError:
            click.echo(
                f"Error: Task configuration not found. Expected .ve-task.yaml in {task_dir}",
                err=True
            )
            raise SystemExit(1)

        # Resolve external repo path
        try:
            external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
        except FileNotFoundError:
            click.echo(
                f"Error: External repository '{config.external_artifact_repo}' not found or not accessible",
                err=True
            )
            raise SystemExit(1)

        # Find the target chunk (could be in external repo or a project)
        target_chunks = None
        target_chunk_name = None
        target_project_path = None

        # First try external repo
        external_chunks = Chunks(external_repo_path)
        resolved = external_chunks.resolve_chunk_id(chunk_id)
        if resolved is not None:
            target_chunks = external_chunks
            target_chunk_name = resolved
            target_project_path = external_repo_path
        else:
            # Try project repos
            for project_ref in config.projects:
                try:
                    project_path = resolve_repo_directory(task_dir, project_ref)
                    project_chunks = Chunks(project_path)
                    resolved = project_chunks.resolve_chunk_id(chunk_id)
                    if resolved is not None:
                        target_chunks = project_chunks
                        target_chunk_name = resolved
                        target_project_path = project_path
                        break
                except FileNotFoundError:
                    continue

        if target_chunks is None:
            click.echo(f"Error: Chunk '{chunk_id}' not found in any task repository", err=True)
            raise SystemExit(1)

        # Create subsystems instance for the same repo where chunk was found
        target_subsystems = Subsystems(target_project_path)

        try:
            overlapping = target_subsystems.find_overlapping_subsystems(target_chunk_name, target_chunks)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        for item in overlapping:
            click.echo(f"docs/subsystems/{item['subsystem_id']} [{item['status']}]")
    else:
        # Single repo context - existing behavior
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
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def create_investigation(short_name, project_dir, projects):
    """Create a new investigation."""
    errors = validate_short_name(short_name)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _create_task_investigation(project_dir, short_name, projects)
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "investigation")

    # Single-repo mode
    investigations = Investigations(project_dir)
    investigation_path = investigations.create_investigation(short_name)

    # Show path relative to project_dir
    relative_path = investigation_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


def _create_task_investigation(task_dir: pathlib.Path, short_name: str, projects_input: str | None = None):
    """Handle investigation creation in task directory (cross-repo mode)."""
    # Parse and validate projects option
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = create_task_investigation(task_dir, short_name, projects=projects)
    except TaskInvestigationError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_investigation_path"]
    click.echo(f"Created investigation in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the investigation directory, not the yaml file
        investigation_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {investigation_dir.relative_to(task_dir)}/")


@investigation.command("list")
@click.option("--state", type=str, default=None, help="Filter by investigation state")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def list_investigations(state, project_dir):
    """List all investigations."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    # Check if we're in a task directory (cross-repo mode)
    if is_task_directory(project_dir):
        _list_task_investigations(project_dir)
        return

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


def _list_task_investigations(task_dir: pathlib.Path):
    """Handle investigation listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.INVESTIGATION)
        _format_grouped_artifact_list(grouped_data, "investigations")
    except (TaskInvestigationError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@investigation.command()
@click.argument("investigation_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(investigation_id, new_status, project_dir):
    """Show or update investigation status."""
    from models import extract_short_name

    # Normalize investigation_id to strip path prefixes
    investigation_id = strip_artifact_path_prefix(investigation_id, ArtifactType.INVESTIGATION)

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


@cli.group()
def external():
    """External artifact reference commands."""
    pass


@external.command()
@click.argument("local_artifact_id")
@click.option("--main-only", is_flag=True, help="Show only main file content (GOAL.md for chunks, OVERVIEW.md for others)")
@click.option("--secondary-only", is_flag=True, help="Show only secondary file content (PLAN.md for chunks only)")
@click.option("--goal-only", is_flag=True, hidden=True, help="Alias for --main-only (backward compatibility)")
@click.option("--plan-only", is_flag=True, hidden=True, help="Alias for --secondary-only (backward compatibility)")
@click.option("--project", type=str, default=None, help="Specify project for disambiguation (task directory only)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def resolve(local_artifact_id, main_only, secondary_only, goal_only, plan_only, project, project_dir):
    """Display external artifact content.

    Resolves an external artifact reference and displays its content.
    Auto-detects artifact type from the path (chunks, narratives, investigations, subsystems).

    For chunks: displays GOAL.md and PLAN.md
    For other types: displays OVERVIEW.md

    Works in both task directory mode (using local worktrees) and single repo mode
    (using the repo cache). Always resolves to the current HEAD of the external repo.
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
            project_dir, local_artifact_id, main_only, secondary_only, project
        )
    else:
        if project:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _resolve_external_single_repo(
            project_dir, local_artifact_id, main_only, secondary_only
        )


# Chunk: docs/chunks/accept_full_artifact_paths - Artifact type detection using normalize_artifact_path
def _detect_artifact_type_from_id(project_path: pathlib.Path, local_artifact_id: str) -> tuple[ArtifactType, str]:
    """Detect artifact type by searching for the artifact in project directories.

    Also normalizes the artifact ID by stripping path prefixes if present.

    Args:
        project_path: Path to the project directory
        local_artifact_id: Local artifact ID to find (can include path prefixes)

    Returns:
        Tuple of (ArtifactType, normalized_artifact_id)

    Raises:
        TaskChunkError: If artifact is not found in any artifact directory
    """
    from external_refs import ARTIFACT_DIR_NAME, normalize_artifact_path

    # First try to normalize using path-based detection
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            local_artifact_id,
            search_path=project_path,
        )
        # Verify the artifact exists
        artifact_dir = project_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
        if artifact_dir.exists():
            return (artifact_type, artifact_id)
    except ValueError:
        # Fall through to legacy search
        pass

    # Legacy search: search all artifact directories
    for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
        artifacts_dir = project_path / "docs" / dir_name
        if not artifacts_dir.exists():
            continue
        for artifact_dir in artifacts_dir.iterdir():
            if artifact_dir.is_dir():
                if artifact_dir.name == local_artifact_id or artifact_dir.name.startswith(f"{local_artifact_id}-"):
                    return (artifact_type, artifact_dir.name)

    raise TaskChunkError(f"Artifact '{local_artifact_id}' not found in any artifact directory")


def _resolve_external_task_directory(
    task_dir: pathlib.Path,
    local_artifact_id: str,
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
    resolved_artifact_id = local_artifact_id
    for project_ref in projects_to_search:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            artifact_type, resolved_artifact_id = _detect_artifact_type_from_id(project_path, local_artifact_id)
            break
        except (FileNotFoundError, TaskChunkError):
            continue

    if artifact_type is None:
        click.echo(f"Error: Artifact '{local_artifact_id}' not found", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_task_directory(
            task_dir,
            resolved_artifact_id,
            artifact_type,
            project_filter=project_filter,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


def _resolve_external_single_repo(
    repo_path: pathlib.Path,
    local_artifact_id: str,
    main_only: bool,
    secondary_only: bool,
):
    """Handle resolve in single repo mode."""
    # Detect artifact type from the repo
    try:
        artifact_type, resolved_artifact_id = _detect_artifact_type_from_id(repo_path, local_artifact_id)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_single_repo(
            repo_path,
            resolved_artifact_id,
            artifact_type,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


def _display_resolve_result(result: ResolveResult, main_only: bool, secondary_only: bool):
    """Display the resolve result to the user."""
    # Determine file names based on artifact type
    main_file = ARTIFACT_MAIN_FILE[result.artifact_type]
    secondary_file = "PLAN.md" if result.artifact_type == ArtifactType.CHUNK else None

    # Header with metadata (new format)
    artifact_type_display = result.artifact_type.value
    click.echo(f"Artifact: {result.artifact_id} ({artifact_type_display})")
    click.echo(f"Context: {result.context_mode}")
    if result.local_path:
        click.echo(f"Path: {result.local_path}")

    # Directory contents
    if result.directory_contents:
        click.echo("Contents:")
        for filename in result.directory_contents:
            click.echo(f"  {filename}")

    click.echo("")

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


@cli.group()
def artifact():
    """Artifact management commands."""
    pass


# Chunk: docs/chunks/artifact_promote - CLI command ve artifact promote <path> [--name]
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
    from task_utils import remove_artifact_from_external, TaskRemoveExternalError

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


@cli.group()
def orch():
    """Orchestrator daemon commands."""
    pass


@orch.command()
@click.option("--port", type=int, default=0, help="TCP port for dashboard (0 = auto-select)")
@click.option("--host", type=str, default="127.0.0.1", help="Host to bind TCP server to")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def start(port, host, project_dir):
    """Start the orchestrator daemon."""
    from orchestrator.daemon import start_daemon, DaemonError

    try:
        pid, actual_port = start_daemon(project_dir, port=port, host=host)
        click.echo(f"Orchestrator daemon started (PID {pid})")
        click.echo(f"Dashboard available at http://{host}:{actual_port}/")
    except DaemonError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@orch.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def stop(project_dir):
    """Stop the orchestrator daemon."""
    from orchestrator.daemon import stop_daemon, DaemonError

    try:
        stopped = stop_daemon(project_dir)
        if stopped:
            click.echo("Orchestrator daemon stopped")
        else:
            click.echo("Orchestrator daemon is not running")
    except DaemonError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@orch.command("status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_status(json_output, project_dir):
    """Show orchestrator daemon status."""
    from orchestrator.daemon import get_daemon_status
    import json

    state = get_daemon_status(project_dir)

    if json_output:
        click.echo(json.dumps(state.model_dump_json_serializable(), indent=2))
    else:
        if state.running:
            click.echo(f"Status: Running")
            click.echo(f"PID: {state.pid}")
            if state.uptime_seconds is not None:
                # Format uptime nicely
                uptime = state.uptime_seconds
                if uptime < 60:
                    uptime_str = f"{uptime:.0f}s"
                elif uptime < 3600:
                    uptime_str = f"{uptime / 60:.0f}m"
                else:
                    uptime_str = f"{uptime / 3600:.1f}h"
                click.echo(f"Uptime: {uptime_str}")
            if state.work_unit_counts:
                click.echo("Work Units:")
                for status, count in sorted(state.work_unit_counts.items()):
                    click.echo(f"  {status}: {count}")
        else:
            click.echo("Status: Stopped")


@orch.command("url")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_url(json_output, project_dir):
    """Print the orchestrator dashboard URL."""
    from orchestrator.daemon import is_daemon_running, get_daemon_url
    import json

    # Check if daemon is running
    if not is_daemon_running(project_dir):
        click.echo("Error: Orchestrator is not running.")
        click.echo("Start it with: ve orch start")
        raise SystemExit(1)

    # Get the URL
    url = get_daemon_url(project_dir)
    if url is None:
        click.echo("Error: Could not read daemon port file.")
        click.echo("The daemon may be running but the port file is missing.")
        raise SystemExit(1)

    if json_output:
        click.echo(json.dumps({"url": url}))
    else:
        click.echo(url)


@orch.command("ps")
@click.option("--status", "status_filter", type=str, help="Filter by status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_ps(status_filter, json_output, project_dir):
    """List all work units (alias for work-unit list)."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.list_work_units(status=status_filter)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            units = result["work_units"]
            if not units:
                click.echo("No work units")
                return

            # Check if any unit needs attention with a reason
            has_attention_reason = any(
                unit.get("status") == "NEEDS_ATTENTION" and unit.get("attention_reason")
                for unit in units
            )

            # Display table - include REASON column if any NEEDS_ATTENTION units have reasons
            if has_attention_reason:
                click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'STATUS':<16} {'REASON':<32} {'BLOCKED BY'}")
                click.echo("-" * 110)
            else:
                click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'STATUS':<16} {'BLOCKED BY'}")
                click.echo("-" * 80)

            for unit in units:
                blocked = ", ".join(unit["blocked_by"]) if unit["blocked_by"] else "-"
                if has_attention_reason:
                    reason = unit.get("attention_reason") or "-"
                    # Truncate reason to 30 chars
                    if len(reason) > 30:
                        reason = reason[:27] + "..."
                    click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['status']:<16} {reason:<32} {blocked}")
                else:
                    click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['status']:<16} {blocked}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.group("work-unit")
def work_unit():
    """Work unit management commands."""
    pass


@work_unit.command("create")
@click.argument("chunk")
@click.option("--phase", default="GOAL", help="Initial phase (GOAL, PLAN, IMPLEMENT, COMPLETE)")
@click.option("--status", "init_status", default="READY", help="Initial status")
@click.option("--blocked-by", multiple=True, help="Chunks this is blocked by")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_create(chunk, phase, init_status, blocked_by, json_output, project_dir):
    """Create a new work unit for a chunk."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.create_work_unit(
            chunk=chunk,
            phase=phase,
            status=init_status,
            blocked_by=list(blocked_by) if blocked_by else None,
        )

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Created work unit: {result['chunk']} [{result['phase']}] {result['status']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("status")
@click.argument("chunk")
@click.argument("new_status", required=False, default=None)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_status(chunk, new_status, json_output, project_dir):
    """Show or update work unit status."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if new_status is None:
            # Show current status
            result = client.get_work_unit(chunk)
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"{result['chunk']}: [{result['phase']}] {result['status']}")
        else:
            # Update status
            old = client.get_work_unit(chunk)
            result = client.update_work_unit(chunk, status=new_status)
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"{chunk}: {old['status']} -> {result['status']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("show")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_show(chunk, json_output, project_dir):
    """Show detailed work unit information including attention reason."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    client = create_client(project_dir)
    try:
        result = client.get_work_unit(chunk)

        if json_output:
            click.echo(json_module.dumps(result, indent=2))
        else:
            click.echo(f"Chunk:            {result['chunk']}")
            click.echo(f"Phase:            {result['phase']}")
            click.echo(f"Status:           {result['status']}")
            click.echo(f"Priority:         {result['priority']}")
            if result.get('blocked_by'):
                click.echo(f"Blocked By:       {', '.join(result['blocked_by'])}")
            if result.get('worktree'):
                click.echo(f"Worktree:         {result['worktree']}")
            if result.get('session_id'):
                click.echo(f"Session ID:       {result['session_id']}")
            if result.get('attention_reason'):
                click.echo(f"Attention Reason: {result['attention_reason']}")
            click.echo(f"Created At:       {result['created_at']}")
            click.echo(f"Updated At:       {result['updated_at']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@work_unit.command("list")
@click.option("--status", "status_filter", type=str, help="Filter by status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_list(status_filter, json_output, project_dir):
    """List all work units."""
    # Delegate to orch ps
    from click import Context
    ctx = click.get_current_context()
    ctx.invoke(orch_ps, status_filter=status_filter, json_output=json_output, project_dir=project_dir)


@work_unit.command("delete")
@click.argument("chunk")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def work_unit_delete(chunk, json_output, project_dir):
    """Delete a work unit."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.delete_work_unit(chunk)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Deleted work unit: {chunk}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


def topological_sort_chunks(
    chunks: list[str],
    dependencies: dict[str, list[str] | None],
) -> list[str]:
    """Sort chunks by dependency order (dependencies first).

    Uses Kahn's algorithm for topological sorting.

    Args:
        chunks: List of chunk names to sort
        dependencies: Maps chunk name -> list of chunk names it depends on (or None if unknown)

    Returns:
        Chunks in topological order (dependencies before dependents)

    Raises:
        ValueError: If a dependency cycle is detected
    """
    # Build in-degree map (count of dependencies within the batch for each chunk)
    in_degree: dict[str, int] = {chunk: 0 for chunk in chunks}
    batch_set = set(chunks)

    # Only count dependencies that are in the batch (treat None as empty list for sorting)
    for chunk in chunks:
        deps = dependencies.get(chunk) or []
        for dep in deps:
            if dep in batch_set:
                in_degree[chunk] += 1

    # Start with chunks that have no in-batch dependencies
    queue = [chunk for chunk in chunks if in_degree[chunk] == 0]
    result: list[str] = []

    while queue:
        # Sort for deterministic ordering
        queue.sort()
        current = queue.pop(0)
        result.append(current)

        # Reduce in-degree for chunks that depend on current
        for chunk in chunks:
            deps = dependencies.get(chunk) or []
            if current in deps:
                in_degree[chunk] -= 1
                if in_degree[chunk] == 0:
                    queue.append(chunk)

    # If we haven't processed all chunks, there's a cycle
    if len(result) != len(chunks):
        # Find the cycle for error message
        remaining = [c for c in chunks if c not in result]
        # Build a simple cycle representation
        cycle_parts = []
        visited = set()
        current = remaining[0]
        while current not in visited:
            visited.add(current)
            cycle_parts.append(current)
            # Find next node in cycle
            deps = dependencies.get(current) or []
            for dep in deps:
                if dep in remaining:
                    current = dep
                    break
        cycle_parts.append(current)  # Complete the cycle
        cycle_str = " -> ".join(cycle_parts)
        raise ValueError(f"Dependency cycle detected: {cycle_str}")

    return result


def read_chunk_dependencies(project_dir: pathlib.Path, chunk_names: list[str]) -> dict[str, list[str] | None]:
    """Read depends_on from chunk frontmatter for all specified chunks.

    Args:
        project_dir: Project directory
        chunk_names: List of chunk names to read

    Returns:
        Dict mapping chunk name -> list of depends_on chunk names, or None if unknown.

        The distinction between None and [] is semantically significant:
        - None: Dependencies unknown (consult oracle)
        - []: Explicitly no dependencies (bypass oracle)
        - ["chunk_a", ...]: Explicit dependencies (bypass oracle)
    """
    from chunks import Chunks

    chunks_manager = Chunks(project_dir)
    dependencies: dict[str, list[str] | None] = {}

    for chunk_name in chunk_names:
        frontmatter = chunks_manager.parse_chunk_frontmatter(chunk_name)
        if frontmatter is not None:
            # Preserve None vs [] distinction from frontmatter
            dependencies[chunk_name] = frontmatter.depends_on
        else:
            # No frontmatter means unknown dependencies
            dependencies[chunk_name] = None

    return dependencies


def validate_external_dependencies(
    client,
    batch_chunks: set[str],
    dependencies: dict[str, list[str] | None],
) -> list[str]:
    """Validate that dependencies outside the batch exist as work units.

    Args:
        client: Orchestrator client for querying existing work units
        batch_chunks: Set of chunk names in the current batch
        dependencies: Maps chunk name -> list of depends_on chunk names (or None if unknown)

    Returns:
        List of error messages (empty if all external deps exist)
    """
    # Collect all external dependencies (skip None values - those have unknown deps)
    external_deps: set[str] = set()
    for chunk, deps in dependencies.items():
        if deps is not None:
            for dep in deps:
                if dep not in batch_chunks:
                    external_deps.add(dep)

    if not external_deps:
        return []

    # Query existing work units
    try:
        result = client._request("GET", "/work-units")
        existing_chunks = {wu["chunk"] for wu in result.get("work_units", [])}
    except Exception:
        existing_chunks = set()

    # Check which external deps are missing
    errors: list[str] = []
    for dep in external_deps:
        if dep not in existing_chunks:
            # Find which chunk(s) depend on this missing dep (skip None values)
            dependents = [c for c, d in dependencies.items() if d is not None and dep in d]
            for dependent in dependents:
                errors.append(
                    f"Chunk '{dependent}' depends on '{dep}' which is not in this batch "
                    "and not an existing work unit"
                )

    return errors


@orch.command("inject")
@click.argument("chunks", nargs=-1, required=True)
@click.option("--phase", type=str, default=None, help="Override initial phase (GOAL, PLAN, IMPLEMENT)")
@click.option("--priority", type=int, default=0, help="Scheduling priority (higher = more urgent)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_inject(chunks, phase, priority, json_output, project_dir):
    """Inject one or more chunks into the orchestrator work pool.

    Accepts multiple chunk arguments: ve orch inject chunk_a chunk_b chunk_c

    When multiple chunks are provided, they are topologically sorted by their
    depends_on declarations and injected in dependency order (dependencies first).
    Chunks with non-empty depends_on have their work units created with blocked_by
    populated and explicit_deps=True.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json as json_module

    # Strip artifact path prefixes from all chunks
    chunk_list = [strip_artifact_path_prefix(c, ArtifactType.CHUNK) for c in chunks]
    batch_chunks = set(chunk_list)

    client = create_client(project_dir)
    try:
        # Read dependencies from all chunks
        if len(chunk_list) > 1 and not json_output:
            click.echo(f"Reading dependencies for {len(chunk_list)} chunks...")

        dependencies = read_chunk_dependencies(project_dir, chunk_list)

        # Validate external dependencies exist as work units
        errors = validate_external_dependencies(client, batch_chunks, dependencies)
        if errors:
            for error in errors:
                click.echo(f"Error: {error}", err=True)
            raise SystemExit(1)

        # Topologically sort chunks
        try:
            sorted_chunks = topological_sort_chunks(chunk_list, dependencies)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        # Inject in order
        results: list[dict] = []
        for chunk in sorted_chunks:
            deps = dependencies.get(chunk)
            body = {"chunk": chunk, "priority": priority}
            if phase:
                body["phase"] = phase

            # Set blocked_by and explicit_deps based on depends_on value
            # - None: Dependencies unknown (consult oracle) -> explicit_deps omitted/False
            # - []: Explicitly no dependencies (bypass oracle) -> explicit_deps=True
            # - ["chunk_a", ...]: Explicit dependencies -> explicit_deps=True, blocked_by set
            if deps is not None:
                # deps is a list (empty or non-empty) - explicit declaration
                body["explicit_deps"] = True
                if deps:
                    body["blocked_by"] = deps
            # else: deps is None - unknown, oracle will be consulted (no explicit_deps)

            result = client._request("POST", "/work-units/inject", json=body)
            results.append(result)

            if not json_output:
                blocked_info = ""
                if deps:
                    blocked_info = f" blocked_by={deps}"
                priority_info = f" priority={result.get('priority', priority)}"
                click.echo(
                    f"Injected: {result['chunk']} [{result['phase']}]{priority_info}{blocked_info}"
                )

        # Final output
        if json_output:
            click.echo(json_module.dumps({"results": results}, indent=2))
        elif len(chunk_list) > 1:
            click.echo(f"Injected {len(results)} chunks in dependency order")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("queue")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_queue(json_output, project_dir):
    """Show ready queue ordered by priority."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client._request("GET", "/work-units/queue")

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            units = result["work_units"]
            if not units:
                click.echo("Ready queue is empty")
                return

            # Display table
            click.echo(f"{'CHUNK':<30} {'PHASE':<12} {'PRIORITY':<10}")
            click.echo("-" * 52)
            for unit in units:
                click.echo(f"{unit['chunk']:<30} {unit['phase']:<12} {unit['priority']:<10}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("prioritize")
@click.argument("chunk")
@click.argument("priority", type=int)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_prioritize(chunk, priority, json_output, project_dir):
    """Set priority for a work unit."""
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client._request(
            "PATCH",
            f"/work-units/{chunk}/priority",
            json={"priority": priority},
        )

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"{chunk}: priority set to {result['priority']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("config")
@click.option("--max-agents", type=int, help="Maximum concurrent agents")
@click.option("--dispatch-interval", type=float, help="Dispatch interval in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_config(max_agents, dispatch_interval, json_output, project_dir):
    """Get or set orchestrator configuration.

    If no options are provided, shows current configuration.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if max_agents is None and dispatch_interval is None:
            # Get config
            result = client._request("GET", "/config")
        else:
            # Update config
            body = {}
            if max_agents is not None:
                body["max_agents"] = max_agents
            if dispatch_interval is not None:
                body["dispatch_interval_seconds"] = dispatch_interval

            result = client._request("PATCH", "/config", json=body)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo("Orchestrator Configuration:")
            click.echo(f"  max_agents: {result['max_agents']}")
            click.echo(f"  dispatch_interval_seconds: {result['dispatch_interval_seconds']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("attention")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_attention(json_output, project_dir):
    """Show attention queue of work units needing operator input.

    Lists NEEDS_ATTENTION work units in priority order:
    - Higher blocked count = higher priority (unblocks more work)
    - Older items surface first among equal priority
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.get_attention_queue()

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            items = result["attention_items"]
            if not items:
                click.echo("No work units need attention")
                return

            click.echo(f"ATTENTION QUEUE ({len(items)} items)")
            click.echo("─" * 60)

            for i, item in enumerate(items, 1):
                chunk = item["chunk"]
                phase = item["phase"]
                blocks = item["blocks_count"]

                # Format time waiting
                time_waiting = item["time_waiting"]
                if time_waiting < 60:
                    time_str = f"{time_waiting:.0f}s"
                elif time_waiting < 3600:
                    time_str = f"{time_waiting / 60:.0f}m"
                else:
                    time_str = f"{time_waiting / 3600:.1f}h"

                click.echo(f"[{i}] {chunk}  {phase}  blocks:{blocks}  waiting:{time_str}")

                # Show attention reason
                reason = item.get("attention_reason")
                if reason:
                    # Truncate long reasons for display
                    if len(reason) > 70:
                        reason = reason[:67] + "..."
                    click.echo(f"    {reason}")

                # Show goal summary if available
                goal_summary = item.get("goal_summary")
                if goal_summary:
                    # Truncate for display
                    if len(goal_summary) > 70:
                        goal_summary = goal_summary[:67] + "..."
                    click.echo(f"    Goal: {goal_summary}")

                click.echo("")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("answer")
@click.argument("chunk")
@click.argument("answer")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_answer(chunk, answer, json_output, project_dir):
    """Answer a question from a NEEDS_ATTENTION work unit.

    Submits the answer and transitions the work unit to READY,
    allowing the scheduler to resume the agent with the answer injected.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        result = client.answer_work_unit(chunk, answer)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Answered {chunk}, work unit queued for resume")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()




@orch.command("conflicts")
@click.argument("chunk", required=False)
@click.option("--unresolved", is_flag=True, help="Show only ASK_OPERATOR verdicts")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_conflicts(chunk, unresolved, json_output, project_dir):
    """Show conflict analyses for chunks.

    If CHUNK is provided, shows conflicts for that specific chunk.
    Otherwise, shows all conflicts.

    Use --unresolved to filter to only ASK_OPERATOR verdicts that need resolution.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    client = create_client(project_dir)
    try:
        if chunk:
            result = client.get_conflicts(chunk)
            conflicts = result.get("conflicts", [])
        else:
            verdict_filter = "ASK_OPERATOR" if unresolved else None
            result = client.list_all_conflicts(verdict=verdict_filter)
            conflicts = result.get("conflicts", [])

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            if not conflicts:
                if unresolved:
                    click.echo("No unresolved conflicts")
                elif chunk:
                    click.echo(f"No conflicts for {chunk}")
                else:
                    click.echo("No conflicts found")
                return

            # Display conflicts
            click.echo(f"{'CHUNK A':<25} {'CHUNK B':<25} {'VERDICT':<15} {'CONFIDENCE':<12} {'STAGE'}")
            click.echo("-" * 90)

            for c in conflicts:
                chunk_a = c["chunk_a"]
                chunk_b = c["chunk_b"]
                verdict = c["verdict"]
                confidence = f"{c['confidence']:.2f}"
                stage = c["analysis_stage"]

                click.echo(f"{chunk_a:<25} {chunk_b:<25} {verdict:<15} {confidence:<12} {stage}")

                # Show overlapping files/symbols if present
                if c.get("overlapping_files"):
                    files = ", ".join(c["overlapping_files"][:3])
                    click.echo(f"  Files: {files}")
                if c.get("overlapping_symbols"):
                    symbols = ", ".join(c["overlapping_symbols"][:3])
                    click.echo(f"  Symbols: {symbols}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("resolve")
@click.argument("chunk")
@click.option("--with", "other_chunk", required=True, help="The other chunk in the conflict")
@click.argument("verdict", type=click.Choice(["parallelize", "serialize"]))
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_resolve(chunk, other_chunk, verdict, json_output, project_dir):
    """Resolve an ASK_OPERATOR conflict between two chunks.

    CHUNK is the work unit to update.
    VERDICT is either 'parallelize' (chunks can run together) or 'serialize' (must run sequentially).

    Example:
        ve orch resolve my_chunk --with other_chunk serialize
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    # Normalize chunk path
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)
    other_chunk = strip_artifact_path_prefix(other_chunk, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        result = client.resolve_conflict(chunk, other_chunk, verdict)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            resolved_verdict = result.get("verdict", verdict)
            click.echo(f"Resolved: {chunk} vs {other_chunk} -> {resolved_verdict}")
            if result.get("blocked_by"):
                click.echo(f"  Blocked by: {', '.join(result['blocked_by'])}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("analyze")
@click.argument("chunk_a")
@click.argument("chunk_b")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_analyze(chunk_a, chunk_b, json_output, project_dir):
    """Analyze potential conflict between two chunks.

    Triggers the conflict oracle to analyze whether CHUNK_A and CHUNK_B
    can be safely parallelized or require serialization.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    # Normalize chunk paths
    chunk_a = strip_artifact_path_prefix(chunk_a, ArtifactType.CHUNK)
    chunk_b = strip_artifact_path_prefix(chunk_b, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        result = client.analyze_conflicts(chunk_a, chunk_b)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            verdict = result.get("verdict", "UNKNOWN")
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")
            stage = result.get("analysis_stage", "UNKNOWN")

            click.echo(f"Conflict Analysis: {chunk_a} vs {chunk_b}")
            click.echo(f"  Verdict:    {verdict}")
            click.echo(f"  Confidence: {confidence:.2f}")
            click.echo(f"  Stage:      {stage}")
            click.echo(f"  Reason:     {reason}")

            if result.get("overlapping_files"):
                click.echo(f"  Files:      {', '.join(result['overlapping_files'])}")
            if result.get("overlapping_symbols"):
                click.echo(f"  Symbols:    {', '.join(result['overlapping_symbols'])}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


@orch.command("tail")
@click.argument("chunk")
@click.option("-f", "--follow", is_flag=True, help="Follow log output in real-time")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_tail(chunk, follow, project_dir):
    """Stream log output for an orchestrator work unit.

    Displays parsed, human-readable log output for CHUNK. Shows tool calls,
    tool results, and assistant messages in a condensed format.

    Use -f to follow the log in real-time as the agent works.
    """
    import time
    from orchestrator.log_parser import (
        parse_log_file,
        format_entry,
        format_phase_header,
    )
    from orchestrator.models import WorkUnitPhase

    # Normalize chunk path
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)

    # Get log directory - compute directly without WorktreeManager to avoid git requirement
    log_dir = project_dir / ".ve" / "chunks" / chunk / "log"

    # Check if chunk directory exists
    chunk_dir = project_dir / "docs" / "chunks" / chunk
    if not chunk_dir.exists():
        click.echo(f"Error: Chunk '{chunk}' not found", err=True)
        raise SystemExit(1)

    # Check if log directory exists
    if not log_dir.exists():
        click.echo(f"No logs yet for chunk '{chunk}'. The work unit may not have started.", err=True)
        raise SystemExit(1)

    # Phase order for iteration
    phase_order = [
        WorkUnitPhase.GOAL,
        WorkUnitPhase.PLAN,
        WorkUnitPhase.IMPLEMENT,
        WorkUnitPhase.REVIEW,
        WorkUnitPhase.COMPLETE,
    ]

    def get_phase_log_files() -> list[tuple[WorkUnitPhase, pathlib.Path]]:
        """Get list of existing phase log files in order."""
        result = []
        for phase in phase_order:
            log_file = log_dir / f"{phase.value.lower()}.txt"
            if log_file.exists():
                result.append((phase, log_file))
        return result

    def display_phase_log(phase: WorkUnitPhase, log_file: pathlib.Path, show_header: bool = True):
        """Display a phase log file."""
        entries = parse_log_file(log_file)
        if not entries:
            return

        # Show phase header
        if show_header and entries:
            header = format_phase_header(phase.value, entries[0].timestamp)
            click.echo(f"\n{header}\n")

        # Display entries
        for entry in entries:
            lines = format_entry(entry)
            for line in lines:
                click.echo(line)

    # Basic mode: display all existing logs
    phase_logs = get_phase_log_files()

    if not phase_logs:
        click.echo(f"No logs yet for chunk '{chunk}'. The work unit may not have started.", err=True)
        raise SystemExit(1)

    # Display existing phase logs
    for phase, log_file in phase_logs:
        display_phase_log(phase, log_file)

    if not follow:
        return

    # Follow mode: stream new lines
    try:
        current_phase_idx = len(phase_logs) - 1
        current_phase, current_log = phase_logs[current_phase_idx]

        # Track file position
        with open(current_log) as f:
            f.seek(0, 2)  # Seek to end
            file_pos = f.tell()

        while True:
            time.sleep(0.1)  # 100ms polling interval

            # Check for new content in current log
            try:
                with open(current_log) as f:
                    f.seek(file_pos)
                    new_content = f.read()
                    if new_content:
                        file_pos = f.tell()
                        # Parse and display new lines
                        for line in new_content.strip().split("\n"):
                            if line.strip():
                                from orchestrator.log_parser import parse_log_line
                                entry = parse_log_line(line)
                                if entry:
                                    lines = format_entry(entry)
                                    for display_line in lines:
                                        click.echo(display_line)
            except FileNotFoundError:
                pass

            # Check for next phase log file
            next_phase_idx = current_phase_idx + 1
            if next_phase_idx < len(phase_order):
                next_phase = phase_order[next_phase_idx]
                next_log = log_dir / f"{next_phase.value.lower()}.txt"
                if next_log.exists():
                    # New phase started
                    current_phase_idx = next_phase_idx
                    current_phase = next_phase
                    current_log = next_log

                    # Show phase header
                    entries = parse_log_file(next_log)
                    if entries:
                        header = format_phase_header(next_phase.value, entries[0].timestamp)
                        click.echo(f"\n{header}\n")

                    # Display any content already in the file
                    for entry in entries:
                        lines = format_entry(entry)
                        for line in lines:
                            click.echo(line)

                    # Update file position
                    with open(current_log) as f:
                        f.seek(0, 2)
                        file_pos = f.tell()

    except KeyboardInterrupt:
        click.echo("\n")  # Clean exit on Ctrl+C


# Subsystem: docs/subsystems/friction_tracking - Friction log management
@cli.group()
def friction():
    """Friction log commands."""
    pass


@friction.command("log")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--title", help="Brief title for the friction entry")
@click.option("--description", help="Detailed description of the friction")
@click.option(
    "--impact",
    type=click.Choice(["low", "medium", "high", "blocking"]),
    help="Severity of the friction",
)
@click.option("--theme", help="Theme ID to cluster the entry under (or 'new' to create interactively)")
@click.option("--theme-name", help="Human-readable name for new themes (required non-interactively for new themes)")
@click.option("--projects", help="Comma-separated project refs to link (task context only)")
def log_entry(project_dir, title, description, impact, theme, theme_name, projects):
    """Log a new friction entry.

    Can be used interactively (prompts for missing values) or non-interactively
    (all options provided via CLI).

    Non-interactive usage (scripts/agents):
      ve friction log --title "X" --description "Y" --impact low --theme cli

    For new themes, also provide --theme-name:
      ve friction log --title "X" --description "Y" --impact low --theme new-id --theme-name "New Theme"

    In task context (with .ve-task.yaml), creates friction entry in external repo
    and links to specified projects (or all projects if --projects is omitted):
      ve friction log --title "X" --description "Y" --impact low --theme cli --projects proj1,proj2
    """
    from friction import Friction
    from task_utils import (
        is_task_directory,
        create_task_friction_entry,
        TaskFrictionError,
        load_task_config,
        parse_projects_option,
    )

    # Detect task directory context
    if is_task_directory(project_dir):
        # Task context: create friction in external repo
        _log_entry_task_context(
            project_dir, title, description, impact, theme, theme_name, projects
        )
        return

    # Single-repo context: original behavior
    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Load existing themes for validation and display
    themes = friction_log.get_themes()
    existing_theme_ids = {t.id for t in themes}

    # Helper function to prompt with graceful failure for non-interactive mode
    def prompt_or_fail(prompt_text, missing_option, **kwargs):
        """Prompt for input, or fail with clear error if prompting isn't possible."""
        try:
            return click.prompt(prompt_text, **kwargs)
        except click.exceptions.Abort:
            # Prompting failed - we're in non-interactive mode
            click.echo(
                f"Error: Missing required option {missing_option}\n"
                "When running non-interactively, all options must be provided.",
                err=True,
            )
            raise SystemExit(1)

    # Display existing themes for interactive users
    if themes and (not title or not description or not impact or not theme):
        click.echo("\nExisting themes:")
        for t in themes:
            click.echo(f"  - {t.id}: {t.name}")

    # Prompt for missing required options
    if not title:
        title = prompt_or_fail("Title", "--title")
    if not description:
        description = prompt_or_fail("Description", "--description")
    if not impact:
        impact = prompt_or_fail(
            "Impact",
            "--impact",
            type=click.Choice(["low", "medium", "high", "blocking"]),
        )
    if not theme:
        theme = prompt_or_fail("Theme ID (or 'new' to create)", "--theme")

    # Handle 'new' theme placeholder
    if theme == "new":
        try:
            theme = click.prompt("New theme ID (e.g., 'code-refs')")
        except click.exceptions.Abort:
            click.echo(
                "Error: --theme 'new' requires interactive prompts.\n"
                "For non-interactive use, provide the actual theme ID and use --theme-name for new themes.",
                err=True,
            )
            raise SystemExit(1)

    # Handle new theme creation (theme not in existing themes)
    is_new_theme = theme not in existing_theme_ids
    if is_new_theme and not theme_name:
        try:
            theme_name = click.prompt(f"Name for theme '{theme}' (e.g., 'Code Reference Friction')")
        except click.exceptions.Abort:
            click.echo(
                f"Error: Theme '{theme}' is new. --theme-name is required for new themes in non-interactive mode.\n"
                f"Example: --theme-name \"My Theme Name\"",
                err=True,
            )
            raise SystemExit(1)

    try:
        entry_id = friction_log.append_entry(
            title=title,
            description=description,
            impact=impact,
            theme_id=theme,
            theme_name=theme_name,
        )
        click.echo(f"\nCreated friction entry: {entry_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _log_entry_task_context(project_dir, title, description, impact, theme, theme_name, projects):
    """Handle friction logging in task context."""
    from friction import Friction
    from task_utils import (
        create_task_friction_entry,
        TaskFrictionError,
        load_task_config,
        parse_projects_option,
        resolve_repo_directory,
    )

    # Load task config for theme validation
    try:
        config = load_task_config(project_dir)
    except FileNotFoundError:
        click.echo(
            f"Error: Task configuration not found. Expected .ve-task.yaml in {project_dir}",
            err=True,
        )
        raise SystemExit(1)

    # Resolve external repo to get existing themes
    try:
        external_repo_path = resolve_repo_directory(project_dir, config.external_artifact_repo)
    except FileNotFoundError:
        click.echo(
            f"Error: External artifact repository '{config.external_artifact_repo}' not found",
            err=True,
        )
        raise SystemExit(1)

    friction_log = Friction(external_repo_path)
    if not friction_log.exists():
        click.echo(
            f"Error: External repository does not have FRICTION.md. Run 've init' first.",
            err=True,
        )
        raise SystemExit(1)

    # Load existing themes for validation and display
    themes = friction_log.get_themes()
    existing_theme_ids = {t.id for t in themes}

    # Helper function to prompt with graceful failure for non-interactive mode
    def prompt_or_fail(prompt_text, missing_option, **kwargs):
        """Prompt for input, or fail with clear error if prompting isn't possible."""
        try:
            return click.prompt(prompt_text, **kwargs)
        except click.exceptions.Abort:
            click.echo(
                f"Error: Missing required option {missing_option}\n"
                "When running non-interactively, all options must be provided.",
                err=True,
            )
            raise SystemExit(1)

    # Display existing themes for interactive users
    if themes and (not title or not description or not impact or not theme):
        click.echo("\nExisting themes (from external repo):")
        for t in themes:
            click.echo(f"  - {t.id}: {t.name}")

    # Prompt for missing required options
    if not title:
        title = prompt_or_fail("Title", "--title")
    if not description:
        description = prompt_or_fail("Description", "--description")
    if not impact:
        impact = prompt_or_fail(
            "Impact",
            "--impact",
            type=click.Choice(["low", "medium", "high", "blocking"]),
        )
    if not theme:
        theme = prompt_or_fail("Theme ID (or 'new' to create)", "--theme")

    # Handle 'new' theme placeholder
    if theme == "new":
        try:
            theme = click.prompt("New theme ID (e.g., 'code-refs')")
        except click.exceptions.Abort:
            click.echo(
                "Error: --theme 'new' requires interactive prompts.\n"
                "For non-interactive use, provide the actual theme ID and use --theme-name for new themes.",
                err=True,
            )
            raise SystemExit(1)

    # Handle new theme creation (theme not in existing themes)
    is_new_theme = theme not in existing_theme_ids
    if is_new_theme and not theme_name:
        try:
            theme_name = click.prompt(f"Name for theme '{theme}' (e.g., 'Code Reference Friction')")
        except click.exceptions.Abort:
            click.echo(
                f"Error: Theme '{theme}' is new. --theme-name is required for new themes in non-interactive mode.\n"
                f"Example: --theme-name \"My Theme Name\"",
                err=True,
            )
            raise SystemExit(1)

    # Parse --projects option
    try:
        resolved_projects = parse_projects_option(projects, config.projects)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Create friction entry in task context
    try:
        result = create_task_friction_entry(
            task_dir=project_dir,
            title=title,
            description=description,
            impact=impact,
            theme_id=theme,
            theme_name=theme_name,
            projects=resolved_projects,
        )

        click.echo(f"\nCreated friction entry in external repo: {result['entry_id']}")
        click.echo(f"  Path: {result['external_repo_path'] / 'docs' / 'trunk' / 'FRICTION.md'}")

        # Report project updates
        for project_ref, updated in result['project_refs'].items():
            if updated:
                click.echo(f"  Updated reference in {project_ref}")
            else:
                click.echo(f"  Skipped {project_ref} (no FRICTION.md)")

    except TaskFrictionError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@friction.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--open", "status_open", is_flag=True, help="Show only OPEN entries")
@click.option("--tags", multiple=True, help="Filter by theme tags")
def list_entries(project_dir, status_open, tags):
    """List friction entries."""
    from friction import Friction, FrictionStatus

    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Apply status filter
    status_filter = FrictionStatus.OPEN if status_open else None

    # Apply theme filter (first tag only for simplicity)
    theme_filter = tags[0] if tags else None

    entries = friction_log.list_entries(status_filter=status_filter, theme_filter=theme_filter)

    if not entries:
        click.echo("No friction entries found", err=True)
        raise SystemExit(0)

    for entry, status in entries:
        click.echo(f"{entry.id} [{status.value}] [{entry.theme_id}] {entry.title}")


@friction.command("analyze")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--tags", multiple=True, help="Filter analysis to specific themes")
def analyze(project_dir, tags):
    """Analyze friction patterns and suggest actions."""
    from friction import Friction

    friction_log = Friction(project_dir)

    if not friction_log.exists():
        click.echo("Error: Friction log does not exist. Run 've init' first.", err=True)
        raise SystemExit(1)

    # Apply theme filter (first tag only for simplicity)
    theme_filter = tags[0] if tags else None

    analysis = friction_log.analyze_by_theme(theme_filter=theme_filter)

    if not analysis:
        click.echo("No friction entries found", err=True)
        raise SystemExit(0)

    click.echo("## Friction Analysis\n")

    # Get theme metadata for names
    themes = {t.id: t.name for t in friction_log.get_themes()}

    for theme_id, entries in sorted(analysis.items()):
        count = len(entries)
        theme_name = themes.get(theme_id, theme_id)

        # Show warning indicator for patterns (3+ entries)
        if count >= 3:
            click.echo(f"### {theme_id} ({count} entries) ⚠️ Pattern Detected")
        else:
            click.echo(f"### {theme_id} ({count} entries)")

        for entry, status in entries:
            click.echo(f"- {entry.id}: {entry.title}")

        if count >= 3:
            click.echo("\nConsider creating a chunk or investigation to address this pattern.\n")
        else:
            click.echo()


# Migration commands
@cli.group()
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


# Chunk: docs/chunks/reviewer_decision_create_cli - Reviewer CLI group for reviewer agent operations
@cli.group()
def reviewer():
    """Reviewer commands"""
    pass


@reviewer.group()
def decision():
    """Decision file commands"""
    pass


@decision.command("create")
@click.argument("chunk_id")
@click.option("--reviewer", "reviewer_name", default="baseline", help="Reviewer name (default: baseline)")
@click.option("--iteration", default=1, type=int, help="Review iteration (default: 1)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def create_decision(chunk_id, reviewer_name, iteration, project_dir):
    """Create a decision file for reviewing a chunk.

    Creates a decision file at docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md
    with frontmatter and criteria assessment template derived from the chunk's GOAL.md.
    """
    chunks = Chunks(project_dir)

    # Validate chunk exists
    chunk_name = chunks.resolve_chunk_id(chunk_id)
    if chunk_name is None:
        click.echo(f"Error: Chunk '{chunk_id}' not found", err=True)
        raise SystemExit(1)

    # Build decision file path
    decisions_dir = project_dir / "docs" / "reviewers" / reviewer_name / "decisions"
    decision_file = decisions_dir / f"{chunk_name}_{iteration}.md"

    # Check if decision file already exists
    if decision_file.exists():
        click.echo(
            f"Error: Decision file already exists at {decision_file.relative_to(project_dir)}. "
            f"Use --iteration {iteration + 1} for a new review iteration.",
            err=True,
        )
        raise SystemExit(1)

    # Get success criteria from chunk GOAL.md
    criteria = chunks.get_success_criteria(chunk_id)

    # Build decision file content
    # Frontmatter with null values (to be filled by reviewer)
    frontmatter_content = """---
decision: null  # APPROVE | FEEDBACK | ESCALATE
summary: null   # One-sentence rationale
operator_review: null  # "good" | "bad" | { feedback: "<message>" }
---

"""

    # Build criteria assessment section
    body_content = "## Criteria Assessment\n\n"

    if criteria:
        for i, criterion in enumerate(criteria, 1):
            body_content += f"### Criterion {i}: {criterion}\n\n"
            body_content += "- **Status**: satisfied | gap | unclear\n"
            body_content += "- **Evidence**: [What implementation evidence supports this assessment]\n\n"
    else:
        body_content += "<!-- No success criteria found in chunk GOAL.md -->\n\n"

    # Add feedback and escalation sections (to be filled as needed)
    body_content += """## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
"""

    # Create parent directories if needed
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Write the decision file
    decision_file.write_text(frontmatter_content + body_content)

    click.echo(f"Created {decision_file.relative_to(project_dir)}")


if __name__ == "__main__":
    cli()
