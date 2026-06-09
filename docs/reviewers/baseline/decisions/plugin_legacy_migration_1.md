---
decision: APPROVE
summary: "All four success criteria satisfied — legacy-layout migration with safety rails and idempotency is implemented, fully tested end-to-end against fixtures, docs describe plugin-based distribution, and the orchestrator's phase-prompt coupling to .agents/skills is resolved via package data."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Running the slimmed `ve init` on a fixture repo with the legacy layout removes .agents/skills/ and ve-owned .claude/commands symlinks, preserves a planted user-authored command file, rewrites the managed block, and reports the actions taken

- **Status**: satisfied
- **Evidence**: `Project._migrate_legacy_layout()` (src/project.py) removes
  symlinks pointing into `.agents/skills/` (including broken ones), removes
  regular files / SKILL.md files carrying the AUTO-GENERATED header via the
  `_is_ve_generated_file()` safety rail, preserves user-authored files with
  warnings, and prunes emptied directories. The existing `_init_agents_md()`
  marker machinery rewrites the managed block to the slimmed template.
  Removals are reported via the new `InitResult.removed` channel; the CLI
  prints `Removed <path>` lines plus a plugin-install pointer
  (src/cli/init_cmd.py). Verified by
  tests/test_init.py::TestLegacyMigration (removal, reporting, pointer,
  managed-block rewrite, user-file preservation for commands, skills, and
  foreign symlinks) and TestLegacyMigrationProjectLevel.

### Criterion 2: A second run is a no-op

- **Status**: satisfied
- **Evidence**: `test_second_run_is_noop`,
  `test_init_result_removed_empty_on_second_run`, and
  `test_second_run_does_not_rewarn_about_preserved_files` — second run
  removes nothing, prints no pointer, emits no migration warnings, and
  reports skips through the existing channels. Preserve-warnings are gated
  on actual removals so already-migrated projects stay quiet.

### Criterion 3: README, SPEC.md, and ORCHESTRATOR.md describe plugin-based distribution and the plugin-update upgrade story

- **Status**: satisfied
- **Evidence**: README.md (slash-commands section now points at the plugin,
  new "Migrating from the legacy rendered layout" subsection, project
  structure updated); docs/trunk/SPEC.md (Workflow Contexts, project/task
  directory structures, `ve init` and `ve task init` postconditions/behavior
  including the documented migration semantics); docs/trunk/ORCHESTRATOR.md
  and src/templates/trunk/ORCHESTRATOR.md.jinja2 (new "Phase Prompts and
  Command Distribution" section: prompts ship with the ve package; upgrades
  via `/plugin update vibe-engineer` and `uv tool upgrade vibe-engineer`,
  never re-rendering).

### Criterion 4: An integration test exercises the legacy-fixture migration end-to-end

- **Status**: satisfied
- **Evidence**: tests/test_init.py::TestLegacyMigration drives the real
  `ve init` CLI (CliRunner) against a constructed legacy fixture
  (`make_legacy_layout`: AUTO-GENERATED skills, relative command symlinks,
  marker-managed AGENTS.md, CLAUDE.md symlink) and asserts filesystem state,
  output, warnings, and idempotency. No test touches this repository's own
  legacy layout.

### Additional: orchestrator phase-prompt coupling (narrative handoff)

- **Status**: satisfied
- **Evidence**: `AgentRunner.get_skill_path()` (src/orchestrator/agent.py)
  now resolves phase prompts from package data (`orchestrator/skills/`,
  hatch force-include of repo-root `commands/` in pyproject.toml; sdist
  includes `commands/**`) with a development-checkout fallback. Wheel build
  verified to contain orchestrator/skills/*.md. Tests assert resolution is
  independent of the project directory and that `commands/chunk-create.md`
  retains the `$ARGUMENTS` placeholder the GOAL phase depends on. Full
  suite: 32 failures, identical to the pre-existing baseline (subsystem
  test files + orchestrator daemon negative-pid); 4011 passed.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
