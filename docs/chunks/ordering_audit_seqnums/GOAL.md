---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-complete.md.jinja2
  - src/templates/commands/chunk-update-references.md.jinja2
  - src/templates/commands/subsystem-discover.md.jinja2
  - CLAUDE.md
code_references:
  - ref: src/templates/commands/chunk-complete.md.jinja2
    implements: "Updated step 3 to use short name directly instead of extracting sequential ID"
  - ref: src/templates/commands/chunk-update-references.md.jinja2
    implements: "Updated backreference format example to use short name pattern"
  - ref: src/templates/commands/subsystem-discover.md.jinja2
    implements: "Updated pattern matching and example paths to use short name format"
  - ref: CLAUDE.md
    implements: "Updated examples to use short name format (e.g., docs/chunks/feature_name/, docs/chunks/symbolic_code_refs)"
narrative: null
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: uses
created_after: ["artifact_promote", "task_qualified_refs", "task_init_scaffolding", "task_status_command", "task_config_local_paths"]
---

# Chunk Goal

## Minor Goal

Audit all slash commands in `.claude/commands/` and remove references to the deprecated sequential numbering scheme (e.g., `NNNN-`, "prefix number", "sequential ID", "sequence number"). The artifact subsystem now uses short names as the canonical identifier for artifacts (chunks, subsystems, investigations, narratives), and the `ve` CLI handles ID resolution internally.

This cleanup ensures agents following the slash commands don't get confused by outdated instructions that reference a numbering scheme that no longer exists in the artifact system.

## Success Criteria

- All `.claude/commands/*.md` files audited for sequence number references
- References to `NNNN-` prefix patterns removed or updated to use short names
- Instructions that tell agents to "extract" or "decompose" sequence numbers replaced with direct CLI usage (e.g., `ve chunk validate <chunk_directory>`)
- Documentation examples updated to use short-name format where applicable
- No grep matches for deprecated patterns: `sequence`, `sequential ID`, `prefix number`, `NNNN-` used as variable/placeholder patterns

