"""Plugin command group.

# Chunk: docs/chunks/dualplugin_template_source - ve plugin render CLI

Build-time commands for the plugin source repository. These operate on the
repo that ships the Claude Code plugin (the one carrying
.claude-plugin/plugin.json), not on consuming projects.
"""

import pathlib

import click

import plugin_render


@click.group()
def plugin():
    """Manage the plugin source tree (build-time rendering)."""
    pass


# Chunk: docs/chunks/dualplugin_template_source - Render committed plugin files from templates
@plugin.command("render")
@click.option(
    "--flavor",
    type=click.Choice(plugin_render.FLAVORS),
    default="claude",
    show_default=True,
    help="Editor flavor to render.",
)
def render(flavor: str) -> None:
    """Render src/templates/plugin/ into the committed plugin files.

    Renders every template in the plugin collection (currently into
    commands/). Run from the root of the plugin source repository after
    editing a template; commit the regenerated files. The drift test
    (tests/test_plugin_render.py) fails until committed renders match the
    templates.
    """
    repo_root = pathlib.Path.cwd()
    if not plugin_render.is_plugin_source_repo(repo_root):
        raise click.ClickException(
            "not a plugin source repository: "
            f"{plugin_render.PLUGIN_MANIFEST_RELPATH} not found under "
            f"{repo_root}. `ve plugin render` regenerates the committed "
            "plugin files and only runs in the repo that ships the plugin."
        )

    written = plugin_render.render_plugin_collection(repo_root, flavor=flavor)
    if not written:
        click.echo("No templates found in the plugin collection.")
        return
    for path in written:
        click.echo(f"rendered {path.relative_to(repo_root)}")
    click.echo(f"{len(written)} file(s) rendered ({flavor} flavor).")
