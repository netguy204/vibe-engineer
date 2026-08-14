"""Opt-in reification of plugin skills into a consuming project.

# Subsystem: docs/subsystems/template_system - Unified template rendering
# Chunk: docs/chunks/plugin_local_skills - Opt-in project-local skill reification

`reify_local_skills` renders the plugin's claude-flavor skill templates into a
project's `.agents/skills/<name>/SKILL.md` — the agentskills.io layout that any
compliant harness discovers. Claude Code finds the same files through a
relative compatibility symlink `.claude/skills -> ../.agents/skills` (the same
symlink tradition the pre-DEC-010 `_init_skills` used for commands). This is
the render channel DEC-010 reserved when it rejected dual-mode distribution:
the plugin remains the default for Claude users (DEC-010 stands), the
templates remain the single source of truth, and nothing here runs unless an
operator asks (DEC-015, as amended).

Ownership is explicit. `.agents/skills/.ve-local-skills.json` records which
skill directories ve rendered and at which version; re-runs overwrite owned
directories only, and a hand-made skill whose name collides is refused by
name, never clobbered. A real `.claude/skills/` directory that ve does not own
is never replaced by the symlink.
"""

import json
import pathlib
import re
import shutil
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
    return project_root / ".agents" / "skills"


def _legacy_skills_dir(project_root: pathlib.Path) -> pathlib.Path:
    """The 0.6.0/0.7.0 destination, now only a compatibility symlink."""
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
    """Return the parsed ownership manifest, or None when not opted in.

    Reads the current `.agents/skills/` location first, then falls back to the
    legacy `.claude/skills/` location (0.6.0/0.7.0 renders) so already-reified
    projects still surface drift before they re-reify and migrate.
    """
    project_root = pathlib.Path(project_root)
    for path in (
        _manifest_path(project_root),
        _legacy_skills_dir(project_root) / MANIFEST_NAME,
    ):
        if path.is_file():
            return json.loads(path.read_text())
    return None


@dataclass
class ReifyResult:
    root: pathlib.Path
    written: list[pathlib.Path] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    migrated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    symlink: pathlib.Path | None = None


def _migrate_legacy_layout(
    project_root: pathlib.Path, result: ReifyResult
) -> bool:
    """Relocate a 0.6.0/0.7.0 `.claude/skills/` render to `.agents/skills/`.

    Returns True when `.claude/skills` is (or may become) available for the
    compatibility symlink, False when a real directory ve does not own stands
    in the way.
    """
    legacy = _legacy_skills_dir(project_root)
    if legacy.is_symlink() or not legacy.is_dir():
        return True

    legacy_manifest = legacy / MANIFEST_NAME
    if not legacy_manifest.is_file():
        # A real, hand-made .claude/skills/ — never ours to touch.
        result.warnings.append(
            f"{legacy} is a real directory not managed by ve; leaving it "
            f"untouched and skipping the compatibility symlink. Claude Code "
            f"will not see the reified skills in .agents/skills/ until the "
            f"collision is resolved (move or remove .claude/skills, then "
            f"re-run `ve skills reify`)."
        )
        return False

    try:
        owned = json.loads(legacy_manifest.read_text()).get("owned", [])
    except (json.JSONDecodeError, OSError):
        owned = []

    new_root = _local_skills_dir(project_root)
    new_root.mkdir(parents=True, exist_ok=True)
    for name in owned:
        src = legacy / name
        if not src.is_dir():
            continue
        dest = new_root / name
        if dest.exists():
            shutil.rmtree(src)  # both sides ve-owned; the render refreshes dest
        else:
            src.rename(dest)
        result.migrated.append(name)

    new_manifest = _manifest_path(project_root)
    if new_manifest.exists():
        legacy_manifest.unlink()
    else:
        legacy_manifest.rename(new_manifest)

    if any(legacy.iterdir()):
        # Hand-made skills shared the legacy directory; their home survives,
        # so the symlink cannot be placed.
        result.warnings.append(
            f"{legacy} still holds entries ve does not own; ve-owned skills "
            f"moved to .agents/skills/ but the compatibility symlink was "
            f"skipped. Claude Code will not see the reified skills until the "
            f"collision is resolved."
        )
        return False

    legacy.rmdir()
    return True


def _ensure_claude_symlink(
    project_root: pathlib.Path, result: ReifyResult
) -> None:
    """Point `.claude/skills` at `.agents/skills` for Claude Code discovery.

    Mirrors the pre-DEC-010 `_init_skills` convention: a relative symlink so
    the project stays relocatable, with `.claude/` created as a plain
    directory when absent. Never replaces a real directory.
    """
    link = _legacy_skills_dir(project_root)
    target = _local_skills_dir(project_root)

    if link.is_symlink():
        if link.resolve() == target.resolve():
            result.symlink = link
        else:
            result.warnings.append(
                f"{link} is a symlink pointing elsewhere; leaving it as-is. "
                f"Point it at ../.agents/skills for Claude Code discovery."
            )
        return
    if link.exists():
        # A real directory: _migrate_legacy_layout already warned.
        return

    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(pathlib.Path("..") / ".agents" / "skills")
    result.symlink = link


def reify_local_skills(project_root: pathlib.Path, version: str) -> ReifyResult:
    """Render the claude-flavor plugin skills into project_root/.agents/skills.

    Also maintains the `.claude/skills -> ../.agents/skills` compatibility
    symlink, and migrates a legacy `.claude/skills/` render (0.6.0/0.7.0) into
    the standard location first.

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
    result = ReifyResult(root=skills_root)
    symlink_ok = _migrate_legacy_layout(project_root, result)

    manifest = load_manifest(project_root) or {
        "schema": MANIFEST_SCHEMA,
        "ve_version": version,
        "owned": [],
    }
    owned = set(manifest.get("owned", []))
    newly_owned: set[str] = set()

    for template_name in templates_for_flavor("claude"):
        parts = pathlib.PurePosixPath(template_name).parts
        if parts[0] != SKILLS_KIND:
            continue  # agents/ are subagent definitions, not skills content
        name = _skill_name(template_name)
        # output_path maps skills/<n>.md.jinja2 -> <root>/skills/<n>/SKILL.md;
        # our root is .agents/, so the rendered file lands in .agents/skills/.
        target = output_path(template_name, project_root / ".agents", "claude")

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

    if symlink_ok:
        _ensure_claude_symlink(project_root, result)
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
