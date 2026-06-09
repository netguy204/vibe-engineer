---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/project.py
- src/cli/init_cmd.py
- src/orchestrator/agent.py
- pyproject.toml
- commands/chunk-create.md
- tests/test_init.py
- tests/test_orchestrator_agent_skills.py
- README.md
- docs/trunk/SPEC.md
- docs/trunk/ORCHESTRATOR.md
- src/templates/trunk/ORCHESTRATOR.md.jinja2
code_references:
- ref: src/project.py#Project::_migrate_legacy_layout
  implements: "Legacy-layout detection and removal: ve-generated .agents/skills content, .claude/commands symlinks, user-file preservation with warnings, directory pruning"
- ref: src/project.py#InitResult
  implements: "removed channel reporting paths deleted by the migration"
- ref: src/project.py#Project::init
  implements: "Migration wired as the first init phase; aggregates the removed channel"
- ref: src/cli/init_cmd.py#init
  implements: "CLI reporting of removed paths and the plugin-install pointer after migration"
- ref: src/orchestrator/agent.py#AgentRunner::get_skill_path
  implements: "Phase prompts resolve from package data (orchestrator/skills/) with a dev-checkout fallback, decoupling the orchestrator from the legacy project layout"
- ref: pyproject.toml
  implements: "Wheel force-include of commands/ as orchestrator/skills package data; sdist includes commands/**"
- ref: tests/test_init.py#TestLegacyMigration
  implements: "End-to-end CLI integration tests of the legacy-fixture migration, preservation warnings, and idempotency"
- ref: tests/test_init.py#TestLegacyMigrationProjectLevel
  implements: "Project.init() level assertions for the removed/warnings channels"
- ref: tests/test_orchestrator_agent_skills.py#TestAgentRunner
  implements: "Phase-prompt resolution tests: package-shipped sources, project independence, $ARGUMENTS invariant"
- ref: README.md
  implements: "Plugin-distribution command docs and the legacy-layout migration story"
- ref: docs/trunk/SPEC.md
  implements: "Plugin-based command distribution in contexts, directory structures, and ve init / ve task init behavior including migration semantics"
- ref: docs/trunk/ORCHESTRATOR.md
  implements: "Phase Prompts and Command Distribution section: package-shipped prompts and the plugin-update upgrade story"
- ref: src/templates/trunk/ORCHESTRATOR.md.jinja2
  implements: "Template counterpart of the command-distribution section rendered into new projects"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_init_slimdown
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---

# Chunk Goal

## Minor Goal

Existing projects on the legacy rendered layout migrate by re-running
`ve init`: it detects and removes ve-generated `.agents/skills/` content and
`.claude/commands/` symlinks while leaving user-authored files untouched,
rewrites the AGENTS.md managed block to the slimmed form, and prints a pointer
to the plugin install. README and trunk docs (SPEC.md, and ORCHESTRATOR.md
where it describes command distribution) describe plugin-based distribution,
and the documented upgrade story for commands is "update the plugin," not
"re-run ve init."

The orchestrator is independent of the removed layout: phase prompts are the
plugin command sources (commands/*.md), shipped with the vibe-engineer
package as orchestrator package data (hatch force-include in pyproject.toml)
and resolved by `AgentRunner.get_skill_path()` with a development-checkout
fallback — never read from the target project.

## Context

- Safety rail: `_is_ve_generated_file()` (src/project.py) checks for the
  "AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY" header. Only ve-generated files
  and symlinks into .agents/skills/ may be removed; user-authored
  .claude/commands files without the header are preserved with a warning.
- The AGENTS.md rewrite reuses the existing magic-marker replacement machinery
  (parse_markers in src/project.py); slimmed managed content comes from
  plugin_init_slimdown.
- Migration is idempotent: re-running on an already-migrated project is a
  no-op — nothing in the InitResult `removed` channel, no pointer, and no
  warnings. Preserve-warnings accompany only runs that actually removed
  something, so user files in `.claude/commands/` produce no recurring noise.
- This is the final chunk of docs/narratives/claude_plugin_port — completing
  it sets the narrative's status to COMPLETED.

## Success Criteria

- Running the slimmed `ve init` on a fixture repo with the legacy layout
  removes .agents/skills/ and ve-owned .claude/commands symlinks, preserves a
  planted user-authored command file, rewrites the managed block, and reports
  the actions taken.
- A second run is a no-op.
- README, SPEC.md, and ORCHESTRATOR.md describe plugin-based distribution and
  the plugin-update upgrade story.
- An integration test exercises the legacy-fixture migration end-to-end.
