"""Hooks command group.

# Chunk: docs/chunks/hooks_lifecycle_fragments - ve hooks CLI surface

`ve hooks show` is invoked from the `!`-prefixed context block of every plugin
command, which drives the design of this module: both commands always exit 0.
A non-zero exit inside a context substitution is a failure the agent must
reason about in a command that has nothing to do with hooks, and an operator's
typo in docs/hooks/ is not a reason to break `ve validate` or a lifecycle
command.
"""

import json
import pathlib

import click

from hooks import Hooks


@click.group()
def hooks() -> None:
    """Inspect VE hooks - per-command instruction fragments in docs/hooks/."""


@hooks.command("show")
@click.argument("event")
@click.option(
    "--project-dir",
    type=click.Path(path_type=pathlib.Path),
    default=".",
    help="Project root to resolve docs/hooks/ against (default: current directory).",
)
def show(event: str, project_dir: pathlib.Path) -> None:
    """Print the project's hook fragment for EVENT.

    EVENT is a plugin command name (e.g. chunk-complete). Prints the rendered
    fragment from docs/hooks/<EVENT>.md, or "(no project hook)" when the
    project defines none.

    Always exits 0. This command runs inside the context block of every
    lifecycle command; failing here would break commands unrelated to hooks.
    """
    project_hooks = Hooks(project_dir)
    click.echo(project_hooks.render(project_hooks.resolve(event)))


@hooks.command("list")
@click.option(
    "--project-dir",
    type=click.Path(path_type=pathlib.Path),
    default=".",
    help="Project root to resolve docs/hooks/ against (default: current directory).",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_hooks(project_dir: pathlib.Path, as_json: bool) -> None:
    """List the hook fragments defined by this project.

    Fragments whose filename matches no plugin command are flagged: they are
    well-formed and will simply never fire, which is this mechanism's primary
    failure mode.
    """
    fragments = Hooks(project_dir).list_fragments()

    if as_json:
        click.echo(
            json.dumps(
                [
                    {
                        "event": fragment.event,
                        "path": fragment.relative_path,
                        "known": known,
                    }
                    for fragment, known in fragments
                ],
                indent=2,
            )
        )
        return

    if not fragments:
        click.echo("No hooks defined (docs/hooks/ is empty or absent)")
        return

    for fragment, known in fragments:
        if known:
            click.echo(f"{fragment.relative_path}  {fragment.event}")
        else:
            click.echo(
                f"{fragment.relative_path}  {fragment.event}  "
                "UNKNOWN EVENT - matches no command, will never fire"
            )
