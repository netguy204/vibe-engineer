---
status: ACTIVE
ticket: null
parent_chunk: null
code_references:
- ref: src/templates/chunk/PLAN.md.jinja2
  implements: Backreference guidance in chunk PLAN.md template
- ref: src/templates/subsystem/OVERVIEW.md.jinja2
  implements: Backreference guidance in subsystem OVERVIEW.md template
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: Code Backreferences section documenting the convention
- ref: src/templates/commands/chunk-update-references.md.jinja2
  implements: Backreference maintenance during reference reconciliation
- ref: CLAUDE.md
  implements: Code Backreferences section in project CLAUDE.md
narrative: null
subsystems:
- subsystem_id: template_system
  relationship: uses
created_after:
- document_investigations
---

# Chunk Goal

## Minor Goal

Add bidirectional references from source code back to the chunks and subsystems that
created or govern them. Currently, documentation references code (via `code_references`
in chunk GOAL.md and subsystem OVERVIEW.md), but the code itself has no way to point
an exploring agent back to the business context that motivated it.

This chunk closes that loop by:

1. **Defining a backreference comment convention** for Python source files that links
   code to its originating chunk or governing subsystem
2. **Updating the PLAN.md template** to instruct agents to add these backreferences
   during implementation
3. **Updating the subsystem OVERVIEW.md template** to instruct agents to add
   backreferences when discovering subsystems
4. **Retroactively adding backreferences** to all existing code that is referenced
   by chunks and subsystems

This enables agents exploring the codebase to immediately recognize that documentation
context exists and where to find it, rather than having to search or guess.

## Backreference Format

Comments should be placed at the semantic level matching what the chunk or subsystem
describes:

- **Module-level**: If the chunk created the entire file
- **Class-level**: If the chunk created or significantly modified a class
- **Method-level**: If the chunk added nuance to a specific method

Format (Python):
```python
# Chunk: docs/chunks/0031-code_to_docs_backrefs - Bidirectional code-to-docs references
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
```

The format includes the ID and a brief description to provide immediate context
without requiring the agent to open the referenced document.

## Multiple Chunk References

When code has been touched by multiple chunks over time (e.g., initial creation then
later refinement), **all relevant chunks should be listed** in the backreference
comments:

```python
# Chunk: docs/chunks/0012-symbolic_code_refs - Symbolic code reference format
# Chunk: docs/chunks/0018-bidirectional_refs - Bidirectional chunk-subsystem linking
# Subsystem: docs/subsystems/0001-template_system - Unified template rendering
```

If a chunk's contribution to that code has been truly superseded (the code no longer
reflects that chunk's work), the chunk's `code_references` entry should be removed
from its GOAL.md - which means no backreference comment is needed.

## Success Criteria

1. **PLAN.md template updated**: The `src/templates/chunk/PLAN.md.jinja2` template
   includes guidance in the Sequence section instructing agents to add backreference
   comments to code they create or modify

2. **Subsystem template updated**: The `src/templates/subsystem/OVERVIEW.md.jinja2`
   template includes guidance instructing agents to add subsystem backreference
   comments to canonical implementation code

3. **Existing chunk backreferences added**: All `code_references` in existing chunk
   GOAL.md files have corresponding backreference comments in the source code

4. **Existing subsystem backreferences added**: All `code_references` in existing
   subsystem OVERVIEW.md files have corresponding backreference comments in the
   source code

5. **Comments list all relevant chunks**: When multiple chunks reference the same
   code location, all are listed (not just the most recent)

6. **CLAUDE.md updated**: The project's CLAUDE.md documents this backreference
   convention so agents exploring code know to look for these comments and
   understand their meaning