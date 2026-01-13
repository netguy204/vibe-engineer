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
# Chunk: docs/chunks/cluster_rename - Cluster rename command

import pathlib

import click

from chunks import Chunks
from external_refs import strip_artifact_path_prefix, is_external_artifact
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
    create_task_investigation,
    list_task_investigations,
    TaskInvestigationError,
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
# Chunk: docs/chunks/selective_project_linking - Added --projects option
@chunk.command("create")
@click.argument("short_name")
@click.argument("ticket_id", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--future", is_flag=True, help="Create chunk with FUTURE status instead of IMPLEMENTING")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def create(short_name, ticket_id, project_dir, yes, future, projects):
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
        _start_task_chunk(project_dir, short_name, ticket_id, status, projects)
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

    # Chunk: docs/chunks/chunk_create_guard - Catch guard errors
    try:
        chunk_path = chunks.create_chunk(ticket_id, short_name, status=status)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    # Show path relative to project_dir
    relative_path = chunk_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


# Chunk: docs/chunks/rename_chunk_start_to_create - Backward compatibility alias
chunk.add_command(create, name="start")


# Chunk: docs/chunks/chunk_create_task_aware - Task directory chunk creation
# Chunk: docs/chunks/selective_project_linking - Selective project linking
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
            if frontmatter:
                status = frontmatter.status.value
            else:
                # Check if it's an external chunk - try to resolve and get real status
                chunk_path = project_dir / "docs" / "chunks" / chunk_name
                if is_external_artifact(chunk_path, ArtifactType.CHUNK):
                    location = chunks.resolve_chunk_location(chunk_name)
                    if location and location.cached_content:
                        ext_frontmatter = chunks._parse_frontmatter_from_content(location.cached_content)
                        if ext_frontmatter:
                            status = ext_frontmatter.status.value
                        else:
                            status = "EXTERNAL"
                    else:
                        status = "EXTERNAL"
                else:
                    status = "UNKNOWN"
            tip_indicator = " *" if chunk_name in tips else ""
            click.echo(f"docs/chunks/{chunk_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/task_status_command - Grouped artifact listing output formatter
def _format_grouped_artifact_list(
    grouped_data: dict,
    artifact_type_dir: str,
) -> None:
    """Format and display grouped artifact listing output.

    Args:
        grouped_data: Dict from list_task_artifacts_grouped with external and projects keys
        artifact_type_dir: Directory name for the artifact type (e.g., "chunks", "narratives")
    """
    external = grouped_data["external"]
    projects = grouped_data["projects"]

    # Check if there are any artifacts at all
    has_external = bool(external["artifacts"])
    has_projects = any(p["artifacts"] for p in projects)

    if not has_external and not has_projects:
        click.echo(f"No {artifact_type_dir} found", err=True)
        raise SystemExit(1)

    # Display external artifacts
    if external["artifacts"]:
        click.echo(f"# External Artifacts ({external['repo']})")
        for artifact in external["artifacts"]:
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
    for project in projects:
        if project["artifacts"]:
            click.echo(f"# {project['repo']} (local)")
            for artifact in project["artifacts"]:
                name = artifact["name"]
                status = artifact["status"]
                is_tip = artifact.get("is_tip", False)
                tip_indicator = " (tip)" if is_tip else ""

                click.echo(f"{name} [{status}]{tip_indicator}")
            click.echo()


# Chunk: docs/chunks/list_task_aware - Task directory chunk listing handler
# Chunk: docs/chunks/task_status_command - Grouped artifact listing
# Chunk: docs/chunks/chunk_list_repo_source - Include repo ref in --latest output
def _list_task_chunks(latest: bool, task_dir: pathlib.Path):
    """Handle chunk listing in task directory (cross-repo mode)."""
    try:
        if latest:
            current_chunk, external_repo = get_current_task_chunk(task_dir)
            if current_chunk is None:
                click.echo("No implementing chunk found", err=True)
                raise SystemExit(1)
            click.echo(f"{external_repo}::docs/chunks/{current_chunk}")
        else:
            grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.CHUNK)
            _format_grouped_artifact_list(grouped_data, "chunks")
    except (TaskChunkError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/task_list_proposed - Helper to format proposed chunks by source
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


# Chunk: docs/chunks/task_list_proposed - Grouped proposed chunks formatter
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


# Chunk: docs/chunks/task_list_proposed - Task directory proposed chunk listing handler
def _list_task_proposed_chunks(task_dir: pathlib.Path):
    """Handle proposed chunk listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_proposed_chunks(task_dir)
        _format_grouped_proposed_chunks(grouped_data)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/proposed_chunks_frontmatter - List proposed chunks command
# Chunk: docs/chunks/task_list_proposed - Task-aware proposed chunk listing
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


# Chunk: docs/chunks/future_chunk_creation - Activate FUTURE chunk
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def activate(chunk_id, project_dir):
    """Activate a FUTURE chunk by changing its status to IMPLEMENTING."""
    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    chunks = Chunks(project_dir)

    try:
        activated = chunks.activate_chunk(chunk_id)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Activated docs/chunks/{activated}")


# Chunk: docs/chunks/valid_transitions - Status command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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


# Chunk: docs/chunks/chunk_overlap_command - Find overlapping chunks
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
@chunk.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find chunks with overlapping code references."""
    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    chunks = Chunks(project_dir)

    try:
        affected = chunks.find_overlapping_chunks(chunk_id)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    for name in affected:
        click.echo(f"docs/chunks/{name}")


# Chunk: docs/chunks/cluster_prefix_suggest - Suggest prefix command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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


# Chunk: docs/chunks/narrative_consolidation - Backreference census command
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


# Chunk: docs/chunks/narrative_consolidation - Chunk clustering command
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


# Chunk: docs/chunks/chunk_validate - Validate chunk for completion
# Chunk: docs/chunks/bidirectional_refs - Subsystem ref validation
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
# Chunk: docs/chunks/task_chunk_validation - Task context awareness
# Chunk: docs/chunks/orch_inject_validate - Injectable validation mode
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


# Chunk: docs/chunks/cluster_rename - Cluster rename command
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


# Chunk: docs/chunks/cluster_list_command - Cluster list command
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


# Chunk: docs/chunks/narrative_cli_commands - Narrative command group
@cli.group()
def narrative():
    """Narrative commands"""
    pass


# Chunk: docs/chunks/narrative_cli_commands - Create narrative command
# Chunk: docs/chunks/task_aware_narrative_cmds - Task-aware narrative creation
# Chunk: docs/chunks/selective_project_linking - Added --projects option
@narrative.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def create_narrative(short_name, project_dir, projects):
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
        _create_task_narrative(project_dir, short_name, projects)
        return

    # Single-repo mode
    narratives = Narratives(project_dir)
    narrative_path = narratives.create_narrative(short_name)

    # Show path relative to project_dir
    relative_path = narrative_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


# Chunk: docs/chunks/task_aware_narrative_cmds - Task directory narrative creation
# Chunk: docs/chunks/selective_project_linking - Selective project linking
def _create_task_narrative(task_dir: pathlib.Path, short_name: str, projects_input: str | None = None):
    """Handle narrative creation in task directory (cross-repo mode)."""
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
# Chunk: docs/chunks/task_status_command - Grouped artifact listing
def _list_task_narratives(task_dir: pathlib.Path):
    """Handle narrative listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.NARRATIVE)
        _format_grouped_artifact_list(grouped_data, "narratives")
    except (TaskNarrativeError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/valid_transitions - Status command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
@narrative.command()
@click.argument("narrative_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(narrative_id, new_status, project_dir):
    """Show or update narrative status."""
    from models import extract_short_name

    # Normalize narrative_id to strip path prefixes
    narrative_id = strip_artifact_path_prefix(narrative_id, ArtifactType.NARRATIVE)

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


# Chunk: docs/chunks/narrative_consolidation - Compact command
@narrative.command("compact")
@click.argument("chunk_ids", nargs=-1, required=True)
@click.option("--name", required=True, help="Short name for the consolidated narrative")
@click.option("--description", default="Consolidated narrative", help="Description for the narrative")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def compact(chunk_ids, name, description, project_dir):
    """Consolidate multiple chunks into a single narrative.

    Takes a list of ACTIVE chunk IDs and creates a narrative that references them.
    Updates each chunk's frontmatter to reference the new narrative.

    Example:
        ve narrative compact chunk_a chunk_b chunk_c --name my_narrative
    """
    from chunks import consolidate_chunks

    if len(chunk_ids) < 2:
        click.echo("Error: Need at least 2 chunks to consolidate", err=True)
        raise SystemExit(1)

    # Normalize chunk IDs
    normalized_ids = [strip_artifact_path_prefix(cid, ArtifactType.CHUNK) for cid in chunk_ids]

    try:
        result = consolidate_chunks(
            project_dir,
            chunk_ids=normalized_ids,
            narrative_name=name,
            narrative_description=description,
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Created narrative: docs/narratives/{result.narrative_id}")
    click.echo("")
    click.echo(f"Consolidated {len(result.chunks_updated)} chunks:")
    for chunk_name in result.chunks_updated:
        click.echo(f"  - {chunk_name}")

    if result.files_to_update:
        click.echo("")
        click.echo("Files with backreferences to update:")
        for file_path, (refs, _) in result.files_to_update.items():
            click.echo(f"  - {file_path}: {len(refs)} refs -> 1 narrative ref")
        click.echo("")
        click.echo(f"Run `ve narrative update-refs {result.narrative_id}` to update code backreferences.")


# Chunk: docs/chunks/narrative_consolidation - Update-refs command
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
# Chunk: docs/chunks/task_status_command - Grouped artifact listing
def _list_task_subsystems(task_dir: pathlib.Path):
    """Handle subsystem listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.SUBSYSTEM)
        _format_grouped_artifact_list(grouped_data, "subsystems")
    except (TaskSubsystemError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/subsystem_cli_scaffolding - Create subsystem command
# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem discovery
# Chunk: docs/chunks/selective_project_linking - Added --projects option
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
# Chunk: docs/chunks/selective_project_linking - Selective project linking
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


# Chunk: docs/chunks/bidirectional_refs - Validate subsystem command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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


# Chunk: docs/chunks/subsystem_status_transitions - Status command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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


# Chunk: docs/chunks/subsystem_impact_resolution - Subsystem overlap command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
@subsystem.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find subsystems with code references overlapping a chunk's changes."""
    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

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
# Chunk: docs/chunks/task_aware_investigations - Task-aware investigation creation
# Chunk: docs/chunks/selective_project_linking - Added --projects option
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

    # Single-repo mode
    investigations = Investigations(project_dir)
    investigation_path = investigations.create_investigation(short_name)

    # Show path relative to project_dir
    relative_path = investigation_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


# Chunk: docs/chunks/task_aware_investigations - Task directory investigation creation
# Chunk: docs/chunks/selective_project_linking - Selective project linking
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


# Chunk: docs/chunks/investigation_commands - List investigations command
# Chunk: docs/chunks/artifact_list_ordering - Use ArtifactIndex for causal ordering
# Chunk: docs/chunks/task_aware_investigations - Task-aware investigation listing
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


# Chunk: docs/chunks/task_aware_investigations - Task directory investigation listing handler
# Chunk: docs/chunks/task_status_command - Grouped artifact listing
def _list_task_investigations(task_dir: pathlib.Path):
    """Handle investigation listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.INVESTIGATION)
        _format_grouped_artifact_list(grouped_data, "investigations")
    except (TaskInvestigationError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/valid_transitions - Status command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path normalization
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
        artifact_type, resolved_artifact_id = _detect_artifact_type_from_id(repo_path, local_artifact_id)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_single_repo(
            repo_path,
            resolved_artifact_id,
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


# Chunk: docs/chunks/artifact_promote - Artifact command group
@cli.group()
def artifact():
    """Artifact management commands."""
    pass


# Chunk: docs/chunks/artifact_promote - Promote artifact command
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


# Chunk: docs/chunks/copy_as_external - Copy external artifact command
# Chunk: docs/chunks/accept_full_artifact_paths - Flexible path input
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


# Chunk: docs/chunks/remove_external_ref - Remove external artifact command
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


# Chunk: docs/chunks/orch_foundation - Orchestrator CLI commands
@cli.group()
def orch():
    """Orchestrator daemon commands."""
    pass


# Chunk: docs/chunks/orch_foundation - Start daemon command
# Chunk: docs/chunks/orch_tcp_port - TCP port and host options
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


# Chunk: docs/chunks/orch_foundation - Stop daemon command
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


# Chunk: docs/chunks/orch_foundation - Daemon status command
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


# Chunk: docs/chunks/orch_foundation - List work units command
# Chunk: docs/chunks/orch_attention_reason - Display attention reason in ps output
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


# Chunk: docs/chunks/orch_foundation - Work unit command group
@orch.group("work-unit")
def work_unit():
    """Work unit management commands."""
    pass


# Chunk: docs/chunks/orch_foundation - Create work unit command
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


# Chunk: docs/chunks/orch_foundation - Work unit status command
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


# Chunk: docs/chunks/orch_attention_reason - Work unit show command
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


# Chunk: docs/chunks/orch_foundation - Work unit list command
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


# Chunk: docs/chunks/orch_foundation - Delete work unit command
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


# Chunk: docs/chunks/orch_scheduling - Inject chunk into work pool
@orch.command("inject")
@click.argument("chunk")
@click.option("--phase", type=str, default=None, help="Override initial phase (GOAL, PLAN, IMPLEMENT)")
@click.option("--priority", type=int, default=0, help="Scheduling priority (higher = more urgent)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_inject(chunk, phase, priority, json_output, project_dir):
    """Inject a chunk into the orchestrator work pool.

    Validates chunk exists and determines initial phase from chunk state.
    """
    from orchestrator.client import create_client, OrchestratorClientError, DaemonNotRunningError
    import json

    # Chunk: docs/chunks/orch_inject_path_compat - Normalize chunk path for CLI consistency
    chunk = strip_artifact_path_prefix(chunk, ArtifactType.CHUNK)

    client = create_client(project_dir)
    try:
        # Use the inject endpoint via generic request
        body = {"chunk": chunk, "priority": priority}
        if phase:
            body["phase"] = phase

        result = client._request("POST", "/work-units/inject", json=body)

        if json_output:
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Injected: {result['chunk']} [{result['phase']}] priority={result['priority']}")

    except DaemonNotRunningError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except OrchestratorClientError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    finally:
        client.close()


# Chunk: docs/chunks/orch_scheduling - Show ready queue
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


# Chunk: docs/chunks/orch_scheduling - Prioritize work unit
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


# Chunk: docs/chunks/orch_scheduling - Config command
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


# Chunk: docs/chunks/orch_attention_queue - Attention queue CLI commands
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


# Chunk: docs/chunks/orch_conflict_oracle - Conflict CLI commands


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


# Chunk: docs/chunks/friction_template_and_cli - Friction log commands
@cli.group()
def friction():
    """Friction log commands."""
    pass


# Chunk: docs/chunks/friction_template_and_cli - Log a new friction entry
# Chunk: docs/chunks/friction_noninteractive - Non-interactive support
# Chunk: docs/chunks/selective_artifact_friction - Task context and --projects flag
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


# Chunk: docs/chunks/selective_artifact_friction - Task context friction logging
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


# Chunk: docs/chunks/friction_template_and_cli - List friction entries
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


# Chunk: docs/chunks/friction_template_and_cli - Analyze friction patterns
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


if __name__ == "__main__":
    cli()
