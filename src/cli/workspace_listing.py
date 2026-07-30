"""Shared plumbing for `--workspace` aggregated artifact listings.

# Chunk: docs/chunks/federation_reverse_interest - Workspace aggregation for listing commands

`ve chunk list --workspace` and `ve subsystem list --workspace` answer the same
question for different artifact types: "what exists across every tree this
workspace names?". Browsability by aggregation is the alternative to promoting
artifacts into the root tree, so the two commands must fail and warn identically -
an operator learning the failure mode once should not meet a different one next
command.

Aggregation is deliberately read-only. It enumerates artifact directories instead
of going through `ArtifactIndex`, which persists `.artifact-order.json`: a browse
query across 29 member trees must not write into 29 member trees. The cost is
that aggregate listings carry no tip indicator and no causal ordering, neither of
which aggregates anyway - both are properties of a single tree's DAG, and a
merged "tip" would be an invention.
"""

import pathlib
from collections.abc import Iterator

import click

from interest import iter_member_trees
from models.workspace import WorkspaceMember
from workspace import Workspace, WorkspaceError, load_workspace


# Chunk: docs/chunks/federation_reverse_interest - One failure mode for every --workspace command
def load_workspace_or_exit(project_dir: pathlib.Path, option: str = "--workspace") -> Workspace:
    """Load the workspace containing `project_dir`, or exit with instructions.

    Args:
        project_dir: Directory to search upward from.
        option: The option being served, named in the error message.

    Returns:
        The loaded workspace.

    Raises:
        SystemExit: Exit code 1 when there is no usable manifest.
    """
    try:
        return load_workspace(project_dir)
    except WorkspaceError as exc:
        click.echo(
            f"Error: {exc}\n"
            f"{option} aggregates across the VE trees a manifest names, so without "
            f"one there is nothing to aggregate; `ve workspace init --scan` proposes "
            f"the trees it finds.",
            err=True,
        )
        raise SystemExit(1)


# Chunk: docs/chunks/federation_reverse_interest - Missing members are reported, not skipped silently
def walk_listable_members(
    workspace: Workspace,
) -> Iterator[tuple[WorkspaceMember, pathlib.Path]]:
    """Yield each member tree that exists on disk, warning about those that don't.

    A registered tree that has vanished is a manifest defect worth naming: the
    listing that follows is incomplete, and silence about why is the failure mode
    this whole narrative exists to remove. The remaining members still list, so
    one stale entry does not blind the operator to the rest of the workspace.
    """
    for member, member_root in iter_member_trees(workspace):
        if not member_root.is_dir():
            click.echo(
                f"Warning: member '{member.name}' points at '{member.path}', which "
                f"does not exist; its artifacts are missing from this listing.",
                err=True,
            )
            continue
        yield member, member_root


__all__ = ["load_workspace_or_exit", "walk_listable_members"]
