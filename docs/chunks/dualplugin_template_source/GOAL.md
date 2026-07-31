---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/plugin/partials/claude/idioms.md.jinja2
- src/templates/plugin/commands/ve-status.md.jinja2
- src/templates/plugin/commands/chunk-create.md.jinja2
- src/plugin_render.py
- src/cli/plugin.py
- src/cli/__init__.py
- commands/ve-status.md
- commands/chunk-create.md
- tests/test_plugin_render.py
- tests/test_plugin_commands.py
- docs/chunks/dualplugin_template_source/TEMPLATING_GUIDE.md
- tests/test_plugin_skills.py
code_references:
- ref: src/plugin_render.py#render_plugin_template
  implements: Single-template render with the flavor/source_template contract and
    trailing-newline normalization
- ref: src/plugin_render.py#list_plugin_templates
  implements: Collection discovery (partials excluded) that the drift test and CLI
    parametrize over
- ref: src/plugin_render.py#render_plugin_collection
  implements: Whole-collection render into the plugin source repo
- ref: src/plugin_render.py#is_plugin_source_repo
  implements: 'Render-target guard: only the repo carrying .claude-plugin/plugin.json'
- ref: src/cli/plugin.py#render
  implements: The `ve plugin render` command (Claude flavor)
- ref: src/templates/plugin/partials/claude/idioms.md.jinja2
  implements: "Claude idiom macros \u2014 the flavor-substitution interface (frontmatter,\
    \ generated_marker, probe, canonical_preamble, plugin_root)"
- ref: src/templates/plugin/commands/ve-status.md.jinja2
  implements: Pilot template with custom context probes
- ref: src/templates/plugin/commands/chunk-create.md.jinja2
  implements: Pilot template using the canonical preamble with task guidance via {%
    call %}
- ref: tests/test_plugin_render.py#TestDrift
  implements: 'Drift test: committed renders must match fresh renders byte-for-byte
    and carry the marker'
- ref: tests/test_plugin_render.py#TestRenderCli
  implements: 'CLI behavior: source-repo guard, render output, idempotence'
- ref: tests/test_plugin_skills.py
  implements: Marker collision guard
narrative: cursor_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- plugin_hook_cli_bootstrap
---
# Chunk Goal

## Minor Goal

A build-time template collection, `src/templates/plugin/`, is the single
source of truth for plugin command and skill content. Editor-specific idioms
live in substitutable partials — the context-probe preamble, the frontmatter
shape, and plugin-root environment references — so the same body renders into
multiple editor flavors. A `ve plugin render` command renders the Claude
flavor into `commands/`; committed renders carry a generated-from-template
marker pointing back at their template, and a drift test fails whenever a
committed render differs from a fresh render (stale after a template edit, or
hand-edited directly). Two pilots prove the layer: ve-status and chunk-create
render byte-identical to today's hand-maintained files, or with deliberate,
documented diffs.

## Context

- Narrative: docs/narratives/cursor_plugin_port. The operator's directive:
  build skills from templates with common idioms substituted differently for
  Claude and Cursor renderings. This chunk owns the layer and the Claude
  target; dualplugin_cursor_scaffold adds the Cursor target.
- The Claude idioms factored into partials
  (src/templates/plugin/partials/claude/idioms.md.jinja2): the canonical
  `## Context`/`## Runtime context` preamble (documented verbatim in
  docs/chunks/plugin_runtime_context/PORTING_GUIDE.md section 2),
  `allowed-tools` frontmatter, and `${CLAUDE_PLUGIN_ROOT}` references. The
  remaining 36 `commands/*.md` and 2 `agents/*.md` stay hand-maintained
  until dualplugin_content_migration moves them into the collection;
  docs/chunks/dualplugin_template_source/TEMPLATING_GUIDE.md is the recipe.
- The renderer (src/plugin_render.py) reuses src/template_system.py
  (`render_template`, collections under src/templates/) — there is no second
  renderer.
- Kind distinction (recorded in the rendered marker and command docs): the
  old `src/templates/commands/` collection (deleted by plugin_init_slimdown)
  rendered per-consuming-project at `ve init` time; this collection renders
  once, at build time, in this repository, and the outputs are COMMITTED —
  consuming repos still receive nothing. This is not a relitigation of
  DEC-010.
- Marker collision rule: `tests/test_plugin_commands.py` asserts commands do
  NOT contain "AUTO-GENERATED" (the old init-rendered header that
  `_is_ve_generated_file()` keys on for legacy cleanup — that string is
  never reused). The marker wording is "GENERATED from
  src/templates/plugin/<path> — edit that template and run `ve plugin
  render`; direct edits here will be overwritten."; the drift test requires
  it while the invariant tests keep rejecting the old header.
- Wheel interplay: pyproject's hatch force-include ships `commands/` as
  orchestrator phase-prompt package data. Renders being committed means the
  wheel build is unaffected; no render step at packaging time.

## Success Criteria

- `src/templates/plugin/` exists with the idiom partials factored out;
  `uv run ve plugin render` regenerates `commands/ve-status.md` and
  `commands/chunk-create.md` byte-identical to the committed files (any
  deliberate diff is documented in PLAN.md Deviations and committed as part
  of this chunk).
- Rendered files carry the new generated-marker comment; the drift test
  fails on (a) template edited without re-render and (b) render hand-edited.
- The invariant suites (test_plugin_commands.py, test_plugin_agents.py,
  test_plugin_manifest.py, test_session_hook.py) pass with the marker-test
  adjustment.
- The render command's collection layout and partial vocabulary are
  documented well enough that dualplugin_content_migration can migrate the
  remaining 36 commands mechanically.
