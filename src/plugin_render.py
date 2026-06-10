"""Build-time rendering of the plugin source tree from src/templates/plugin/.

The src/templates/plugin/ collection is the single source of truth for plugin
command content. Editor-specific idioms (context-probe preamble, frontmatter
shape, plugin-root references) live in per-flavor partials
(partials/<flavor>/idioms.md.jinja2); each template imports the partial named
by the `flavor` render variable, so the same body renders into multiple
editor flavors.

Unlike the old src/templates/commands/ collection (deleted by
plugin_init_slimdown), which rendered per-consuming-project at `ve init`
time, this collection renders once, at build time, in the plugin source
repository, and the outputs are COMMITTED. Consuming repos receive nothing
(DEC-010 stands). tests/test_plugin_render.py keeps the committed renders in
lockstep with the templates.
"""
# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/dualplugin_template_source - Build-time plugin template collection and renderer

import pathlib

from constants import template_dir
from template_system import render_template

PLUGIN_COLLECTION = "plugin"

# Flavors with an idiom partial at partials/<flavor>/idioms.md.jinja2.
# dualplugin_cursor_scaffold adds "cursor".
FLAVORS = ("claude",)

# Marker carried by every rendered file, pointing back at its template. The
# marker text the templates emit (via the generated_marker idiom macro) must
# start with this prefix so the drift test can require it. Deliberately
# distinct from the legacy "AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY"
# header: src/project.py#_is_ve_generated_file keys on that string to delete
# legacy init-rendered files, and the plugin invariant tests reject it.
# Build-time renders are committed source, not per-project render output.
GENERATED_MARKER_PREFIX = "<!-- GENERATED from "

# Presence of this file marks the plugin source repository (render target).
PLUGIN_MANIFEST_RELPATH = pathlib.PurePosixPath(".claude-plugin/plugin.json")


def plugin_collection_dir() -> pathlib.Path:
    """Return the root directory of the plugin template collection."""
    return template_dir / PLUGIN_COLLECTION


def list_plugin_templates() -> list[str]:
    """List collection-relative template names, partials excluded.

    Returns names like "commands/ve-status.md.jinja2", sorted. Subdirectories
    map output kinds (commands/ today; agents/ arrives with
    dualplugin_content_migration).
    """
    root = plugin_collection_dir()
    if not root.exists():
        return []
    names = []
    for path in sorted(root.rglob("*.jinja2")):
        rel = path.relative_to(root)
        if rel.parts[0] == "partials":
            continue
        names.append(rel.as_posix())
    return names


def output_path(template_name: str, repo_root: pathlib.Path) -> pathlib.Path:
    """Map a collection-relative template name to its committed render path.

    "commands/ve-status.md.jinja2" -> <repo_root>/commands/ve-status.md
    """
    rel = template_name
    if rel.endswith(".jinja2"):
        rel = rel[: -len(".jinja2")]
    return repo_root.joinpath(*pathlib.PurePosixPath(rel).parts)


def render_plugin_template(template_name: str, flavor: str = "claude") -> str:
    """Render one collection template in the given flavor.

    Passes the two-variable render contract every template relies on:
    `flavor` (selects the idiom partial) and `source_template` (the
    repo-relative template path the generated marker points at). Output is
    normalized to end with exactly one trailing newline so renders are
    byte-stable.
    """
    rendered = render_template(
        PLUGIN_COLLECTION,
        template_name,
        flavor=flavor,
        source_template=f"src/templates/plugin/{template_name}",
    )
    return rendered.rstrip("\n") + "\n"


def is_plugin_source_repo(repo_root: pathlib.Path) -> bool:
    """True if repo_root is the plugin source repository (render target guard).

    `ve plugin render` must never scaffold a commands/ tree in a consuming
    project; only the repo carrying .claude-plugin/plugin.json is a valid
    render target.
    """
    return repo_root.joinpath(*PLUGIN_MANIFEST_RELPATH.parts).is_file()


def render_plugin_collection(
    repo_root: pathlib.Path, flavor: str = "claude"
) -> list[pathlib.Path]:
    """Render every collection template into repo_root; return written paths."""
    written = []
    for template_name in list_plugin_templates():
        out = output_path(template_name, repo_root)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_plugin_template(template_name, flavor))
        written.append(out)
    return written
