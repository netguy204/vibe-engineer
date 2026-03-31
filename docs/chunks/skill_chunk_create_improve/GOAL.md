---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-create.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "Skill description improvement for discoverability and context capture instructions for implementing agents"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_analytics_domain
---

# Chunk Goal

## Minor Goal

Improve the `/chunk-create` skill template to address two problems:

1. **Discoverability** — The skill description should ensure it triggers when
   the user asks to "create a chunk", "start new work", "make a chunk for X",
   etc. Review the current description and make it more trigger-friendly.

2. **Completeness for autonomous agents** — The GOAL.md template and the
   skill instructions should guide the creating agent to include ALL relevant
   context the implementing agent will need. The implementing agent won't have
   access to the conversation where the chunk was created, so the goal must be
   self-contained. This means:
   - Specific file paths, function names, and code patterns referenced in the
     conversation
   - Error messages or reproduction steps for bugs
   - Design decisions and rejected alternatives
   - Links to related chunks, investigations, or subsystems
   - Any operator preferences or constraints mentioned in conversation

Study the current `src/templates/commands/chunk-create.md.jinja2` template and
improve both the skill description (for discoverability) and the instructions
(for completeness).

## Success Criteria

- The skill description triggers on natural phrases like "create a chunk",
  "start a new chunk", "chunk this work"
- The template instructions explicitly prompt the agent to capture conversation
  context that would be lost when handing off to an implementing agent
- The GOAL.md template includes guidance for self-contained goals
- Existing chunk-create functionality is preserved (naming, frontmatter, etc.)
