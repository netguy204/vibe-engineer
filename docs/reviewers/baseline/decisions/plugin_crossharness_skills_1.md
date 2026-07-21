---
decision: APPROVE
summary: "All 38 workflow docs ship as self-contained skills/<name>/SKILL.md, commands/ is empty, consumers (orchestrator loader, packaging, tests, refs, DEC-010) follow the move, and the full suite shows only the 31 pre-existing baseline failures."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Every workflow doc previously at `commands/<name>.md` ships at `skills/<name>/SKILL.md`; `commands/` contains no workflow content

- **Status**: satisfied
- **Evidence**: 38 `skills/*/SKILL.md` files (git-tracked renames from `commands/*.md`); `commands/` contains only `.gitkeep`. Enforced by `tests/test_plugin_skills.py::test_commands_ships_no_workflow_content` and `test_skills_directory_has_content`.

### Criterion 2: Each SKILL.md has valid `name` + `description` frontmatter and is self-contained (no `` !`...` `` preprocessing; context detection as explicit run-commands instructions)

- **Status**: satisfied
- **Evidence**: All 38 files audited; the 3-line (and extended, e.g. chunk-commit's 8-line, ve-status's and chunk-execute-all's variants) `## Context` blocks now open with "Gather this context before following the instructions: run each of the commands below (with the Bash tool)..." and carry the same shell commands as plain inline code. `grep -rn '!\`' skills/` returns nothing. Enforced per-file by `TestSkillInvariants::test_self_contained_no_dynamic_preprocessing` and `test_frontmatter_name_matches_directory` (name must equal the skill directory; description non-empty; YAML parsed). `allowed-tools` retained in all 38.

### Criterion 3: In a fresh Claude Code session with the plugin installed, `Skill(vibe-engineer:chunk-create)` resolves and skills are invocable as slash invocations

- **Status**: satisfied (layout-level; runtime resolution not verifiable in-repo)
- **Evidence**: `skills/chunk-create/SKILL.md` exists in the canonical `skills/<name>/SKILL.md` layout Claude Code's skill loader discovers at the plugin root; frontmatter carries `name`/`description`. The runtime `Skill(...)` resolution itself is a property of a live Claude Code session and cannot be asserted by this repo's tests; the motivating failure (empty `skills/` with only `.gitkeep`) is structurally eliminated.

### Criterion 4: DEC-010's consequence is amended documenting the cross-harness-skills distribution and the commands-reserved boundary

- **Status**: satisfied
- **Evidence**: docs/trunk/DECISIONS.md DEC-010 Consequences: first bullet struck through with a dated **Amended 2026-07-21** note referencing docs/chunks/plugin_crossharness_skills, recording the native cross-harness format (not a render channel), the self-containment constraint, and the "commands/ reserved for genuinely command-shaped future UX" boundary.

### Criterion 5: `code_references` in the affected `plugin_*` chunks that point at `commands/*.md` are updated to the new `skills/` paths

- **Status**: satisfied
- **Evidence**: 126 `ref: commands/<name>.md` references across 71 chunk GOAL.md files (including plugin_core_commands, plugin_orch_commands, plugin_scaffold, plugin_runtime_context, plugin_subagents, plugin_legacy_migration) repointed to `ref: skills/<name>/SKILL.md`, each verified to exist. plugin_runtime_context's test-module refs follow the `tests/test_plugin_skills.py` rename. `grep -rn 'ref: commands/' docs/chunks/*/GOAL.md` returns nothing.

### Criterion 6: Existing tests pass (`uv run pytest tests/`), including the plugin/CLI co-versioning check; any test referencing `commands/` paths is updated

- **Status**: satisfied
- **Evidence**: Full suite: 4167 passed, 31 failed — the identical 31 failures (test_subsystem_list/status/subsystems/task_cli_context/task_subsystem_discover) reproduce on the unmodified pre-chunk tree (verified via stash), so they are the inherited baseline, not regressions. tests/test_session_hook.py (co-versioning) passes. Updated: test_plugin_commands.py -> test_plugin_skills.py, test_plugin_manifest.py (pilot skill), test_plugin_agents.py, test_orchestrator_agent_skills.py, test_orchestrator_feedback_injection.py. Wheel build verified: 38 `orchestrator/skills/<name>/SKILL.md` files force-included.
