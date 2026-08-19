---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- .cursor-plugin/plugin.json
- .cursor-plugin/marketplace.json
- .cursor-plugin/skills/ve-status/SKILL.md
- .cursor-plugin/skills/chunk-create/SKILL.md
- src/plugin_render.py
- src/cli/plugin.py
- src/templates/plugin/partials/cursor/idioms.md.jinja2
- tests/test_cursor_manifest.py
- tests/test_plugin_render.py
- tests/test_session_hook.py
- tests/fixtures/cursor_plugin_schemas/plugin.schema.json
- tests/fixtures/cursor_plugin_schemas/marketplace.schema.json
- docs/trunk/DECISIONS.md
- pyproject.toml
code_references:
- ref: .cursor-plugin/plugin.json
  implements: Cursor plugin manifest; explicit skills/agents/hooks paths override
    folder discovery so Cursor never reads the Claude build product
- ref: .cursor-plugin/marketplace.json
  implements: Single-entry marketplace pointing at the repo root, mirroring .claude-plugin/marketplace.json
- ref: .cursor-plugin/README.md
  implements: 'Rationale the JSON manifests cannot carry: why the component paths
    are explicit and hooks is empty'
- ref: .cursor-plugin/skills/ve-status/SKILL.md
  implements: Cursor pilot render (ad-hoc probe block path)
- ref: .cursor-plugin/skills/chunk-create/SKILL.md
  implements: Cursor pilot render (canonical preamble and arguments-idiom path)
- ref: src/templates/plugin/partials/cursor/idioms.md.jinja2
  implements: 'Cursor half of the flavor-substitution interface: probes become agent-run
    instructions, allowed-tools dropped, $ARGUMENTS mapped'
- ref: src/templates/plugin/partials/claude/idioms.md.jinja2
  implements: Claude half extended with probe_intro and arguments macros so both flavors
    share one interface
- ref: src/plugin_render.py#FLAVOR_MANIFESTS
  implements: 'Per-flavor render-target guard: each flavor keys on its own plugin
    manifest'
- ref: src/plugin_render.py#FLAVOR_OUTPUT_ROOTS
  implements: Cursor renders to .cursor-plugin/ so the two flavors never write the
    same file
- ref: src/plugin_render.py#FLAVOR_TEMPLATE_SUBSETS
  implements: Cursor pilot scope boundary; dualplugin_cursor_render removes it
- ref: src/plugin_render.py#templates_for_flavor
  implements: Template selection per flavor
- ref: src/plugin_render.py#output_path
  implements: Flavor-aware mapping from template name to committed render path
- ref: src/plugin_render.py#flavor_manifest_relpath
  implements: Manifest lookup used by the render-target guard and its error message
- ref: src/plugin_render.py#is_plugin_source_repo
  implements: Refuses to scaffold a flavor's tree into a repo that does not ship that
    flavor
- ref: src/cli/plugin.py#render
  implements: '`ve plugin render --flavor cursor` entry point and per-flavor guard
    message'
- ref: tests/test_cursor_manifest.py#TestDiscoveryCollision
  implements: 'Success criterion: manifests steer Cursor away from Claude content;
    guards the explicit-path overrides'
- ref: tests/test_cursor_manifest.py#TestPluginManifest
  implements: 'Success criterion: manifests validate against the current cursor/plugins
    spec'
- ref: tests/test_cursor_manifest.py#TestPilotRender
  implements: 'Success criterion: pilot renders carry no Jinja2 residue and no Claude-only
    idioms'
- ref: tests/test_plugin_render.py#TestCursorDrift
  implements: Committed Cursor renders stay in lockstep with their templates
- ref: tests/test_plugin_render.py#TestCursorScope
  implements: The Cursor pilot boundary is explicit and its entries name real templates
- ref: tests/test_session_hook.py#TestVersionSource::test_plugin_and_package_versions_are_coupled
  implements: 'Success criterion: version equality across all three manifests, naming
    whichever drifts'
- ref: tests/test_session_hook.py#TestVersionSource::test_every_shipped_plugin_manifest_is_co_versioned
  implements: A fourth ecosystem cannot ship a manifest without joining the co-versioning
    policy
- ref: tests/fixtures/cursor_plugin_schemas/PROVENANCE.md
  implements: Provenance and refresh instructions for the vendored upstream Cursor
    schemas
narrative: cursor_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- dualplugin_template_source
created_after:
- plugin_hook_cli_bootstrap
---

# Chunk Goal

## Minor Goal

The repository is also a Cursor plugin. `.cursor-plugin/plugin.json` and
`.cursor-plugin/marketplace.json` validate against the cursor/plugins
schemas, and `ve plugin render --flavor cursor` renders the pilot content
(ve-status, chunk-create) from the same templates the Claude flavor uses,
substituting Cursor idiom partials. DEC-014 records the dual-ecosystem
decision, and DEC-011's co-versioning covers all three manifests —
pyproject.toml, .claude-plugin/plugin.json, .cursor-plugin/plugin.json —
test-enforced.

## Context

- Cursor plugin facts, verified against the live spec on 2026-08-07
  (github.com/cursor/plugins schemas at commit `0701892`, vendored under
  `tests/fixtures/cursor_plugin_schemas/`, plus
  cursor.com/docs/reference/plugins): the manifest is
  `.cursor-plugin/plugin.json`, requiring only a kebab-case `name` and
  permitting no keys outside its documented set (`additionalProperties:
  false`). `author` is an **object** `{name, email}`, not a string.
  `.cursor-plugin/marketplace.json` indexes plugins in a repository.
  Components are skills (`skills/<name>/SKILL.md`, the cross-agent
  standard), commands, rules (`.mdc`), agents, hooks, and MCP servers.
- Two June 2026 recollections did not survive verification and are not
  relied on: there is no `/add-plugin` command in current Cursor (install
  paths are the Customize page, cursor.com/marketplace, and team
  marketplaces imported from a repository), and Cursor's client versions
  are 3.x rather than 2.4/2.6, so the manifest declares no
  `minClientVersions` floor rather than guess one.
- Content ships as SKILL.md skills rather than Cursor commands: it is the
  cross-agent standard, it matches the layout the Claude flavor already
  uses, and Cursor's docs state a Claude Code skill loads unmodified.
- Cursor idiom partials substitute for the Claude ones. Cursor has no `!`
  preprocessing, so probes become explicit "run these first" instructions
  carrying the same commands, the same fallback chains, and the same
  Runtime context interpretation guidance — the agent runs them instead of
  the harness. `allowed-tools` is dropped, `$CLAUDE_PLUGIN_ROOT` maps to
  `${PLUGIN_ROOT}`, and `$ARGUMENTS` maps to a pointer at the request that
  invoked the skill, since Cursor has no argument string to substitute.
- Component discovery is folder-based by default, which makes this
  repository's dual nature hazardous: its root already holds the Claude
  build product at `skills/`, `agents/`, and `hooks/hooks.json`. The Cursor
  manifest therefore names those component paths explicitly — a specified
  path replaces folder discovery — so Cursor reads `.cursor-plugin/` and
  never the Claude tree.
- Live verification remains open. Static rendering is not sufficient; the
  pilot must be exercised in a real Cursor session. The implementing agent
  cannot drive Cursor, so `CURSOR_VERIFICATION.md` in this chunk directory
  is the operator script (install, expected component inventory, both
  skills, and the three schema-valid-but-unconfirmed behaviors to check),
  and operator confirmation is the verification gate.
- DEC-014 records dual-ecosystem distribution from one template source and
  triple co-versioning, enforced by
  `tests/test_session_hook.py::TestVersionSource`. Plugin managers key
  update detection to manifest versions, so all three bump together (see
  DEC-011 and the 0.3.0 release).

## Success Criteria

- `.cursor-plugin/plugin.json` and `marketplace.json` validate against the
  current cursor/plugins spec; the Cursor render of ve-status and
  chunk-create emits into the spec's expected layout with no Jinja2 residue
  and no Claude-only idioms (`!` backtick lines, allowed-tools).
- A documented operator verification script exists and the pilot has been
  confirmed working in a live Cursor session (or the chunk's review
  ESCALATEs pending that confirmation rather than approving on static
  checks alone).

  **Status: partially met, deliberately.** The script exists at
  `CURSOR_VERIFICATION.md` and everything statically checkable is checked,
  but no live Cursor session has run it. Three behaviors are schema-valid
  and doc-consistent yet unconfirmed against a client: `"hooks": {}`
  suppressing folder discovery, component paths pointing inside the
  `.cursor-plugin/` dot-directory, and a marketplace entry with
  `"source": "./"` sitting beside a `plugin.json` in the same directory.
  Per this criterion's own terms, that is an ESCALATE, not an approval.
- DEC-014 recorded; the version-equality test covers all three manifests
  and fails if any one drifts.
