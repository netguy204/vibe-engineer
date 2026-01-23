---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries:
  - entry_id: "Over-eager conflict oracle causes unnecessary blocking"
    scope: full
created_after: ["artifact_copy_backref", "friction_claude_docs", "friction_template_and_cli", "orch_conflict_template_fix", "orch_sandbox_enforcement", "orch_blocked_lifecycle"]
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

Fix the orchestrator scheduler bug where work units remain stuck in NEEDS_ATTENTION
status after their blocking work units complete. When a blocker completes and is
removed from a work unit's `blocked_by` list, if that list becomes empty, the work
unit should automatically transition from NEEDS_ATTENTION back to READY status.

Currently, the scheduler correctly clears the `blocked_by` list but fails to update
the status, leaving work units orphaned in NEEDS_ATTENTION with stale attention
reasons. This requires manual intervention via `ve orch work-unit status <chunk> READY`.

## Success Criteria

- When a work unit's last blocker completes, the work unit transitions from
  NEEDS_ATTENTION to READY automatically (no manual intervention required)
- The `attention_reason` field is cleared on ANY transition to READY or RUNNING
  (not just unblock scenarios - also manual status changes, retries, etc.)
- The `blocked_by` list is cleared when a work unit transitions to RUNNING
  (currently RUNNING work units still show stale blockers in `ve orch ps`)
- `ve orch ps` output shows no stale reasons or blockers for active work units
- Test coverage for the unblock-to-ready transition path
- Test coverage for reason and blocked_by cleanup on status transitions
- Existing orchestrator tests continue to pass

## Investigation Context

This bug was discovered during `/orchestrator-investigate` when three work units
(`friction_chunk_linking`, `selective_project_linking`, `remove_external_ref`)
were stuck in NEEDS_ATTENTION after their blocker `artifact_copy_backref` completed.

**Observed behavior from logs:**
```
Removed artifact_copy_backref from friction_chunk_linking's blocked_by (remaining: [])
Removed artifact_copy_backref from selective_project_linking's blocked_by (remaining: [])
Removed artifact_copy_backref from remove_external_ref's blocked_by (remaining: [])
```

The `blocked_by` lists were correctly cleared, but the work units remained stuck
with status=NEEDS_ATTENTION and stale attention_reason messages still referencing
`artifact_copy_backref`.

**Likely fix location:** The scheduler code that handles blocker completion
(look for "Removed X from Y's blocked_by" log message) needs to check if
`blocked_by` is now empty and, if so, transition status to READY and clear
`attention_reason`.

**Related issue #1:** The `attention_reason` field persists when work units are
manually reset to READY or when they transition to RUNNING. This causes confusing
output in `ve orch ps` where work units show reasons that no longer apply. The fix
should clear `attention_reason` on any transition to READY or RUNNING.

**Related issue #2:** The `blocked_by` list is not cleared when work units transition
to RUNNING. Observed: `remove_external_ref` was RUNNING but still showed
`friction_chunk_linking` in its BLOCKED BY column even though that chunk was DONE.
The `blocked_by` list should be cleared when a work unit starts running.