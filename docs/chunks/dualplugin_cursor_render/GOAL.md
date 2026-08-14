---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/plugin_render.py
- src/templates/plugin/partials/claude/idioms.md.jinja2
- src/templates/plugin/partials/cursor/idioms.md.jinja2
- src/templates/plugin/agents/chunk-executor.md.jinja2
- src/templates/plugin/agents/intent-auditor.md.jinja2
- src/templates/plugin/skills/
- .cursor-plugin/skills/
- .cursor-plugin/agents/
- tests/test_plugin_render.py
- tests/test_cursor_manifest.py
code_references:
- ref: src/plugin_render.py#FLAVOR_TEMPLATE_SUBSETS
  implements: Pilot boundary deleted — empty by default, so templates_for_flavor
    returns the full collection for every flavor
- ref: src/templates/plugin/partials/claude/idioms.md.jinja2
  implements: 'Claude halves of the new idiom macros: agent_frontmatter (name/
    description/tools), arguments_ref (`$ARGUMENTS`), arguments_token ($ARGUMENTS)'
- ref: src/templates/plugin/partials/cursor/idioms.md.jinja2
  implements: 'Cursor halves: agent_frontmatter drops tools per the Cursor agents
    spec, arguments_ref names the operator''s request, arguments_token emits the
    caller''s placeholder'
- ref: src/templates/plugin/agents/chunk-executor.md.jinja2
  implements: Agent frontmatter routed through idioms.agent_frontmatter
- ref: src/templates/plugin/agents/intent-auditor.md.jinja2
  implements: Agent frontmatter routed through idioms.agent_frontmatter
- ref: tests/test_plugin_render.py#TestCursorScope
  implements: Cursor drift coverage widened to the full collection; scope test
    asserts cursor renders everything
- ref: tests/test_cursor_manifest.py#TestCursorSkillRenders
  implements: Skill invariants parameterized over all 39 Cursor skills (widened
    automatically when the subset died)
- ref: tests/test_cursor_manifest.py#TestCursorAgentRenders
  implements: 'Cursor agent invariants: declared path, name+description-only
    frontmatter, no Claude idioms, generated marker, no Jinja residue'
- ref: tests/test_cursor_manifest.py#TestDiscoveryCollision::test_declared_agents_dir_holds_only_rendered_agents
  implements: Successor to the empty-agents-dir guard — the declared dir holds
    exactly the rendered agents
narrative: cursor_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- dualplugin_content_migration
- dualplugin_cursor_scaffold
created_after:
- plugin_hook_cli_bootstrap
---

# Chunk Goal

## Minor Goal

The full plugin surface renders for Cursor: every command/skill and both
agents (as Cursor subagents) are emitted from `src/templates/plugin/` into
the Cursor layout established by dualplugin_cursor_scaffold. The invariant
and drift tests parameterize over both flavors — Claude renders keep their
existing invariants; Cursor renders are checked for no Jinja2 residue, no
Claude-only idioms, and spec-valid frontmatter — and a representative sample
of commands has an operator verification script
(`docs/chunks/dualplugin_cursor_render/CURSOR_VERIFICATION.md`) for
confirmation in a live Cursor session.

## Context

- Prerequisites: all content lives in templates
  (dualplugin_content_migration) and the Cursor target + idiom partials
  exist (dualplugin_cursor_scaffold). This chunk is the mechanical
  cross-product plus test coverage.
- Agents map to Cursor subagents. Cursor's agent frontmatter is `name` +
  `description` only (reference docs, fetched 2026-08-14), so the Claude
  `tools:` list is dropped by the `agent_frontmatter` idiom macro — the same
  treatment `allowed-tools` gets in skills. The chunk-executor's
  worktree-mode protocol and the intent-auditor's audit protocol are
  editor-agnostic (git + ve CLI) and ship verbatim.
- Sample for live verification (operator-driven, same checkpoint pattern as
  the scaffold chunk): chunk-create (runtime context detection),
  chunk-plan, steward-send (channel-naming guidance), and
  chunk-execute-all (sub-agent orchestration — verify Cursor's agent can
  follow the wave protocol or document divergence).
- Content that references Claude Code by name renders per editor: the
  billing rationale and worktree-isolation phrasing in chunk-execute-all,
  chunk-commit's commit trailer, and the background-task timeout notes in
  steward-watch and swarm-request-response carry flavor branches. Slash
  references like `/chunk-create` ship verbatim: Cursor invokes skills
  manually as `/skill-name` in chat, so they are valid Cursor mechanics.
  Harness tool names with no verified Cursor equivalent (`TaskStop`,
  `run_in_background`, `/loop`, `CronDelete`, "the Agent tool" in
  narrative-execute and audit-intent) ship verbatim — a documented handoff,
  not an oversight (see PLAN.md and CURSOR_VERIFICATION.md §6).

## Success Criteria

- `uv run ve plugin render` regenerates both complete flavors; drift test
  covers every file in both trees.
- Invariant tests parameterize over the Cursor render with
  ecosystem-appropriate assertions; full plugin suites pass.
- The four-command sample is confirmed in a live Cursor session by the
  operator (or review ESCALATEs pending confirmation).
- No rendered Cursor file instructs Claude-Code-specific mechanics where a
  Cursor equivalent was available.
