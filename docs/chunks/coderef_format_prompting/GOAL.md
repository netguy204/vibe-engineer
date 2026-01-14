---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/chunks.py
- src/task_utils.py
- src/templates/chunk/GOAL.md.jinja2
- tests/test_models.py
- tests/test_chunks.py
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
created_after:
- taskdir_context_cmds
---
<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
║                                                                              ║
║  AGENT INSTRUCTIONS: When editing this file, preserve this entire comment    ║
║  block. Only modify the frontmatter YAML and the content sections below      ║
║  (Minor Goal, Success Criteria, Relationship to Parent). Use targeted edits  ║
║  that replace specific sections rather than rewriting the entire file.       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This comment describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- FUTURE: This chunk is queued for future work and not yet being implemented
- IMPLEMENTING: This chunk is in the process of being implemented.
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only


BACKGROUND WORKFLOW NOTE:
When a FUTURE chunk is created via the "background" keyword (operator says "in the background"),
you MUST present the GOAL.md to the operator for review before committing or injecting.
The background keyword indicates work should be queued, not that it's pre-approved.

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

INVESTIGATION:
- If this chunk was derived from an investigation's proposed_chunks, reference the investigation
  directory name (e.g., "memory_leak" for docs/investigations/memory_leak/).
- This provides traceability from implementation work back to exploratory findings.
- When implementing, read the referenced investigation's OVERVIEW.md for context on findings,
  hypotheses tested, and decisions made during exploration.
- Validated by `ve chunk validate` to ensure referenced investigations exist.

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

FRICTION_ENTRIES:
- Optional list of friction entries that this chunk addresses
- Provides "why did we do this work?" traceability from implementation back to accumulated pain points
- Format: entry_id is the friction entry ID (e.g., "F001"), scope is "full" or "partial"
  - "full": This chunk fully resolves the friction entry
  - "partial": This chunk partially addresses the friction entry
- When to populate: During /chunk-create if this chunk addresses known friction from FRICTION.md
- Example:
  friction_entries:
    - entry_id: F001
      scope: full
    - entry_id: F003
      scope: partial
- Validated by `ve chunk validate` to ensure referenced friction entries exist in FRICTION.md
- When a chunk addresses friction entries and is completed, those entries are considered RESOLVED


BUG_TYPE:
- Optional field for bug fix chunks that guides agent behavior at completion
- Values: semantic | implementation | null (for non-bug chunks)
  - "semantic": The bug revealed new understanding of intended behavior
    - Code backreferences REQUIRED (the fix adds to code understanding)
    - On completion, search for other chunks that may need updating
    - Status → ACTIVE (the chunk asserts ongoing understanding)
  - "implementation": The bug corrected known-wrong code
    - Code backreferences MAY BE SKIPPED (they don't add semantic value)
    - Focus purely on the fix
    - Status → HISTORICAL (point-in-time correction, not an ongoing anchor)
- Leave null for feature chunks and other non-bug work

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/0042-foo/migrate.py)
- These artifacts help future archaeologists understand what the chunk did
- Unlike code in src/, chunk artifacts are not expected to be maintained long-term
- Examples: data migration scripts, one-time fixups, analysis tools used during implementation


CREATED_AFTER:
- Auto-populated by `ve chunk create` - DO NOT MODIFY manually
- Lists the "tips" of the chunk DAG at creation time (chunks with no dependents yet)
- Tips must be ACTIVE chunks (shipped work that has been merged)
- Example: created_after: ["auth_refactor", "api_cleanup"]

IMPORTANT - created_after is NOT implementation dependencies:
- created_after tracks CAUSAL ORDERING (what work existed when this chunk was created)
- It does NOT mean "chunks that must be implemented before this one can work"
- FUTURE chunks can NEVER be tips (they haven't shipped yet)

COMMON MISTAKE: Setting created_after to reference FUTURE chunks because they
represent design dependencies. This is WRONG. If chunk B conceptually depends on
chunk A's implementation, but A is still FUTURE, B's created_after should still
reference the current ACTIVE tips, not A.

WHERE TO TRACK IMPLEMENTATION DEPENDENCIES:
- Investigation proposed_chunks ordering (earlier = implement first)
- Narrative chunk sequencing in OVERVIEW.md
- Design documents describing the intended build order
- The `created_after` field will naturally reflect this once chunks ship
-->

# Chunk Goal

## Minor Goal

Fix the mismatch between the chunk template's code reference examples and the
`SymbolicReference` validator's requirements in task context.

**The bug:** The GOAL.md template (`src/templates/chunk/GOAL.md.jinja2` lines
54-61) shows examples with short repo names:
```yaml
- ref: dotter::xr#worktrees
- ref: vibe-engineer::src/chunks.py#Chunks::create
```

But the `SymbolicReference.validate_ref()` method (`src/models.py:422`) requires
full `org/repo::` format, rejecting short names like `pybusiness::`.

Agents follow the template examples exactly, then `ve chunk validate` fails with
an unhelpful "Could not parse frontmatter" error that doesn't explain the actual
format requirement.

**Three fixes needed:**

1. **Template fix**: Update examples to use full `org/repo::` format and add
   guidance telling agents where to find project names
2. **Template expansion**: During `ve task init` (or chunk create in task
   context), expand template examples using actual project names from
   `.ve-task.yaml` so agents see real examples like `cloudcapitalco/pybusiness::`
   instead of generic `acme/dotter::`
3. **Validator fix**: Improve error message to explain the required format so
   agents (and chunk-complete) can self-correct

## Success Criteria

- Template examples in `src/templates/chunk/GOAL.md.jinja2` use full `org/repo::`
  format and include guidance: "See `.ve-task.yaml` projects list for org/repo names"
- When rendering chunk GOAL.md in task context, examples use actual project names
  from the task config (e.g., `cloudcapitalco/pybusiness::` not `acme/dotter::`)
- `SymbolicReference.validate_ref()` error message explicitly states:
  "project qualifier must be in 'org/repo' format (e.g., 'acme/project::path'),
  got 'pybusiness'"
- Error message includes the actual invalid value to help debugging
- `parse_chunk_frontmatter()` surfaces the validation error detail instead of
  returning generic "Could not parse frontmatter"
- Existing tests pass; new tests cover template expansion and improved error message

