---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/skills_local.py
- src/cli/skills.py
- src/cli/__init__.py
- src/integrity.py
- docs/trunk/DECISIONS.md
- tests/test_skills_local.py
code_references:
- ref: src/skills_local.py#reify_local_skills
  implements: Opt-in render of the claude-flavor plugin skill templates into a consuming
    project's .agents/skills/ (agentskills.io layout), refusing the plugin source repo
    and any name-colliding directory the ownership manifest does not record; manifest
    written last so a crash under-claims ownership rather than over-claims; maintains
    the .claude/skills compatibility symlink and migrates a legacy .claude/skills/
    render in place, never replacing a real directory ve does not own.
- ref: src/skills_local.py#local_skills_status
  implements: Drift reporting between the manifest's rendering version and the installed
    CLI.
- ref: src/cli/skills.py#reify
  implements: User-facing opt-in path; prints migrations, every path written, the
    symlink, per-name refusals (exit 2), warnings, and the platform notes (next-session
    discovery, any agentskills.io-compliant harness served from .agents/skills/ with
    Claude Code reading through the symlink, Cursor served by .cursor-plugin instead,
    plugin remains the default for Claude users).
- ref: src/cli/skills.py#status
  implements: Reified-state and drift report for operators.
- ref: src/integrity.py#IntegrityValidator::_validate_local_skills_stale
  implements: "skills\u2192stale warning when reified skills were rendered by an older\
    \ ve \u2014 warning not error so a release day does not fail every opted-in project;\
    \ silent without the opt-in manifest; no network."
- ref: src/templates/claude/AGENTS.md.jinja2
  implements: "The one-sentence discoverability pointer in the managed block's Workflow\
    \ Commands section \u2014 the surface an agent without skills is guaranteed to\
    \ read \u2014 naming `uvx --from vibe-engineer ve skills reify` as the opt-in\
    \ fallback when the plugin cannot be installed."
- ref: tests/test_skills_local.py
  implements: 'Contract pins: render/marker/manifest shape, idempotency, collision
    refusal, plugin-source-repo refusal, compatibility-symlink creation and refusal
    to replace a real unowned .claude/skills, legacy-layout migration, outside-writes
    canary, drift statuses, validator warning volume, CLI output including platform
    notes.'
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- dualplugin_cursor_scaffold
- external_never_resolved
---
# Chunk Goal

## Minor Goal

A project can **opt in** to project-local reified skills: `ve skills reify`
renders the plugin's skill templates into the project's
`.agents/skills/<name>/SKILL.md` — the standard agentskills.io layout that
any compliant harness discovers — and maintains a relative compatibility
symlink `.claude/skills -> ../.agents/skills` so Claude Code finds the same
files (the symlink tradition the pre-DEC-010 `_init_skills` established).
The plugin remains the default distribution channel for Claude users; nothing
renders unless the operator runs the command, and the one place the docs
mention the alternative says exactly that.

The render source is the **same template collection the plugin is built from**
— `src/templates/plugin/skills/*.md.jinja2`, rendered claude-flavor through
`plugin_render.render_plugin_template`. The templates ship inside the installed
wheel (hatch `only-include = ["src"]`), so a consuming project's installed `ve`
renders them with no checkout of this repository. This is the render channel
DEC-010 reserved when it rejected dual-mode distribution: DEC-010's objection
was two *sources of truth*, and there is still exactly one — the committed
plugin files and the reified local skills are both build products of the same
templates. A new ADR records the reintroduction as opt-in and single-source.

**Ownership contract.** `.agents/skills/.ve-local-skills.json` records which
skill directories ve owns and the ve version that rendered them. Re-running
`reify` overwrites owned files only; a hand-made skill whose name collides is
refused by name and reported, never clobbered. Every rendered SKILL.md carries
a managed-marker HTML comment immediately after its frontmatter naming the
re-render command — the same contract the AGENTS.md managed block makes, at
file granularity. The marker is a comment, not a frontmatter key, because the
frontmatter schema belongs to Claude Code, not to ve.

**Drift surfacing.** `ve skills status` reports what is reified and whether the
recorded version differs from the installed CLI. `ve validate` warns (link_type
`skills→stale`, warning not error, same shape as `external→never-resolved`)
when reified skills exist at a version older than the installed CLI, naming
`ve skills reify` as the fix. A warning because stale skills are degraded, not
broken, and an error would fail every project on the day after a ve release.

**Safety lines, test-enforced.** The command writes only under the target
project's `.agents/skills/`, plus the single `.claude/skills` compatibility
symlink (and the legacy-layout migration that moves ve-owned content between
those two places). It never replaces a real `.claude/skills/` directory it
does not own — it warns and skips the symlink instead. It never touches
`~/.claude` (user scope), never touches plugin caches (`~/.claude/plugins/...`
— DEC-013's user-managed line), and never writes into the `skills/` directory
at a repository root (that is the plugin build product in this repo). It
prints every path it writes.

## Success Criteria

- `ve skills reify` in a ve-initialized project creates
  `.agents/skills/<name>/SKILL.md` for every claude-flavor plugin skill
  template, each with valid YAML frontmatter and the managed marker after it,
  plus the ownership manifest, plus the relative `.claude/skills ->
  ../.agents/skills` symlink. Output lists every file written and the
  symlink.
- A real `.claude/skills/` directory ve does not own is left untouched: the
  render still lands in `.agents/skills/`, the symlink is skipped, and the
  output warns that Claude Code will not see the reified skills until the
  collision is resolved.
- A legacy `.claude/skills/` render (0.6.0/0.7.0, identified by our manifest)
  is migrated: ve-owned skill directories and the manifest relocate to
  `.agents/skills/`, the symlink replaces the emptied directory, and the
  output reports what moved.
- Running `reify` twice is idempotent; running it after a version bump
  re-renders owned files in place.
- A pre-existing `.agents/skills/<name>/` NOT in the manifest is refused by
  name; the run reports it and continues with the rest (no partial clobber, no
  abort of the unaffected skills).
- `ve skills status` reports reified skill count, rendering version, installed
  version, and names drift when they differ.
- `ve validate` emits one `skills→stale` warning when the manifest version ≠
  installed version, silent otherwise, and performs no network access.
  Warning text names `ve skills reify`.
- No file outside the target project's `.agents/skills/` — plus the one
  `.claude/skills` symlink — is written by any code path in this chunk
  (tested with a canary layout).
- The reify output states the platform notes: skills discovered at next
  session start, `.agents/skills/` serving any agentskills.io-compliant
  harness with Claude Code reading through the symlink, and Cursor not served
  by this mechanism (`.cursor-plugin` is that route).
- `uv run ve validate` exits zero; full suite passes.

## Rejected Ideas

### `.claude/skills` as the destination

Rejected after one day live: it made the feature Claude-only, which
contradicted its own motivation — the requirement that revived this render
channel was harnesses where the plugin cannot be installed. The standard
directory (`.agents/skills/`, agentskills.io layout) plus a Claude
compatibility symlink serves every compliant harness at the same cost.

### A `--local-skills` flag on `ve init`

The operator's request named an "initialization path", and an init flag is its
natural shape. Deferred, not rejected on principle: `src/cli/init_cmd.py`
carries uncommitted in-flight operator work (crossref_declaration_union), and
this chunk refuses to entangle its diff with that file. The standalone command
is the durable mechanism; the init flag is a ~5-line follow-up once init_cmd.py
is free, and was flagged to the operator in the coordination room at the time.

### Copy the packaged pre-rendered skills instead of rendering templates

The wheel force-includes the rendered `skills/` as `orchestrator/skills`, so
copying them would avoid Jinja at runtime. Rejected: that path is an internal
packaging detail of the orchestrator (docs/chunks/plugin_legacy_migration),
its content is the claude flavor frozen at package-build time, and copying
sidesteps the marker-injection and flavor-selection seams. Rendering through
`render_plugin_template` keeps one code path for every consumer of the
templates.

### Auto-reify when no plugin is detected

Rejected: the operator's request says "explicit alternative only when a project
requests them", and detection would be wrong in both directions — the CLI
cannot see another harness's plugin state reliably, and a false positive
silently converts a plugin project into a dual-channel one. Opt-in is the
product, not a limitation.

### Write skills to `~/.claude/skills` (user scope)

Rejected: crosses from "this project" to "everything this user does" without
the project boundary that makes review possible, and violates the DEC-013
spirit that user-managed surfaces are warned about, never modified.

### Make the stale-skills finding an error

Rejected: every reified project would fail validation the day after a ve
release, which trains people to skip the gate (the same reasoning as
external_never_resolved's warning-not-error decision).

### A frontmatter key as the managed marker

Rejected: the SKILL.md frontmatter schema belongs to Claude Code; adding keys
to it couples ve to that schema's tolerance for unknown fields. An HTML comment
after the frontmatter is invisible to the harness and survives schema changes.
