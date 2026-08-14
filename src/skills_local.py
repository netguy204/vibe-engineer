"""Opt-in reification of plugin skills into a consuming project.

# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/plugin_local_skills - Opt-in project-local skill reification

`reify_local_skills` renders the plugin's claude-flavor skill templates into a
project's `.claude/skills/<name>/SKILL.md` — the directory Claude Code scans
for project-scoped skills. This is the render channel DEC-010 reserved when it
rejected dual-mode distribution: the plugin remains the default (DEC-010
stands), the templates remain the single source of truth, and nothing here
runs unless an operator asks (DEC-015).

Ownership is explicit. `.claude/skills/.ve-local-skills.json` records which
skill directories ve rendered and at which version; re-runs overwrite owned
directories only, and a hand-made skill whose name collides is refused by
name, never clobbered.
"""

import json
import pathlib
import re
from dataclasses import dataclass, field

from plugin_render import (
    SKILLS_KIND,
    is_plugin_source_repo,
    output_path,
    render_plugin_template,
    templates_for_flavor,
)

# The local-reification marker, inserted immediately after the frontmatter of
# every rendered SKILL.md. Distinct from plugin_render.GENERATED_MARKER_PREFIX
# (which stays in the content and points at the template) and from the legacy
# AUTO-GENERATED header that project.py#_is_ve_generated_file keys on to
# delete legacy init-rendered files — this marker must never match either.
LOCAL_MARKER_PREFIX = "<!-- VE:LOCAL-SKILL "

MANIFEST_NAME = ".ve-local-skills.json"
MANIFEST_SCHEMA = 1

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _local_skills_dir(project_root: pathlib.Path) -> pathlib.Path:
    return project_root / ".claude" / "skills"


def _manifest_path(project_root: pathlib.Path) -> pathlib.Path:
    return _local_skills_dir(project_root) / MANIFEST_NAME


def _local_marker(version: str) -> str:
    return (
        f"{LOCAL_MARKER_PREFIX}rendered by `ve skills reify` at ve {version} — "
        f"edits here are lost on the next reify; the plugin remains the default "
        f"distribution channel (DEC-015). -->"
    )


def _skill_name(template_name: str) -> str:
    """skills/chunk-create.md.jinja2 -> chunk-create."""
    stem = pathlib.PurePosixPath(template_name).name
    for suffix in (".jinja2", ".md"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def _insert_marker(rendered: str, version: str) -> str:
    """Insert the local marker on its own line after the frontmatter block.

    Rendered skills always begin with a frontmatter block; if one is ever
    absent the marker goes first, which still reads correctly as a comment.
    """
    marker = _local_marker(version) + "\n"
    match = _FRONTMATTER_RE.match(rendered)
    if match:
        end = match.end()
        return rendered[:end] + marker + rendered[end:]
    return marker + rendered


def load_manifest(project_root: pathlib.Path) -> dict | None:
    """Return the parsed ownership manifest, or None when not opted in."""
    path = _manifest_path(project_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text())


@dataclass
class ReifyResult:
    root: pathlib.Path
    written: list[pathlib.Path] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)


def reify_local_skills(project_root: pathlib.Path, version: str) -> ReifyResult:
    """Render the claude-flavor plugin skills into project_root/.claude/skills.

    Raises ValueError when project_root is the plugin source repository: that
    repo's skills/ tree is the plugin build product, rendered by
    `ve plugin render`, and local reification there would shadow it.
    """
    project_root = pathlib.Path(project_root)
    if is_plugin_source_repo(project_root):
        raise ValueError(
            "this is the plugin source repository — skills/ here is the plugin "
            "build product (`ve plugin render`); local reification is for "
            "consuming projects"
        )

    skills_root = _local_skills_dir(project_root)
    manifest = load_manifest(project_root) or {
        "schema": MANIFEST_SCHEMA,
        "ve_version": version,
        "owned": [],
    }
    owned = set(manifest.get("owned", []))

    result = ReifyResult(root=skills_root)
    newly_owned: set[str] = set()

    for template_name in templates_for_flavor("claude"):
        parts = pathlib.PurePosixPath(template_name).parts
        if parts[0] != SKILLS_KIND:
            continue  # agents/ are subagent definitions, not .claude/skills content
        name = _skill_name(template_name)
        # output_path maps skills/<n>.md.jinja2 -> <root>/skills/<n>/SKILL.md;
        # our root is .claude/, so the rendered file lands in .claude/skills/.
        target = output_path(template_name, project_root / ".claude", "claude")

        if target.parent.is_dir() and name not in owned:
            result.refused.append(name)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_insert_marker(render_plugin_template(template_name), version))
        result.written.append(target)
        newly_owned.add(name)

    # Manifest last: a crash mid-run under-claims ownership, never over-claims.
    manifest["schema"] = MANIFEST_SCHEMA
    manifest["ve_version"] = version
    manifest["owned"] = sorted(owned | newly_owned)
    skills_root.mkdir(parents=True, exist_ok=True)
    _manifest_path(project_root).write_text(json.dumps(manifest, indent=2) + "\n")
    return result


@dataclass
class StatusResult:
    opted_in: bool
    rendered_version: str | None = None
    installed_version: str | None = None
    owned: list[str] = field(default_factory=list)

    @property
    def drifted(self) -> bool:
        return (
            self.opted_in
            and self.rendered_version is not None
            and self.rendered_version != self.installed_version
        )


def local_skills_status(project_root: pathlib.Path, version: str) -> StatusResult:
    """Report reification state for project_root against the installed version."""
    manifest = load_manifest(pathlib.Path(project_root))
    if manifest is None:
        return StatusResult(opted_in=False, installed_version=version)
    return StatusResult(
        opted_in=True,
        rendered_version=manifest.get("ve_version"),
        installed_version=version,
        owned=list(manifest.get("owned", [])),
    )
