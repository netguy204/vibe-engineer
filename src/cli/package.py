"""Package command group.

# Chunk: docs/chunks/federation_template_pointers - `ve package scaffold`

The command a package template calls instead of shipping a `docs/` tree of its own.
Its default output is a pointer-only workspace member; a full VE tree is the
explicit opt-in.

The command takes a positional PATH rather than a `--project-dir`: it *creates* a
tree, so the nearest-enclosing-tree redirect that every `--project-dir` carries
(`cli/tree_discovery.py`) would be exactly wrong here — the same reason `init` is in
its EXEMPT_COMMANDS.
"""

import pathlib

import click

from package_scaffold import PackageScaffold


@click.group()
def package():
    """Scaffold packages as workspace members."""
    pass


# Chunk: docs/chunks/federation_template_pointers - Pointer-only scaffold, full tree opt-in
@package.command()
@click.argument("path", type=click.Path(path_type=pathlib.Path))
@click.option(
    "--interest",
    "interests",
    multiple=True,
    metavar="SPEC",
    help="Intent this package consumes, as "
         "'<member>::docs/<type>/<name>: why it depends on it'. Repeatable.",
)
@click.option(
    "--name",
    default=None,
    help="Workspace member name (defaults to the directory's name). This is what "
         "'<member>::' references resolve against.",
)
@click.option(
    "--full-tree",
    is_flag=True,
    help="Create a full VE tree (docs/trunk/ and artifact directories) instead of a "
         "pointer-only one. For a package that will own intent of its own.",
)
def scaffold(path, interests, name, full_tree):
    """Scaffold the package at PATH as a workspace member.

    By default this creates a *pointer-only* tree: one `external.yaml` interest edge
    per --interest and nothing else — no `docs/trunk/`, no empty artifact
    directories. The package becomes addressable as `<member>::docs/...` without
    becoming a new addressing root, which is what keeps a monorepo from growing a
    documentation namespace per package.

    \b
    Examples:
        ve package scaffold apps/viz \\
          --interest 'pybusiness::docs/subsystems/commitment_baseline: charts render this baseline'
        ve package scaffold packages/libs/newlib --full-tree
    """
    scaffolder = PackageScaffold(
        path=path, name=name, interests=list(interests), full_tree=full_tree
    )

    errors = scaffolder.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    result = scaffolder.execute()

    flavor = "full VE tree" if result.full_tree else "pointer-only package"
    click.echo(f"Scaffolded {flavor} at {result.path}")

    # Annotate each interest pointer with its target, the way `ve external point`
    # reports one, so the same information reads the same in both places.
    edges = {f"{edge.local_path}/external.yaml": edge for edge in result.interests}
    for created in result.created:
        click.echo(f"  Created {created}")
        edge = edges.get(created)
        if edge is None:
            continue
        click.echo(f"    points at tree:{edge.member} -> {edge.qualified_ref}")
        if edge.why:
            click.echo(f"    why: {edge.why}")

    if result.registered:
        click.echo(
            f"Registered member '{result.name}' in the workspace at "
            f"{result.workspace_root}"
        )
    elif result.workspace_root is None:
        click.echo(
            "No .ve-workspace.yaml found at or above this path, so there is no "
            "workspace to join; skipped member registration."
        )

    if not result.full_tree:
        if result.governing_tree is not None:
            click.echo(f"Governed by the VE tree at {result.governing_tree}")
        else:
            click.echo(
                "No VE tree governs this package: bare references in its files "
                "resolve to nothing, so every reference must be qualified "
                "('<member>::docs/...') or recorded as an interest edge. See "
                f"{result.path / 'AGENTS.md'}."
            )

    for warning in result.warnings:
        click.echo(f"Warning: {warning}", err=True)
