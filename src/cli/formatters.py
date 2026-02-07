"""Shared CLI formatting helpers.

Common formatting functions used across artifact CLI modules to eliminate
duplication and cross-module private imports.
"""
# Chunk: docs/chunks/cli_formatters_extract - Extract shared formatters from CLI modules

import json

import click

from models import ChunkStatus


def artifact_to_json_dict(
    name: str,
    frontmatter,
    tips: set[str] | None = None,
) -> dict:
    """Convert an artifact and its frontmatter to a JSON-serializable dictionary.

    This is a generic formatter that works for chunks, narratives, subsystems,
    and investigations. All artifact types share the same serialization pattern.

    Args:
        name: The artifact directory name
        frontmatter: Parsed frontmatter object (or None)
        tips: Set of artifact names that are tips (optional, for is_tip field)

    Returns:
        Dictionary with artifact name, status, is_tip, and all frontmatter fields
    """
    if frontmatter is None:
        return {
            "name": name,
            "status": "UNKNOWN",
            "is_tip": name in tips if tips else False,
        }

    # Use Pydantic's model_dump() for serialization
    fm_dict = frontmatter.model_dump()

    # Convert StrEnum values to their string representations
    # Status is already a StrEnum, model_dump should handle it
    if hasattr(fm_dict.get("status"), "value"):
        fm_dict["status"] = fm_dict["status"].value

    # Build the result with name first, then status, then rest of frontmatter
    result = {
        "name": name,
        "status": fm_dict.pop("status", "UNKNOWN"),
    }

    # Add is_tip indicator
    result["is_tip"] = name in tips if tips else False

    # Add remaining frontmatter fields
    result.update(fm_dict)

    return result


def format_grouped_artifact_list(
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


def format_grouped_artifact_list_json(
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
