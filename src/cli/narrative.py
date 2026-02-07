"""Narrative command group.

Commands for managing narratives - multi-chunk initiatives.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/cli_modularize - Narrative CLI commands

import pathlib

import click

from chunks import Chunks
from external_refs import strip_artifact_path_prefix
from narratives import Narratives
from models import NarrativeStatus, ArtifactType
from task_utils import (
    is_task_directory,
    create_task_narrative,
    list_task_narratives,
    TaskNarrativeError,
    load_task_config,
    parse_projects_option,
    check_task_project_context,
)
from artifact_ordering import ArtifactIndex, ArtifactType

from cli.utils import validate_short_name, warn_task_project_context


@click.group()
def narrative():
    """Manage narratives - multi-chunk initiatives with upfront decomposition.

    Use narratives when work is too large for a single chunk. They decompose
    big ambitions into ordered chunks with a shared context.
    """
    pass


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
            from cli.utils import format_not_found_error
            click.echo(f"Error: {format_not_found_error('Narrative', narrative_id, 've narrative list')}", err=True)
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
        from cli.utils import format_not_found_error
        click.echo(f"Error: {format_not_found_error('Narrative', narrative_id, 've narrative list')}", err=True)
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
