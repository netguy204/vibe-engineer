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
FLAVORS = ("claude", "cursor")

DEFAULT_FLAVOR = "claude"

# Template subdirectory whose renders take the agentskills.io per-skill layout.
SKILLS_KIND = "skills"

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

# Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor render target
# Per-flavor manifest whose presence marks a valid render target. Each flavor
# guards on its own manifest: rendering the cursor flavor into a repo that
# only ships the Claude plugin would scaffold a .cursor-plugin/skills/ tree
# nobody declared.
FLAVOR_MANIFESTS = {
    "claude": PLUGIN_MANIFEST_RELPATH,
    "cursor": pathlib.PurePosixPath(".cursor-plugin/plugin.json"),
}

# Chunk: docs/chunks/dualplugin_cursor_scaffold - Flavor-specific output roots
# Directory under repo_root that a flavor's renders live in. Claude's is the
# repo root itself because Claude Code requires plugin content at the plugin
# root (skills/, agents/). Cursor's cannot also be the repo root: the two
# flavors would then write the same skills/<name>/SKILL.md and one would
# clobber the other. Cursor's manifest names .cursor-plugin/ explicitly,
# which per the Cursor spec replaces folder discovery — so Cursor reads the
# Cursor render and never sees the Claude one.
FLAVOR_OUTPUT_ROOTS = {
    "claude": "",
    "cursor": ".cursor-plugin",
}

# Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor pilot scope boundary
# The Cursor flavor renders only these templates. dualplugin_cursor_scaffold
# proves the render target and the Cursor idiom partial on two pilots;
# rendering the full surface is dualplugin_cursor_render's job. That chunk
# removes this restriction by deleting the entry below, at which point
# templates_for_flavor returns the whole collection for every flavor.
FLAVOR_TEMPLATE_SUBSETS = {
    "cursor": (
        "skills/chunk-create.md.jinja2",
        "skills/ve-status.md.jinja2",
    ),
}


def plugin_collection_dir() -> pathlib.Path:
    """Return the root directory of the plugin template collection."""
    return template_dir / PLUGIN_COLLECTION


def list_plugin_templates() -> list[str]:
    """List collection-relative template names, partials excluded.

    Returns names like "skills/ve-status.md.jinja2", sorted. The first path
    component is the output kind: skills/ renders into the per-skill
    agentskills.io layout, agents/ renders in place.
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


# Chunk: docs/chunks/dualplugin_cursor_scaffold - Per-flavor template subsets
def templates_for_flavor(flavor: str = DEFAULT_FLAVOR) -> list[str]:
    """List the collection templates a flavor renders.

    Every flavor renders the whole collection unless FLAVOR_TEMPLATE_SUBSETS
    restricts it. A subset entry is a deliberate, temporary scope boundary
    (see the Cursor entry there), never a permanent difference in surface:
    the point of the collection is that both flavors carry the same content.
    """
    names = list_plugin_templates()
    subset = FLAVOR_TEMPLATE_SUBSETS.get(flavor)
    if subset is None:
        return names
    allowed = set(subset)
    return [name for name in names if name in allowed]


def output_path(
    template_name: str, repo_root: pathlib.Path, flavor: str = DEFAULT_FLAVOR
) -> pathlib.Path:
    """Map a collection-relative template name to its committed render path.

    Skills land in the agentskills.io layout — one directory per skill, content
    in SKILL.md — which is the portable shape a non-Claude harness can consume.
    The flavor selects the output root (FLAVOR_OUTPUT_ROOTS), so the two
    flavors never write the same file:

    claude, "skills/ve-status.md.jinja2"
        -> <repo_root>/skills/ve-status/SKILL.md
    claude, "agents/chunk-executor.md.jinja2"
        -> <repo_root>/agents/chunk-executor.md
    cursor, "skills/ve-status.md.jinja2"
        -> <repo_root>/.cursor-plugin/skills/ve-status/SKILL.md
    """
    rel = template_name
    if rel.endswith(".jinja2"):
        rel = rel[: -len(".jinja2")]
    parts = pathlib.PurePosixPath(rel).parts
    root = repo_root
    output_root = FLAVOR_OUTPUT_ROOTS.get(flavor, "")
    if output_root:
        root = root / output_root
    if parts[0] == SKILLS_KIND:
        name = pathlib.PurePosixPath(parts[-1]).stem
        return root / SKILLS_KIND / name / "SKILL.md"
    return root.joinpath(*parts)


def render_plugin_template(template_name: str, flavor: str = DEFAULT_FLAVOR) -> str:
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


def flavor_manifest_relpath(flavor: str = DEFAULT_FLAVOR) -> pathlib.PurePosixPath:
    """Return the manifest whose presence marks a render target for `flavor`."""
    return FLAVOR_MANIFESTS.get(flavor, PLUGIN_MANIFEST_RELPATH)


def is_plugin_source_repo(
    repo_root: pathlib.Path, flavor: str = DEFAULT_FLAVOR
) -> bool:
    """True if repo_root is the plugin source repository for `flavor`.

    `ve plugin render` must never scaffold a skills/ tree in a consuming
    project; only the repo carrying the flavor's plugin manifest
    (.claude-plugin/plugin.json, .cursor-plugin/plugin.json) is a valid
    render target for that flavor.
    """
    relpath = flavor_manifest_relpath(flavor)
    return repo_root.joinpath(*relpath.parts).is_file()


def render_plugin_collection(
    repo_root: pathlib.Path, flavor: str = DEFAULT_FLAVOR
) -> list[pathlib.Path]:
    """Render the flavor's templates into repo_root; return written paths."""
    written = []
    for template_name in templates_for_flavor(flavor):
        out = output_path(template_name, repo_root, flavor)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_plugin_template(template_name, flavor))
        written.append(out)
    return written
