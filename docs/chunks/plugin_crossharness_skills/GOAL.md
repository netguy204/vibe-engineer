---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- skills/
- commands/
- src/orchestrator/agent.py
- pyproject.toml
- agents/chunk-executor.md
- tests/test_plugin_skills.py
- tests/test_plugin_manifest.py
- tests/test_plugin_agents.py
- tests/test_orchestrator_agent_skills.py
- docs/trunk/DECISIONS.md
- docs/trunk/ORCHESTRATOR.md
- README.md
code_references:
- ref: skills/chunk-create/SKILL.md
  implements: 'Representative cross-harness skill: agentskills.io skills/<name>/SKILL.md
    layout with self-contained gather-context instructions replacing !`...` preprocessing
    (pattern applied to all 38 workflow skills)'
- ref: skills/ve-status/SKILL.md
  implements: Pilot skill relocated from commands/ve-status.md; read-only allowed-tools
    frontmatter retained
- ref: src/orchestrator/agent.py#AgentRunner::get_skill_path
  implements: Phase prompts resolve the skills/<name>/SKILL.md sources (wheel force-include
    and dev-checkout fallback)
- ref: pyproject.toml
  implements: Hatch wheel force-include and sdist include ship skills/ instead of
    commands/
- ref: agents/chunk-executor.md
  implements: Slash-command fallback instructions point at the skills/<name>/SKILL.md
    paths
- ref: tests/test_plugin_skills.py#TestSkillInvariants
  implements: 'Per-skill invariants: frontmatter name matches skill directory, no
    Jinja2, no AUTO-GENERATED header, no !`...` dynamic preprocessing'
- ref: tests/test_plugin_skills.py#test_commands_ships_no_workflow_content
  implements: 'Boundary invariant: commands/ is reserved and ships no workflow content'
- ref: tests/test_plugin_skills.py#TestRuntimeDetection
  implements: Behavioral check that the instructed context-gathering shell lines distinguish
    plain project, configured project, and task workspace
- ref: tests/test_plugin_manifest.py#TestPilotSkill
  implements: Install-contract pilot assertions retargeted to skills/ve-status/SKILL.md
- ref: tests/test_orchestrator_agent_skills.py#TestAgentRunner::test_get_skill_path_resolves_packaged_skill_source
  implements: Every orchestrator phase resolves an existing skills/<name>/SKILL.md
    source
- ref: docs/trunk/DECISIONS.md
  implements: 'DEC-010 consequence amended: cross-harness skills are the plugin''s
    native format; commands/ reserved for command-shaped future UX'
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- watch_handshake_5xx_retry
---

# Chunk Goal

## Minor Goal

The vibe-engineer plugin distributes the entire agent-facing workflow as
**cross-harness skills** — `skills/<name>/SKILL.md` (agentskills.io directory
layout) — rather than Claude Code commands (`commands/*.md`). The plugin's
`commands/` directory ships no workflow content; it is reserved for a future
in which some interaction is genuinely command-shaped (Claude-Code-specific
UX), but today the workflow is fully representable as skills.

**The guarded intent:** the vibe-engineer workflow is plausibly cross-harness.
Claude Code is the primary supported target, but the skill representation must
not *depend* on Claude-Code-only machinery. Concretely, each SKILL.md is
self-contained: context the agent needs (ve CLI availability, `.ve-task.yaml`
task-workspace detection, `.ve-config.yaml` project config) is gathered by
**instructing the agent to run commands**, not by Claude Code's `` !`...` ``
slash-command preprocessing, which other harnesses (and Claude Code's own
Skill-tool invocation path) do not execute.

This amends a DEC-010 consequence. DEC-010 (plugin-based distribution) stated:
"The agent-agnostic `.agents/skills/` (agentskills.io) layout is dropped;
non-Claude-Code agent support narrows to the AGENTS.md pointer file… if
multi-agent support becomes a requirement later, a render channel can be
reintroduced from the plugin sources." This chunk reintroduces the
cross-harness layout *as the plugin's native format* rather than as a render
channel — one source of truth, no drift.

## Context

- **Motivating failure (2026-07-21):** a Claude Code session invoked
  `Skill(vibe-engineer:chunk-create)` and got `Unknown skill` — at the time,
  the plugin's `skills/` directory contained only `.gitkeep` while all 38
  workflow docs lived in `commands/`. Plugin commands surfaced as slash
  commands but not as Skill-tool-invocable skills. The agent fell back to
  reading `commands/chunk-create.md` off disk, which silently skipped the
  `` !`...` `` dynamic context block (ve CLI check, task-workspace
  detection) — exactly the failure mode the self-containment constraint
  above prevents.
- **Layout:** the 38 workflow docs (chunk-*, narrative-*, orchestrator-*,
  steward-*, swarm-*, entity-*, plus audit-intent, cluster-rename,
  decision-create, discover-subsystems, friction-log, investigation-create,
  migrate-managed-claude-md, subsystem-discover, validate-fix, ve-status)
  live at `skills/<name>/SKILL.md`; `commands/` carries only a `.gitkeep`.
  `agents/` (subagents) and `hooks/` (session_start) are **out of scope** —
  unchanged (except that `agents/chunk-executor.md`'s fallback paths follow
  the moved files).
- **Frontmatter:** skills keep `name` + `description` (required by both
  Claude Code and agentskills.io); `allowed-tools` is retained where present
  (e.g. `skills/chunk-create/SKILL.md`) — harnesses that don't understand it
  ignore extra frontmatter keys.
- **Dynamic context blocks:** `plugin_runtime_context` introduced `## Context`
  sections using `` !`ve --help …` ``-style substitution. These are
  converted to explicit "gather context first" instructions: each `## Context`
  block opens by instructing the agent to run the listed shell commands and
  note their outputs (the pre-plugin `.agents/skills/` renders showed this
  instruction-driven style). No SKILL.md contains `` !` `` preprocessing —
  enforced by `tests/test_plugin_skills.py`.
- **Naming:** skill directory names mirror the former command basenames
  (`commands/chunk-create.md` → `skills/chunk-create/SKILL.md`), matching the
  naming the legacy `.agents/skills/` structure used.
- **Related chunks:** `plugin_scaffold` (plugin/marketplace layout),
  `plugin_core_commands` / `plugin_orch_commands` (the static ports that
  moved — their `code_references` point at the `skills/` paths),
  `plugin_runtime_context` (the context-detection pattern preserved in
  instruction form), `agentskills_migration` (the original cross-harness
  layout this restores at the plugin level).
- **Decision record:** DEC-010's first consequence in
  `docs/trunk/DECISIONS.md` carries a dated amendment recording that the
  plugin ships cross-harness skills as its native format and that
  `commands/` is reserved for genuinely command-shaped future UX.

## Success Criteria

- Every workflow doc previously at `commands/<name>.md` ships at
  `skills/<name>/SKILL.md`; `commands/` contains no workflow content.
- Each SKILL.md has valid `name` + `description` frontmatter and is
  self-contained: no `` !`...` `` preprocessing or other Claude-Code-only
  machinery required for correct execution; runtime context detection is
  expressed as explicit instructions to run commands.
- In a fresh Claude Code session with the plugin installed,
  `Skill(vibe-engineer:chunk-create)` resolves (the motivating bug is fixed),
  and skills are invocable as `/chunk-create`-style slash invocations.
- DEC-010's consequence is amended (or a new decision added) documenting the
  cross-harness-skills distribution and the "commands reserved for genuinely
  command-shaped future UX" boundary.
- `code_references` in the affected `plugin_*` chunks that point at
  `commands/*.md` are updated to the new `skills/` paths.
- Existing tests pass (`uv run pytest tests/`), including the
  plugin/CLI co-versioning check in `tests/test_session_hook.py`; any test
  referencing `commands/` paths is updated.

## Rejected Ideas

### Ship both commands/ and skills/ (dual surface)

Keep `commands/*.md` and add `skills/` mirroring them, so slash commands and
Skill-tool invocation both work from their "native" directories.

Rejected because: two copies of every workflow doc is exactly the
two-sources-of-truth drift DEC-010 rejected when it killed the render
channel. Skills already surface as slash invocations; the dual layout buys
nothing.

### Keep commands/ as the format and register them as skills some other way

Rejected because: the operator's intent is that the workflow is
**cross-harness** — the agentskills.io `skills/<name>/SKILL.md` layout is the
portable representation. `commands/` remains available for a future in which
something is genuinely Claude-Code-command-shaped, but nothing today is.