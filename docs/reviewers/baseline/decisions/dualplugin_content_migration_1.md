---
decision: APPROVE
summary: "All 36 remaining commands and both agents now render from src/templates/plugin/ with mechanically verified byte-stability (marker-only diffs), full-surface drift coverage with a 1:1 completeness test, and all plugin suites plus the inherited test/validate baselines intact"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: All 38 commands and 2 agents regenerate from `uv run ve plugin render` with zero diff against the committed tree (deliberate diffs documented in PLAN.md Deviations)

- **Status**: satisfied
- **Evidence**: `uv run ve plugin render` reports "40 file(s) rendered" and
  leaves `git status` clean (verified post-commit fd9cd55). Each of the 38
  newly migrated files changed by exactly one added line — the generated
  marker — per `git diff --numstat` (38 files, +1/-0 each); the two pilot
  renders were byte-identical. The migration script
  (docs/chunks/dualplugin_content_migration/migrate_templates.py) enforced
  this mechanically: it renders each written template and aborts on any
  diff beyond the inserted marker. The one deliberate non-marker deviation
  (agent templates carry literal frontmatter because the five-macro idiom
  interface has no `tools:`-key emitter) is documented in PLAN.md
  Deviations and affects template structure, not rendered bytes.

### Criterion 2: The drift test parameterizes over every rendered file; mutating any committed render or template (without re-render) fails it

- **Status**: satisfied
- **Evidence**: `TestDrift` parametrizes over `list_plugin_templates()`,
  now 40 entries. Behaviorally verified both directions: appending a line
  to commands/steward-send.md failed
  `test_committed_render_matches_fresh_render[commands/steward-send.md.jinja2]`,
  and appending to src/templates/plugin/commands/decision-create.md.jinja2
  without re-rendering failed its drift test (both mutations reverted).
  The new `TestCollectionLayout::test_collection_covers_every_committed_render`
  (tests/test_plugin_render.py) closes the remaining hole: a hand-added
  commands/*.md or agents/*.md with no template now fails the suite, and
  `test_collection_spans_full_plugin_surface` pins 38 commands + 2 agents.

### Criterion 3: All plugin suites pass, including the pinned chunk-executor/intent-auditor invariants and `ve validate` backreference integrity

- **Status**: satisfied
- **Evidence**: tests/test_plugin_render.py + test_plugin_commands.py +
  test_plugin_agents.py + test_plugin_manifest.py: 323 passed, including
  the pinned chunk-executor lifecycle text ("/chunk-plan" … "3 times
  maximum", SUCCESS/FAILURE) and intent-auditor rules (Veto rule,
  Symmetric verification, action_taken, "Do NOT commit"). Backreference
  HTML comment counts in all 40 rendered files are identical to the
  pre-migration tree (verified against HEAD~1). `uv run ve validate`
  reports the same 50 inherited errors as unmodified main, none touching
  files in this chunk's scope. Full suite: 32 failed / 4190 passed — the
  failures are exactly the inherited baseline set (subsystem files,
  test_task_subsystem_discover, task CLI context, orchestrator daemon);
  passes grew only by the new parametrized drift/layout tests.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
