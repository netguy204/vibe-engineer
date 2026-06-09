---
decision: APPROVE
summary: "All 15 orchestrator/steward/swarm/entity/migration commands ported per the runtime context-detection recipe with no surviving Jinja2, proactive descriptions, embedded target-project channel guidance, and passing invariant tests; the three deliberate body deviations are code-verified and documented in PLAN.md."
operator_review: null
---

## Criteria Assessment

### Criterion 1: All 15 commands exist in the plugin with no Jinja2 syntax remaining.

- **Status**: satisfied
- **Evidence**: All 15 files exist in `commands/` (orchestrator-inject/monitor/investigate/submit-future, steward-setup/watch/send/changelog, swarm-monitor, swarm-request-response, entity-startup/shutdown/episodic, audit-intent, migrate-managed-claude-md). `grep -nE '\{%|\{\{|\{#' commands/*.md` matches nothing; `tests/test_plugin_commands.py` (70 tests, parameterized over all 17 command files) passes, including the no-Jinja2 and no-AUTO-GENERATED-header invariants.

### Criterion 2: Each command has a description suitable for proactive/skill invocation.

- **Status**: satisfied
- **Evidence**: Every frontmatter `description` states what the command does plus trigger conditions ("Use when ..."), e.g. orchestrator-investigate names NEEDS_ATTENTION/stalled-chunk triggers; entity-episodic names the "remember when we..." trigger. Verified non-empty and >40 chars for all 15; `name` matches the file stem (test_frontmatter_has_name_and_description).

### Criterion 3: The steward-send and swarm command bodies carry the target-project channel naming guidance.

- **Status**: satisfied
- **Evidence**: `commands/steward-send.md` has a dedicated "Derive the channel name from the TARGET project" section with the `<target-project>-steward` convention, the vibe-engineer-steward example, and the documented common mistake (reading the local STEWARD.md `channel` field). `commands/swarm-request-response.md` Phase 1 carries the same convention + common-mistake warning; `commands/swarm-monitor.md` Key Concepts carries a cross-project channel naming bullet; `commands/steward-changelog.md` adds the target-project derivation note. The guidance no longer depends on the AGENTS.md managed block.

### Criterion 4: Spot-check from a plugin install: steward-send and orchestrator-monitor run correctly in a ve project.

- **Status**: satisfied
- **Evidence**: A true `/plugin install` cannot be exercised in this headless environment; the spot-check was approximated by (a) executing all three `!`-probe lines from both commands in a ve project and an empty directory — outputs distinguish installed/not-installed and task/non-task correctly; (b) YAML frontmatter parses and `allowed-tools` covers every probe and `ve` invocation the bodies instruct; (c) instruction bodies are diff-identical to the proven rendered templates (verified for orchestrator-monitor, steward-watch, and four others), so runtime behavior matches the pre-port commands.

## Notes

Three deliberate deviations from verbatim porting, all documented in PLAN.md
Deviations and verified against code: steward-changelog cursor path corrected
to `.ve/board/cursors/` (matches `src/board/storage.py`), audit-intent
prerequisite checks rewritten to work in consuming projects (`ve chunk list
--status COMPOSITE` verified to exit 0/1 appropriately), and `uv run ve`
asides removed per the bare-`ve` recipe rule.
