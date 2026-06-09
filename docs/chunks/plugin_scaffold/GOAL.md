---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- .claude-plugin/plugin.json
- .claude-plugin/marketplace.json
- commands/ve-status.md
- skills/.gitkeep
- agents/.gitkeep
- hooks/.gitkeep
- docs/trunk/DECISIONS.md
- README.md
- tests/test_plugin_manifest.py
code_references:
- ref: .claude-plugin/plugin.json
  implements: "Plugin manifest defining the vibe-engineer Claude Code plugin (name, version, description, author)"
- ref: .claude-plugin/marketplace.json
  implements: "Marketplace manifest making this repository installable via /plugin marketplace add + /plugin install"
- ref: commands/ve-status.md
  implements: "Read-only pilot command wrapping ve chunk list --current, proving the plugin install path end-to-end"
- ref: tests/test_plugin_manifest.py#TestPluginManifest
  implements: "Validates plugin.json carries the required Claude Code plugin schema fields"
- ref: tests/test_plugin_manifest.py#TestMarketplaceManifest
  implements: "Validates marketplace.json lists the plugin and its source resolves to the repo root"
- ref: tests/test_plugin_manifest.py#TestPilotCommand
  implements: "Validates the pilot command exists, is read-only, and wraps ve chunk list --current"
- ref: tests/test_plugin_manifest.py#TestPluginLayout
  implements: "Validates the canonical plugin content layout (commands/, skills/, agents/, hooks/) exists at the plugin root"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---
# Chunk Goal

## Minor Goal

The vibe-engineer repository hosts a Claude Code plugin as the native
distribution surface for the workflow. `.claude-plugin/plugin.json` defines the
plugin and `.claude-plugin/marketplace.json` makes the repository an
installable marketplace, so users adopt the workflow with
`/plugin marketplace add <owner>/vibe-engineer` followed by
`/plugin install vibe-engineer`. The plugin directory layout (`commands/`,
`skills/`, `agents/`, `hooks/`) is the canonical home for agent-facing
workflow content, and a single pilot command proves the install path
end-to-end. The distribution decision and its accepted trade-off are recorded
as an ADR in docs/trunk/DECISIONS.md.

## Context

- Narrative: docs/narratives/claude_plugin_port — this is the first of eight
  chunks; later chunks port the 36 commands, add hooks and subagents, slim
  `ve init`, and build the legacy migration.
- Today distribution is render-based: `ve init` (src/cli/init_cmd.py,
  `Project.init()` in src/project.py) renders 36 Jinja2 command skills from
  src/templates/commands/ into `.agents/skills/` plus `.claude/commands/`
  symlinks. The plugin replaces that channel entirely (the operator chose full
  replacement over dual-mode).
- The `ve` Python CLI remains separately installed (uv/pip) and remains the
  workflow engine; the plugin is the agent-facing layer that shells out to it.
- Keep the pilot small and read-only (e.g., a status command wrapping
  `ve chunk list --current`). The mass port of commands happens in
  plugin_core_commands and plugin_orch_commands — do not port them here.

## Success Criteria

- `.claude-plugin/plugin.json` is valid per Claude Code's plugin schema (name,
  version, description, author) and the plugin loads without errors.
- `.claude-plugin/marketplace.json` lists the plugin; adding this repo as a
  marketplace and installing the plugin succeeds against a local checkout.
- The pilot command runs from a plugin install inside a project that has had
  `ve init`.
- An ADR in docs/trunk/DECISIONS.md records: plugin-based distribution
  replaces render-based distribution; the trade-off of dropping the
  agent-agnostic `.agents/skills/` (agentskills.io) layout; and the choice to
  host the plugin in this repo rather than a separate repo.
- README documents the install path.

## Rejected Ideas

### Separate plugin repository

A dedicated vibe-engineer-plugin repo that this repo publishes into.

Rejected because: the operator chose to keep the plugin co-versioned with the
Python source in this repository; marketplace.json can point at this repo
directly, and a publish pipeline adds moving parts with no current benefit.

### MCP server exposing ve operations

Expose chunk list / board send / etc. as MCP tools instead of shelling out.

Rejected because: out of scope for this narrative. Commands shell out to the
`ve` CLI, which must be installed anyway; an MCP layer adds surface without
removing that dependency.
