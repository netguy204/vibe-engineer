---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- skills/chunk-plan/SKILL.md
- skills/chunk-implement/SKILL.md
- skills/chunk-complete/SKILL.md
- skills/chunk-execute/SKILL.md
- skills/chunk-review/SKILL.md
- skills/chunk-commit/SKILL.md
- skills/chunk-rebase/SKILL.md
- skills/chunk-demote/SKILL.md
- skills/chunk-update-references/SKILL.md
- skills/chunks-resolve-references/SKILL.md
- skills/cluster-rename/SKILL.md
- skills/narrative-create/SKILL.md
- skills/narrative-compact/SKILL.md
- skills/narrative-execute/SKILL.md
- skills/investigation-create/SKILL.md
- skills/subsystem-discover/SKILL.md
- skills/discover-subsystems/SKILL.md
- skills/decision-create/SKILL.md
- skills/friction-log/SKILL.md
- skills/validate-fix/SKILL.md
code_references:
- ref: skills/chunk-plan/SKILL.md
  implements: "Static plugin port of chunk-plan with runtime task-context guidance"
- ref: skills/chunk-implement/SKILL.md
  implements: "Static plugin port of chunk-implement with runtime task-context guidance"
- ref: skills/chunk-complete/SKILL.md
  implements: "Static plugin port of chunk-complete preserving both single-project and task-workspace reference formats"
- ref: skills/chunk-execute/SKILL.md
  implements: "Static plugin port of chunk-execute (plan/implement/review/complete loop)"
- ref: skills/chunk-review/SKILL.md
  implements: "Static plugin port of chunk-review (four-phase review workflow)"
- ref: skills/chunk-commit/SKILL.md
  implements: "Static plugin port of chunk-commit with canonical preamble added to its git context"
- ref: skills/chunk-rebase/SKILL.md
  implements: "Static plugin port of chunk-rebase (merge trunk before review)"
- ref: skills/chunk-demote/SKILL.md
  implements: "Static plugin port of chunk-demote"
- ref: skills/chunk-update-references/SKILL.md
  implements: "Static plugin port of chunk-update-references preserving both symbolic reference format variants"
- ref: skills/chunks-resolve-references/SKILL.md
  implements: "Static plugin port of chunks-resolve-references (parallel reference fan-out)"
- ref: skills/cluster-rename/SKILL.md
  implements: "Static plugin port of cluster-rename"
- ref: skills/narrative-create/SKILL.md
  implements: "Static plugin port of narrative-create"
- ref: skills/narrative-compact/SKILL.md
  implements: "Static plugin port of narrative-compact with runtime task-context guidance"
- ref: skills/narrative-execute/SKILL.md
  implements: "Static plugin port of narrative-execute (wave execution with inline chunk-executor agent prompt)"
- ref: skills/investigation-create/SKILL.md
  implements: "Static plugin port of investigation-create with runtime task-context guidance"
- ref: skills/subsystem-discover/SKILL.md
  implements: "Static plugin port of subsystem-discover with runtime task-context guidance"
- ref: skills/discover-subsystems/SKILL.md
  implements: "Static plugin port of discover-subsystems"
- ref: skills/decision-create/SKILL.md
  implements: "Static plugin port of decision-create"
- ref: skills/friction-log/SKILL.md
  implements: "Static plugin port of friction-log (raw block unwrapped)"
- ref: skills/validate-fix/SKILL.md
  implements: "Static plugin port of validate-fix (raw block unwrapped)"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_runtime_context
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---
# Chunk Goal

## Minor Goal

The core workflow commands ship as static plugin commands and skills:
chunk-create, chunk-plan, chunk-implement, chunk-complete, chunk-execute,
chunk-review, chunk-commit, chunk-rebase, chunk-demote,
chunk-update-references, chunks-resolve-references, cluster-rename,
narrative-create, narrative-compact, narrative-execute, investigation-create,
subsystem-discover, discover-subsystems, decision-create, friction-log, and
validate-fix. Each exists as a slash command and carries a skill description
that lets the model invoke it proactively; all follow the runtime
context-detection convention established by plugin_runtime_context.

## Context

- Sources: src/templates/commands/<name>.md.jinja2. Port content and strip all
  Jinja2 (auto-generated header partial, `{% if task_context %}` conditionals,
  `ve_config` interpolation) per the plugin_runtime_context convention and
  porting guide.
- chunk-create is already ported (the plugin_runtime_context pilot); this
  chunk covers the remaining 20 core commands.
- Skill descriptions should state trigger conditions so the model surfaces
  commands proactively (use the descriptions in this repo's rendered
  .claude/commands files as a starting point).
- Source templates remain in place during this chunk — deleting
  src/templates/commands/ belongs to plugin_init_slimdown.

## Success Criteria

- All 21 core commands exist in the plugin with no Jinja2 syntax remaining.
- Each command has a description suitable for proactive/skill invocation.
- Where a source template had `{% if task_context %}` blocks, the ported
  command preserves that guidance as runtime conditionals.
- Spot-check from a plugin install in a ve project: chunk-plan,
  narrative-create, and validate-fix run correctly.
