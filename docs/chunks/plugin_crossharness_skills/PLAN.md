

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Mechanical relocation plus a targeted content transformation, with the test
suite moved in lockstep:

1. **Relocation**: every `commands/<name>.md` (38 files) moves to
   `skills/<name>/SKILL.md` via `git mv` (history-preserving). `commands/`
   keeps only a `.gitkeep` so the directory survives as the reserved slot for
   genuinely command-shaped future UX; `skills/.gitkeep` is removed.
2. **Self-containment transformation**: every SKILL.md's `## Context` block
   loses its Claude-Code-only `` !`...` `` preprocessing. The same shell
   commands are kept verbatim but demoted to plain inline code with an
   explicit instruction to run them (Bash) and note the outputs before
   following the instructions. The follow-on `## Runtime context` section's
   lead-in is reworded from "the context above" to "the context you
   gathered". All other content (frontmatter `name`/`description`/
   `allowed-tools`, `$ARGUMENTS`, backreference comments, bodies) is
   unchanged. The transformation is scripted (one-shot Python in the chunk
   directory is unnecessary — it is a sed-class rewrite done inline) and
   verified by tests.
3. **Consumers follow the move**:
   - `src/orchestrator/agent.py#AgentRunner::get_skill_path` — both branches:
     packaged path becomes `orchestrator/skills/<name>/SKILL.md`, dev
     fallback becomes `<repo>/skills/<name>/SKILL.md`.
   - `pyproject.toml` — hatch wheel force-include maps `skills` →
     `orchestrator/skills`; sdist includes `skills/**` instead of
     `commands/**`.
   - `agents/chunk-executor.md` — the slash-command fallback paragraph points
     at the new `skills/<name>/SKILL.md` paths (agents/ itself is otherwise
     untouched, per the GOAL's scope).
4. **Tests move in lockstep** (see docs/trunk/TESTING_PHILOSOPHY.md — tests
   assert the install contract, not implementation details):
   - `tests/test_plugin_commands.py` retargets from `commands/*.md` to
     `skills/*/SKILL.md` (name matches the skill directory, not the file
     stem). New invariants: no `` !` `` preprocessing anywhere in a SKILL.md
     (the cross-harness guarantee), and `commands/` ships no workflow
     content (no `*.md`). The `TestRuntimeDetection` behavioral tests keep
     running the same three-scenario matrix by extracting the instructed
     shell lines from the `## Context` section instead of the `` !` ``
     markers.
   - `tests/test_plugin_manifest.py` pilot assertions retarget to
     `skills/ve-status/SKILL.md`; the layout test keeps asserting all four
     plugin content directories exist.
   - `tests/test_plugin_agents.py` retargets `narrative-execute` /
     `audit-intent` lookups to their skills/ locations.
   - `tests/test_orchestrator_agent_skills.py` phase-prompt assertions accept
     the `skills/<name>/SKILL.md` shape (file named SKILL.md, parent named
     after the phase skill).
5. **Documentation**: DEC-010's first consequence bullet in
   `docs/trunk/DECISIONS.md` gains an explicit amendment (dated, referencing
   this chunk) recording that the plugin ships the workflow as cross-harness
   `skills/<name>/SKILL.md` content and that `commands/` is reserved for
   genuinely command-shaped future UX. README.md's repo-layout tree and
   ORCHESTRATOR.md's phase-prompt paragraph are updated to name `skills/`.
6. **Reference integrity**: every chunk GOAL.md carrying a live
   `ref: commands/<name>.md` code reference (72 files — a previous mass
   resolution pointed them all at the plugin command sources) is updated
   mechanically to `ref: skills/<name>/SKILL.md`. Historical `code_paths`
   lists are left as-is (they are planning-time records; precedent: the
   pre-plugin chunks kept `src/templates/...` code_paths when their refs
   were re-pointed at commands/).

This work amends DEC-010 (docs/trunk/DECISIONS.md) rather than adding a new
decision — the distribution mechanism is unchanged; only the shipped format
inside the plugin changes.

## Sequence

### Step 1: Move the 38 workflow docs to skills/

`git mv commands/<name>.md skills/<name>/SKILL.md` for all 38 files; remove
`skills/.gitkeep`; add `commands/.gitkeep`.

### Step 2: Strip `` !` `` preprocessing from every SKILL.md

Scripted rewrite of each `## Context` block: insert the "gather this context
by running these commands" instruction line, drop the `!` prefix from each
`` !`...` `` span (keeping the shell command verbatim), and reword the
`## Runtime context` lead-in. Audit afterwards: `grep -rn '!\`' skills/`
must return nothing.

### Step 3: Retarget the orchestrator phase-prompt loader

Update `AgentRunner.get_skill_path` (both packaged and dev-checkout
branches) and its docstring; update the `pyproject.toml` force-include and
sdist include. Verify `uv run python -c` resolution for every phase.

### Step 4: Update agents/chunk-executor.md fallback paths

The "if slash commands are unavailable" paragraph names
`skills/chunk-plan/SKILL.md` etc.

### Step 5: Update the test suite

Retarget `test_plugin_commands.py`, `test_plugin_manifest.py`,
`test_plugin_agents.py`, `test_orchestrator_agent_skills.py` as described in
the Approach; add the two new invariants (no `` !` `` in skills/, no
workflow content in commands/).

### Step 6: Amend DEC-010 and update prose docs

DECISIONS.md consequence amendment; README.md layout tree; ORCHESTRATOR.md
phase-prompt paragraph.

### Step 7: Mass-update chunk code_references

`ref: commands/<name>.md` → `ref: skills/<name>/SKILL.md` across
docs/chunks/*/GOAL.md.

### Step 8: Full test run and validation

`uv run pytest tests/` green; `uv run ve chunk validate
plugin_crossharness_skills` at completion.

## Dependencies

None beyond the already-merged plugin chunks (plugin_scaffold,
plugin_core_commands, plugin_orch_commands, plugin_runtime_context,
plugin_subagents, plugin_legacy_migration).

## Risks and Open Questions

- **Claude Code slash invocation of skills**: the GOAL asserts skills are
  invocable as `/chunk-create`-style slash invocations. This cannot be
  verified from tests in this repo; it is a property of Claude Code's skill
  loader. The in-repo criteria (layout, self-containment, frontmatter) are
  fully testable.
- **Wheel packaging**: the hatch force-include change is exercised only at
  build time; `test_get_skill_path_resolves_packaged_command_source` covers
  the dev fallback. A local `uv build` sanity check confirms the wheel
  carries `orchestrator/skills/<name>/SKILL.md`.
- **allowed-tools in skills**: Claude Code accepts extra frontmatter keys on
  skills; other harnesses ignore them. Retained as the GOAL directs.

## Deviations

- Step 7 widened beyond the GOAL's "plugin_* chunks" wording: a previous
  mass reference-resolution had pointed 72 chunks' `code_references` at
  `commands/<name>.md`, so all of them (not just plugin_*) are re-pointed at
  `skills/<name>/SKILL.md` to keep every live reference resolvable. Purely
  mechanical; historical `code_paths` untouched.
- Step 4 extended to `agents/intent-auditor.md`? No — only chunk-executor.md
  references command paths; intent-auditor does not. (Verified by grep.)
