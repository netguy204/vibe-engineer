"""Chunk command group.

Commands for managing chunks - the primary work unit in Vibe Engineering.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cluster_analysis - Chunk naming and clustering
# Chunk: docs/chunks/cli_modularize - Chunk CLI commands
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands

import json
import pathlib

import click

from chunks import Chunks
from external_refs import strip_artifact_path_prefix, is_external_artifact, load_external_ref
from investigations import Investigations
from narratives import Narratives
from subsystems import Subsystems
from models import ChunkStatus, ArtifactType
from task_utils import (
    is_task_directory,
    create_task_chunk,
    list_task_chunks,
    get_current_task_chunk,
    TaskChunkError,
    list_task_artifacts_grouped,
    TaskArtifactListError,
    list_task_proposed_chunks,
    load_task_config,
    parse_projects_option,
    check_task_project_context,
)
from cluster_analysis import check_cluster_size, format_cluster_warning
from chunks import get_chunk_prefix
from artifact_ordering import ArtifactIndex, ArtifactType

from cli.utils import (
    validate_short_name,
    validate_ticket_id,
    validate_combined_chunk_name,
    warn_task_project_context,
    handle_task_context,
)


@click.group()
def chunk():
    """Manage chunks - discrete units of implementation work.

    Chunks are the primary work units in Vibe Engineering, each representing
    a focused piece of implementation with a defined goal and success criteria.
    """
    pass


@chunk.command("create")
@click.argument("short_names", nargs=-1, required=True)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--future", is_flag=True, help="Create chunk with FUTURE status instead of IMPLEMENTING")
@click.option("--ticket", default=None, help="Ticket ID to apply to all chunks")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
# Chunk: docs/chunks/chunk_batch_create - CLI command accepting variadic chunk names with batch creation logic
# Chunk: docs/chunks/future_chunk_creation - CLI command with --future flag for creating FUTURE chunks
# Chunk: docs/chunks/implement_chunk_start-ve-001 - create command - argument parsing, validation, normalization, duplicate detection, --yes flag
def create(short_names, project_dir, yes, future, ticket, projects):
    """Create a new chunk (or multiple chunks). (Aliases: start)

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


# Chunk: docs/chunks/cli_json_output - Helper function for JSON serialization of chunk frontmatter
def _chunk_to_json_dict(
    chunk_name: str,
    frontmatter,
    chunks_manager,
    project_dir: pathlib.Path,
    tips: set[str] | None = None,
) -> dict:
    """Convert a chunk and its frontmatter to a JSON-serializable dictionary.

    Args:
        chunk_name: The chunk directory name
        frontmatter: Parsed ChunkFrontmatter object (or None)
        chunks_manager: Chunks instance for additional lookups
        project_dir: Project directory path
        tips: Set of chunk names that are tips (optional, for is_tip field)

    Returns:
        Dictionary with chunk name, status, and all frontmatter fields
    """
    if frontmatter is None:
        return {
            "name": chunk_name,
            "status": "UNKNOWN",
            "is_tip": chunk_name in tips if tips else False,
        }

    # Use Pydantic's model_dump() for serialization
    fm_dict = frontmatter.model_dump()

    # Convert StrEnum values to their string representations
    # Status is already a StrEnum, model_dump should handle it
    if hasattr(fm_dict.get("status"), "value"):
        fm_dict["status"] = fm_dict["status"].value

    # Build the result with name first, then status, then rest of frontmatter
    result = {
        "name": chunk_name,
        "status": fm_dict.pop("status", "UNKNOWN"),
    }

    # Add is_tip indicator
    result["is_tip"] = chunk_name in tips if tips else False

    # Add remaining frontmatter fields
    result.update(fm_dict)

    return result


# Chunk: docs/chunks/chunklist_status_filter - Parse and validate status filters
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
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
# Chunk: docs/chunks/artifact_list_ordering - CLI command with tip indicator display using ArtifactIndex
# Chunk: docs/chunks/chunk_list_command-ve-002 - CLI command ve chunk list with --latest, --last-active, and --project-dir options
# Chunk: docs/chunks/chunk_list_flags - CLI command with renamed --current flag and new --recent flag
# Chunk: docs/chunks/chunk_last_active - CLI handler with --last-active flag and mutual exclusivity check
# Chunk: docs/chunks/chunklist_status_filter - Status filter parsing and handling
# Chunk: docs/chunks/chunklist_external_status - External chunk status display in list output
# Chunk: docs/chunks/cli_exit_codes - Exit code 0 for empty chunk list results
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
# Chunk: docs/chunks/future_chunk_creation - CLI command showing status, --latest uses get_current_chunk to find IMPLEMENTING chunk
def list_chunks(current, last_active, recent, status_filter, future_flag, active_flag, implementing_flag, json_output, project_dir):
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
        _list_task_chunks(current, last_active, recent, status_set, project_dir, json_output)
        return

    # Single-repo mode - list from docs/chunks/
    chunks = Chunks(project_dir)

    if current:
        current_chunk = chunks.get_current_chunk()
        if current_chunk is None:
            if json_output:
                click.echo(json.dumps([]))
                return
            click.echo("No implementing chunk found", err=True)
            raise SystemExit(1)
        if json_output:
            # Get frontmatter for the current chunk
            frontmatter = chunks.parse_chunk_frontmatter(current_chunk)
            result = _chunk_to_json_dict(current_chunk, frontmatter, chunks, project_dir)
            click.echo(json.dumps([result], indent=2))
        else:
            click.echo(f"docs/chunks/{current_chunk}")
    elif last_active:
        active_chunk = chunks.get_last_active_chunk()
        if active_chunk is None:
            if json_output:
                click.echo(json.dumps([]))
                return
            click.echo("No active tip chunk found", err=True)
            raise SystemExit(1)
        if json_output:
            frontmatter = chunks.parse_chunk_frontmatter(active_chunk)
            result = _chunk_to_json_dict(active_chunk, frontmatter, chunks, project_dir)
            click.echo(json.dumps([result], indent=2))
        else:
            click.echo(f"docs/chunks/{active_chunk}")
    elif recent:
        recent_chunks = chunks.get_recent_active_chunks(limit=10)
        if not recent_chunks:
            if json_output:
                click.echo(json.dumps([]))
                return
            click.echo("No active chunks found", err=True)
            raise SystemExit(1)
        if json_output:
            results = []
            for chunk_name in recent_chunks:
                frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
                results.append(_chunk_to_json_dict(chunk_name, frontmatter, chunks, project_dir))
            click.echo(json.dumps(results, indent=2))
        else:
            for chunk_name in recent_chunks:
                click.echo(f"docs/chunks/{chunk_name}")
    else:
        chunk_list = chunks.list_chunks()
        if not chunk_list:
            if json_output:
                click.echo(json.dumps([]))
                return
            click.echo("No chunks found")
            raise SystemExit(0)

        artifact_index = ArtifactIndex(project_dir)
        tips = set(artifact_index.find_tips(ArtifactType.CHUNK))

        # Collect results for JSON output or track count for text output
        results = []
        filtered_count = 0

        for chunk_name in chunk_list:
            chunk_path = project_dir / "docs" / "chunks" / chunk_name
            # Check for external artifact reference before parsing frontmatter
            if is_external_artifact(chunk_path, ArtifactType.CHUNK):
                external_ref = load_external_ref(chunk_path)
                # External chunks have no parseable status - skip when filtering
                if status_set is not None:
                    continue
                filtered_count += 1
                if json_output:
                    results.append({
                        "name": chunk_name,
                        "status": "EXTERNAL",
                        "repo": external_ref.repo,
                        "artifact_id": external_ref.artifact_id,
                        "track": external_ref.track,
                        "is_tip": chunk_name in tips,
                    })
                else:
                    status = f"EXTERNAL: {external_ref.repo}"
                    tip_indicator = " *" if chunk_name in tips else ""
                    click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")
            else:
                frontmatter, errors = chunks.parse_chunk_frontmatter_with_errors(chunk_name)
                if frontmatter:
                    chunk_status = frontmatter.status
                    # Apply status filter if specified
                    if status_set is not None and chunk_status not in status_set:
                        continue
                    filtered_count += 1
                    if json_output:
                        results.append(_chunk_to_json_dict(chunk_name, frontmatter, chunks, project_dir, tips))
                    else:
                        status = chunk_status.value
                        tip_indicator = " *" if chunk_name in tips else ""
                        click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")
                elif errors:
                    # Chunks with parse errors - skip when filtering
                    if status_set is not None:
                        continue
                    filtered_count += 1
                    if json_output:
                        results.append({
                            "name": chunk_name,
                            "status": "PARSE_ERROR",
                            "error": errors[0],
                            "is_tip": chunk_name in tips,
                        })
                    else:
                        # Show first error for brevity
                        first_error = errors[0]
                        status = f"PARSE ERROR: {first_error}"
                        tip_indicator = " *" if chunk_name in tips else ""
                        click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")
                else:
                    # Unknown status - skip when filtering
                    if status_set is not None:
                        continue
                    filtered_count += 1
                    if json_output:
                        results.append({
                            "name": chunk_name,
                            "status": "UNKNOWN",
                            "is_tip": chunk_name in tips,
                        })
                    else:
                        status = "UNKNOWN"
                        tip_indicator = " *" if chunk_name in tips else ""
                        click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")

        if json_output:
            click.echo(json.dumps(results, indent=2))
        elif filtered_count == 0:
            # Handle case where all chunks were filtered out
            if status_set is not None:
                status_names = ", ".join(s.value for s in status_set)
                click.echo(f"No chunks found matching status: {status_names}")
            else:
                click.echo("No chunks found")
            raise SystemExit(0)


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
        from cli.utils import format_not_found_error
        click.echo(f"Error: {format_not_found_error('Chunk', chunk_id, 've chunk list')}", err=True)
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


# Chunk: docs/chunks/cli_json_output - JSON output for grouped artifact listing
def _format_grouped_artifact_list_json(
    grouped_data: dict,
    artifact_type_dir: str,
    status_set: set[ChunkStatus] | None = None,
) -> None:
    """Format and output grouped artifact listing as JSON.

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

    # Collect all artifacts into a flat list with repo information
    results = []

    # Add external artifacts
    for artifact in external["artifacts"]:
        if status_matches(artifact["status"]):
            result = {**artifact, "repo": external["repo"], "source": "external"}
            results.append(result)

    # Add project artifacts
    for project in projects:
        for artifact in project["artifacts"]:
            if status_matches(artifact["status"]):
                result = {**artifact, "repo": project["repo"], "source": "local"}
                results.append(result)

    click.echo(json.dumps(results, indent=2))


# Chunk: docs/chunks/chunk_list_repo_source - Format output as {external_repo}::docs/chunks/{chunk_name} in --latest mode
# Chunk: docs/chunks/chunk_last_active - Cross-repo (task context) support for --last-active
# Chunk: docs/chunks/cli_json_output - JSON output for task context chunk listing
def _list_task_chunks(
    current: bool,
    last_active: bool,
    recent: bool,
    status_set: set[ChunkStatus] | None,
    task_dir: pathlib.Path,
    json_output: bool = False,
):
    """Handle chunk listing in task directory (cross-repo mode).

    Args:
        current: If True, output only the current IMPLEMENTING chunk
        last_active: If True, output only the most recently completed ACTIVE chunk
        recent: If True, output the 10 most recently created ACTIVE chunks
        status_set: If provided, filter to only chunks with matching status
        task_dir: Path to the task directory
        json_output: If True, output in JSON format
    """
    try:
        if current:
            current_chunk, external_repo = get_current_task_chunk(task_dir)
            if current_chunk is None:
                if json_output:
                    click.echo(json.dumps([]))
                    return
                click.echo("No implementing chunk found", err=True)
                raise SystemExit(1)
            if json_output:
                # Get frontmatter for the current chunk
                from task_utils import resolve_repo_directory, load_task_config
                config = load_task_config(task_dir)
                external_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
                external_chunks = Chunks(external_path)
                frontmatter = external_chunks.parse_chunk_frontmatter(current_chunk)
                result = _chunk_to_json_dict(current_chunk, frontmatter, external_chunks, external_path)
                result["repo"] = external_repo
                click.echo(json.dumps([result], indent=2))
            else:
                click.echo(f"{external_repo}::docs/chunks/{current_chunk}")
        elif last_active:
            # For task context, get the last active chunk from the external artifacts repo
            from task_utils import resolve_repo_directory, load_task_config

            config = load_task_config(task_dir)
            external_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            active_chunk = external_chunks.get_last_active_chunk()
            if active_chunk is None:
                if json_output:
                    click.echo(json.dumps([]))
                    return
                click.echo("No active tip chunk found", err=True)
                raise SystemExit(1)
            if json_output:
                frontmatter = external_chunks.parse_chunk_frontmatter(active_chunk)
                result = _chunk_to_json_dict(active_chunk, frontmatter, external_chunks, external_path)
                result["repo"] = config.external_artifact_repo
                click.echo(json.dumps([result], indent=2))
            else:
                click.echo(f"{config.external_artifact_repo}::docs/chunks/{active_chunk}")
        elif recent:
            # For task context, get recent active chunks from the external artifacts repo
            from task_utils import resolve_repo_directory, load_task_config

            config = load_task_config(task_dir)
            external_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
            external_chunks = Chunks(external_path)
            recent_chunks = external_chunks.get_recent_active_chunks(limit=10)
            if not recent_chunks:
                if json_output:
                    click.echo(json.dumps([]))
                    return
                click.echo("No active chunks found", err=True)
                raise SystemExit(1)
            if json_output:
                results = []
                for chunk_name in recent_chunks:
                    frontmatter = external_chunks.parse_chunk_frontmatter(chunk_name)
                    result = _chunk_to_json_dict(chunk_name, frontmatter, external_chunks, external_path)
                    result["repo"] = config.external_artifact_repo
                    results.append(result)
                click.echo(json.dumps(results, indent=2))
            else:
                for chunk_name in recent_chunks:
                    click.echo(f"{config.external_artifact_repo}::docs/chunks/{chunk_name}")
        else:
            grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.CHUNK)
            if json_output:
                _format_grouped_artifact_list_json(grouped_data, "chunks", status_set)
            else:
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
# Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
def list_proposed_chunks_cmd(project_dir):
    """List all proposed chunks that haven't been created yet."""
    if handle_task_context(project_dir, lambda: _list_task_proposed_chunks(project_dir)):
        return

    # Single-repo mode
    chunks = Chunks(project_dir)
    investigations = Investigations(project_dir)
    narratives = Narratives(project_dir)
    subsystems_mgr = Subsystems(project_dir)

    proposed = chunks.list_proposed_chunks(investigations, narratives, subsystems_mgr)

    if not proposed:
        click.echo("No proposed chunks found", err=True)
        raise SystemExit(0)

    _format_proposed_chunks_by_source(proposed)


# Chunk: docs/chunks/accept_full_artifact_paths - CLI command using strip_artifact_path_prefix
# Chunk: docs/chunks/future_chunk_creation - CLI command to activate a FUTURE chunk to IMPLEMENTING status
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
    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    chunks = Chunks(project_dir)

    # Resolve chunk_id
    resolved_id = chunks.resolve_chunk_id(chunk_id)
    if resolved_id is None:
        from cli.utils import format_not_found_error
        click.echo(f"Error: {format_not_found_error('Chunk', chunk_id, 've chunk list')}", err=True)
        raise SystemExit(1)

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = chunks.get_status(resolved_id)
            click.echo(f"{resolved_id}: {current_status.value}")
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
        click.echo(f"{resolved_id}: {old_status.value} -> {updated_status.value}")
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
    from backreferences import count_backreferences

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
    for i, (cluster_items, theme) in enumerate(zip(result.clusters, result.cluster_themes), 1):
        click.echo(f"Cluster {i}: {theme}")
        for name in cluster_items:
            click.echo(f"  - {name}")
        click.echo("")

    if result.unclustered:
        click.echo(f"Unclustered chunks ({len(result.unclustered)}):")
        for name in result.unclustered:
            click.echo(f"  - {name}")


# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/chunk_validate - CLI command for chunk validation
# Chunk: docs/chunks/bidirectional_refs - Renamed from 'complete' to 'validate', includes subsystem ref validation
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
