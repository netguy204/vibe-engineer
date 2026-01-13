---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: selective_artifact_linking
subsystems:
  - subsystem_id: workflow_artifacts
    relationship: implements
friction_entries: []
created_after: ["cluster_list_command", "cluster_naming_guidance", "friction_chunk_workflow", "narrative_consolidation"]
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

Enable friction logging to participate in task context and implement selective project linking across all artifact creation workflows.

### Part 1: Friction Logging in Task Context

Currently, friction log entries are only recorded in the local project's `docs/trunk/FRICTION.md`. When working in a task context (multi-project work with an external artifact repo), friction should be surfaced as an artifact that links back to the relevant projects—just like chunks, investigations, narratives, and subsystems do.

**Key design constraint**: Unlike other artifacts which get their own directories, `FRICTION.md` is a singleton file in each project. We cannot use the standard `external.yaml` pattern. Instead, we need a mechanism for embedding external references *within* the singleton friction log—likely via frontmatter that lists external friction sources.

### Part 2: Selective Project Linking (`--projects` flag)

Implement the `--projects` flag for all artifact creation workflows so operators can selectively specify which projects an artifact should link to. This implements Option D from the selective artifact linking investigation: flag-based selection with all-projects as the default.

### Part 3: Artifact Subsystem Update

Update the `docs/subsystems/workflow_artifacts/OVERVIEW.md` to add `--projects` as a **hard invariant** for all artifact creation commands in task context. This ensures the capability is consistently available and enforced.

This is the right next step because:
1. Friction logging is currently the only artifact type that doesn't support task context, creating an inconsistency
2. The `--projects` flag is a foundational capability that makes selective linking available across all artifact types
3. Without selective linking, task-context artifacts create noise in project chunk histories by linking to irrelevant projects

## Success Criteria

1. **Friction logging in task context works**: When `ve friction log` is run in a task context:
   - A friction entry is created in the external artifact repo's `docs/trunk/FRICTION.md`
   - The friction entry includes metadata indicating which projects it relates to
   - Projects specified via `--projects` (or all projects if omitted) receive a reference to the external friction entry in their local `FRICTION.md` (via frontmatter or inline reference)

2. **--projects flag available on all artifact commands**: The following commands accept `--projects`:
   - `ve chunk create`
   - `ve investigation create`
   - `ve narrative create`
   - `ve subsystem discover`
   - `ve friction log`

3. **Default behavior preserved**: When `--projects` is omitted, all projects in the task context receive external.yaml references (or equivalent for friction) (backward compatible)

4. **Flexible project specification**: The `--projects` flag accepts:
   - Comma-separated project names (e.g., `--projects service-a,service-b`)
   - Short project names (e.g., `--projects service-a`)
   - Full org/repo refs (e.g., `--projects acme/service-a`)

5. **Task utils integration**: The `create_task_*` functions in `src/task_utils.py` accept an optional `projects` parameter that filters the project iteration loop

6. **Subsystem invariant documented**: `docs/subsystems/workflow_artifacts/OVERVIEW.md` includes a new hard invariant requiring all task-aware artifact creation commands to support `--projects`

7. **All tests pass**: Existing tests continue to pass; new tests cover selective project linking