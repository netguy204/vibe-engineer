---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_activate_on_inject"]
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
-->

# Chunk Goal

## Minor Goal

Defer git worktree creation until work can actually begin execution, rather than creating worktrees at inject time.

Currently, when work is injected via `ve orch inject`, the worktree is created immediately. This is problematic because:

1. **Stale base state**: A worktree created at inject time reflects the repository state when the work was queued, not when it actually runs. If the work is blocked or there are no agent slots available, other work may complete and change the repository before this work starts.

2. **Blocked work sees outdated code**: Work that depends on other chunks (via `created_after`) gets a worktree based on the state *before* its dependencies complete. The work should see the state *after* its dependencies have merged.

3. **Resource waste**: Creating worktrees for work that can't run yet consumes disk space and git resources unnecessarily.

**Solution**: Create worktrees at the moment a work unit transitions from READY to RUNNING (i.e., when an agent slot becomes available and the scheduler dispatches the work). This ensures:
- The worktree reflects the most current repository state
- Blocked work sees the changes from the work it was waiting on
- Resources are allocated only when actually needed

## Success Criteria

1. **Worktree creation moved to dispatch time**
   - `ve orch inject` does NOT create a worktree
   - Worktree is created in `Scheduler._run_work_unit()` just before agent execution begins
   - The worktree is created from the current HEAD at dispatch time, not inject time

2. **Blocked work waits for current state**
   - Work with unmet dependencies (BLOCKED status) does not have a worktree
   - When dependencies complete and work transitions BLOCKED → READY → RUNNING, worktree is created at RUNNING transition
   - The worktree reflects repository state after dependency merges

3. **Queue-only work has no worktree**
   - Work units in READY status waiting for agent slots do not have worktrees
   - Only RUNNING work units have worktrees

4. **Tests validate deferred creation**
   - Integration test: inject work, verify no worktree exists, start agent, verify worktree created
   - Integration test: blocked work gains worktree only when dependencies complete and it starts running
   - Existing tests continue to pass (worktree cleanup, phase execution, etc.)

