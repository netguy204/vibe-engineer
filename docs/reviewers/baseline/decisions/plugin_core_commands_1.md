---
decision: APPROVE
summary: "All 21 core commands exist as static plugin commands with the canonical runtime-context preamble, proactive trigger-stating descriptions, preserved task-context guidance (both variants of dual blocks), verbatim instruction bodies, and the parameterized command invariants pass."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: All 21 core commands exist in the plugin with no Jinja2 syntax remaining.

- **Status**: satisfied
- **Evidence**: All 21 files present in commands/ (chunk-create from the pilot
  plus the 20 ported here). `grep -nE '\{%|\{\{|\{#' commands/*.md` matches
  nothing; no AUTO-GENERATED header in any file;
  tests/test_plugin_commands.py (85 tests, parameterized over every
  commands/*.md) passes.

### Criterion 2: Each command has a description suitable for proactive/skill invocation.

- **Status**: satisfied
- **Evidence**: Every frontmatter description states what the command does
  plus "Use when ..." trigger conditions (32–47 words each), e.g.
  commands/chunk-plan.md ("Use when the operator asks to plan the current
  chunk ... or as the PLAN phase of the chunk lifecycle") and
  commands/validate-fix.md ("Use when validation errors appear, after
  refactors that may have broken artifact links ...").

### Criterion 3: Where a source template had `{% if task_context %}` blocks, the ported command preserves that guidance as runtime conditionals.

- **Status**: satisfied
- **Evidence**: All 8 templates with task blocks (chunk-plan,
  chunk-implement, chunk-execute, chunk-complete, chunk-update-references,
  narrative-compact, investigation-create, subsystem-discover) carry the
  guidance as "If this is a task workspace (.ve-task.yaml present)" prose in
  the Runtime context section. Dual-variant if/else blocks keep BOTH
  variants: chunk-complete step 2 and chunk-update-references' Symbolic
  Reference Format show project-qualified and single-project formats side by
  side; chunk-complete's task-only step 15 became an explicit "task
  workspaces only / skip in a single project" step.

### Criterion 4: Spot-check from a plugin install in a ve project: chunk-plan, narrative-create, and validate-fix run correctly.

- **Status**: satisfied
- **Evidence**: Static review of the three commands: canonical preamble
  probes match the pilot exactly (and TestRuntimeDetection verifies the
  probe behavior across plain/config/task directories); allowed-tools cover
  every `ve` invocation each body instructs (chunk-plan: chunk list,
  suggest-prefix, cluster-list; narrative-create: narrative create;
  validate-fix: validate); instruction bodies diff clean against their
  source templates apart from trailing-newline normalization. A live
  plugin-install smoke test remains an operator-environment activity, but
  nothing in the files blocks it.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
