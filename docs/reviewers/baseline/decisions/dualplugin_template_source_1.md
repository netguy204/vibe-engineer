---
decision: APPROVE
summary: "All four success criteria satisfied — the plugin template collection renders both pilots byte-identical modulo the documented marker line, the drift test fails on both stale-template and hand-edit modes, invariant suites pass unchanged, and TEMPLATING_GUIDE.md gives the migration chunk a mechanical recipe."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `src/templates/plugin/` exists with the idiom partials factored out; `uv run ve plugin render` regenerates the pilots byte-identical to the committed files (deliberate diffs documented in PLAN.md Deviations)

- **Status**: satisfied
- **Evidence**: src/templates/plugin/partials/claude/idioms.md.jinja2 defines
  the five idiom macros (frontmatter, generated_marker, probe,
  canonical_preamble, plugin_root); commands/ve-status.md.jinja2 and
  commands/chunk-create.md.jinja2 are the pilots. `uv run ve plugin render`
  produced exactly one added line per pilot (`git diff commands/` shows only
  the marker line) and re-running is idempotent
  (TestRenderCli::test_render_is_idempotent). The marker line is documented
  as the sole deliberate diff in PLAN.md Deviations. The renderer reuses
  template_system.render_template — no second renderer (template_system
  subsystem respected).

### Criterion 2: Rendered files carry the new generated-marker comment; the drift test fails on (a) template edited without re-render and (b) render hand-edited

- **Status**: satisfied
- **Evidence**: Both pilots carry `<!-- GENERATED from
  src/templates/plugin/commands/<name>.md.jinja2 ... -->` immediately after
  the frontmatter;
  tests/test_plugin_render.py::TestDrift::test_rendered_file_carries_generated_marker
  requires it per template. Both failure modes were exercised during
  implementation: appending a byte to commands/ve-status.md and appending a
  line to the template each made
  test_committed_render_matches_fresh_render fail, and restoring made it
  pass.

### Criterion 3: The invariant suites pass with the marker-test adjustment

- **Status**: satisfied
- **Evidence**: test_plugin_commands.py, test_plugin_agents.py,
  test_plugin_manifest.py, test_session_hook.py and the new
  test_plugin_render.py — 188 passed. The marker wording avoids the
  `AUTO-GENERATED` substring so `test_no_auto_generated_header` needed no
  semantic change (its docstring now documents the collision rule, and
  TestDrift::test_marker_does_not_collide_with_legacy_header guards it
  per rendered file). `src/project.py#_is_ve_generated_file` legacy cleanup
  cannot match the new marker.

### Criterion 4: Collection layout and partial vocabulary documented well enough for dualplugin_content_migration to migrate the remaining 36 commands mechanically

- **Status**: satisfied
- **Evidence**: docs/chunks/dualplugin_template_source/TEMPLATING_GUIDE.md
  documents the collection layout, the two-variable render contract
  (flavor, source_template), all five macro signatures with their Claude
  renderings, the marker collision rule, a per-command migration recipe
  (including the `{% raw %}` caveat for literal double braces), and the
  byte-stability/whitespace-control rules learned from the pilots. The
  drift test parametrizes over the collection so migrated files gain
  coverage without test edits.

## Scope check

Only the two pilots migrated; the other 36 commands, agents/, and
.cursor-plugin are untouched (later chunks own those). Full suite: 32
failures, identical to the inherited main baseline (subsystem-related files,
test_task_subsystem_discover, task CLI context, orchestrator daemon); 4036
pass (+16 new tests).
