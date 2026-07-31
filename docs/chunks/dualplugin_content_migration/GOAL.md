---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/plugin/skills
- src/templates/plugin/agents/
- skills/
- agents/
- tests/test_plugin_render.py
- docs/chunks/dualplugin_content_migration/migrate_templates.py
code_references:
- ref: src/templates/plugin/skills/chunk-plan.md.jinja2
  implements: "Representative of the 34 command templates using the canonical preamble (8 with {% call %} task-workspace bullets, 26 plain)"
- ref: src/templates/plugin/skills/chunk-commit.md.jinja2
  implements: "Representative of the nonstandard-context class (chunk-commit, chunk-execute-all): own ## Context heading with idioms.probe per probe line"
- ref: src/templates/plugin/agents/chunk-executor.md.jinja2
  implements: "Agent template with literal frontmatter (tools: key is outside the five-macro flavor interface) and generated marker"
- ref: src/templates/plugin/agents/intent-auditor.md.jinja2
  implements: "Second agent template; body verbatim, pinned protocol rules preserved"
- ref: tests/test_plugin_render.py#TestCollectionLayout::test_collection_covers_every_committed_render
  implements: "1:1 completeness between collection templates and committed commands/agents renders in both directions"
- ref: tests/test_plugin_render.py#TestCollectionLayout::test_collection_spans_full_plugin_surface
  implements: "Pins the full surface: 38 command templates and both agent templates"
- ref: docs/chunks/dualplugin_content_migration/migrate_templates.py#migrate
  implements: "One-time self-verifying migration: derives templates from committed renders, aborts on any diff beyond the inserted marker"
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

Every piece of plugin content exists exactly once, in
`src/templates/plugin/`: the 36 commands beyond the two pilots, plus both
agents (chunk-executor, intent-auditor), all render from templates.
`commands/` and `agents/` are build products of `ve plugin render`, each file
carries the generated-from-template marker, and the drift test covers the
entire surface — a hand edit to any rendered file fails the suite.

## Context

- Builds on dualplugin_template_source's collection layout, partials, and
  marker convention; follow its documentation mechanically.
- Migration standard: each command's Claude render must be byte-identical to
  the committed file, or the diff is deliberate and documented. The shared
  canonical preamble should collapse into the preamble partial; per-command
  variation to preserve faithfully includes: task-workspace guidance blocks
  (chunk-create, chunk-complete step 15, investigation-create), chunk-commit
  and chunk-rebase's extra git/pytest `allowed-tools`, chunk-review's
  verbatim ReviewDecision references, steward/swarm commands'
  target-project channel-naming guidance, and every chunk backreference
  HTML comment (they are load-bearing for `ve validate`).
- Agents: tests/test_plugin_agents.py pins chunk-executor's lifecycle text
  ("/chunk-plan" … "3 times maximum", SUCCESS/FAILURE contract) and both
  agents' backreference comments — renders must keep those invariants.
- After this chunk the contributor docs story changes (edit template, not
  render); the full write-up lands in dualplugin_lifecycle_release, but the
  generated markers must already point contributors at the right place.

## Success Criteria

- All 38 commands and 2 agents regenerate from `uv run ve plugin render`
  with zero diff against the committed tree (deliberate diffs documented in
  PLAN.md Deviations).
- The drift test parameterizes over every rendered file; mutating any
  committed render or template (without re-render) fails it.
- All plugin suites pass, including the pinned chunk-executor/intent-auditor
  invariants and `ve validate` backreference integrity.
