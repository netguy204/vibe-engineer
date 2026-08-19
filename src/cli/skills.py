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
    """Render the plugin's skills into this project's .agents/skills/.

    Opt-in alternative to the vibe-engineer plugin for setups that cannot
    install it. Skills land in the standard agentskills.io layout
    (.agents/skills/<name>/SKILL.md) so any compliant harness can discover
    them; Claude Code finds them through a .claude/skills compatibility
    symlink. The plugin remains the default for Claude users: prefer
    `/plugin install vibe-engineer` in Claude Code when available. Re-running
    re-renders only the skills this command previously wrote (recorded in
    .agents/skills/.ve-local-skills.json); hand-made skills whose names
    collide are refused, never overwritten.
    """
    ver = _installed_version()
    try:
        result = reify_local_skills(project_dir, ver)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    for name in result.migrated:
        click.echo(f"Migrated {name} from .claude/skills/ to .agents/skills/")
    for path in result.written:
        click.echo(f"Wrote {path}")
    if result.symlink is not None:
        click.echo(f"Symlink {result.symlink} -> ../.agents/skills")
    for name in result.refused:
        click.echo(
            f"Refused {name}: .agents/skills/{name}/ exists and is not managed "
            f"by ve — rename or remove it if you want the ve version",
            err=True,
        )
    for warning in result.warnings:
        click.echo(f"Warning: {warning}", err=True)
    click.echo(f"Reified {len(result.written)} skill(s) at ve {ver}.")
    click.echo(
        "Notes: new skills are discovered at the next session start; "
        ".agents/skills/ serves any agentskills.io-compliant harness, and "
        "Claude Code reads it through the .claude/skills symlink — Cursor "
        "users install via .cursor-plugin. For Claude users the plugin "
        "remains the default distribution channel."
    )
    if result.refused:
        raise SystemExit(2)


@skills.command()
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(project_dir):
    """Report reified-skill state and version drift."""
    st = local_skills_status(project_dir, _installed_version())
    if not st.opted_in:
        click.echo("Not opted in: no .agents/skills/.ve-local-skills.json manifest.")
        return
    click.echo(f"Reified skills: {len(st.owned)}")
    click.echo(f"Rendered at ve {st.rendered_version}; installed ve {st.installed_version}")
    if st.drifted:
        click.echo("Drift: rendered version differs — run `ve skills reify` to refresh.")
    else:
        click.echo("Up to date.")
