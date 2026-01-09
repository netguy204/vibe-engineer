---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
subsystems:
  - subsystem_id: "0001-template_system"
    relationship: uses
---

<!--
DO NOT DELETE THIS COMMENT until the chunk complete command is run.
This describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- FUTURE: This chunk is queued for future work and not yet being implemented
- IMPLEMENTING: This chunk is in the process of being implemented.
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only

PARENT_CHUNK:
- null for new work
- chunk directory name (e.g., "006-segment-compaction") for corrections or modifications

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Populated after implementation, before PR
- Uses symbolic references to identify code locations
- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Example:
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
    - ref: src/segment/writer.rs#SegmentWriter::fsync
      implements: "Durability guarantees"
    - ref: src/utils.py#validate_input
      implements: "Input validation logic"

NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name.
- When setting this field during /chunk-create, also update the narrative's OVERVIEW.md
  frontmatter to add this chunk to its `chunks` array with the prompt and chunk_directory.
- If this is the final chunk of a narrative, the narrative status should be set to completed
  when this chunk is completed.

SUBSYSTEMS:
- Optional list of subsystem references that this chunk relates to
- Format: subsystem_id is {NNNN}-{short_name}, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "0001-validation"
      relationship: implements
    - subsystem_id: "0002-frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section.
-->

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
# Chunk: 0031-code_to_docs_backrefs - Bidirectional code-to-docs references
# Subsystem: 0001-template_system - Unified template rendering
```

The format includes the ID and a brief description to provide immediate context
without requiring the agent to open the referenced document.

## Multiple Chunk References

When code has been touched by multiple chunks over time (e.g., initial creation then
later refinement), **all relevant chunks should be listed** in the backreference
comments:

```python
# Chunk: 0012-symbolic_code_refs - Symbolic code reference format
# Chunk: 0018-bidirectional_refs - Bidirectional chunk-subsystem linking
# Subsystem: 0001-template_system - Unified template rendering
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