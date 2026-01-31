---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Creating Artifacts section with artifact creation guidance"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
created_after:
- chunklist_external_status
- orch_url_command
---

# Chunk Goal

## Minor Goal

Add instructions to the CLAUDE.md Jinja2 template that remind agents they should never manually create GOAL.md or PLAN.md files. Instead, they must use the appropriate artifact creation commands (`ve chunk create`, `/chunk-create`, etc.) to instantiate templates properly.

This prevents agents from bypassing the template system and creating malformed artifacts missing required frontmatter or structure.

## Success Criteria

1. `src/templates/claude/CLAUDE.md.jinja2` includes clear instruction that agents must NOT manually create GOAL.md or PLAN.md files
2. Instruction specifies to use `ve chunk create` or `/chunk-create` instead
3. Instruction applies to all artifact types (chunks, investigations, narratives, subsystems)
4. Run `ve init` to regenerate CLAUDE.md and verify the new guidance appears

