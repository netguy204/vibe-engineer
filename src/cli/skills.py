"""Skills command group — opt-in project-local skill reification.

# Chunk: docs/chunks/plugin_local_skills - Opt-in project-local skill reification
"""

import pathlib
from importlib.metadata import PackageNotFoundError, version as package_version

import click

from skills_local import local_skills_status, reify_local_skills


def _installed_version() -> str:
    try:
        return package_version("vibe-engineer")
    except PackageNotFoundError:
        return "unknown"


@click.group()
def skills():
    """Project-local skill reification (opt-in; the plugin is the default)."""


@skills.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def reify(project_dir):
    """Render the plugin's skills into this project's .claude/skills/.

    Opt-in alternative to the vibe-engineer plugin for setups that cannot
    install it. The plugin remains the default: prefer `/plugin install
    vibe-engineer` in Claude Code when available. Re-running re-renders only
    the skills this command previously wrote (recorded in
    .claude/skills/.ve-local-skills.json); hand-made skills whose names
    collide are refused, never overwritten.
    """
    ver = _installed_version()
    try:
        result = reify_local_skills(project_dir, ver)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    for path in result.written:
        click.echo(f"Wrote {path}")
    for name in result.refused:
        click.echo(
            f"Refused {name}: .claude/skills/{name}/ exists and is not managed "
            f"by ve — rename or remove it if you want the ve version",
            err=True,
        )
    click.echo(f"Reified {len(result.written)} skill(s) at ve {ver}.")
    click.echo(
        "Notes: new skills are discovered at the next session start; this "
        "serves Claude Code only — Cursor users install via .cursor-plugin. "
        "The plugin remains the default distribution channel."
    )
    if result.refused:
        raise SystemExit(2)


@skills.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(project_dir):
    """Report reified-skill state and version drift."""
    st = local_skills_status(project_dir, _installed_version())
    if not st.opted_in:
        click.echo("Not opted in: no .claude/skills/.ve-local-skills.json manifest.")
        return
    click.echo(f"Reified skills: {len(st.owned)}")
    click.echo(f"Rendered at ve {st.rendered_version}; installed ve {st.installed_version}")
    if st.drifted:
        click.echo("Drift: rendered version differs — run `ve skills reify` to refresh.")
    else:
        click.echo("Up to date.")
