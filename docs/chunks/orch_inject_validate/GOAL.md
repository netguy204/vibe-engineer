---
status: FUTURE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/ve.py
  - src/orchestrator/api.py
  - tests/test_chunk_validate_inject.py
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["respect_future_intent", "orch_scheduling"]
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

The orchestrator can currently accept chunks in illegal states (e.g., ACTIVE status with no plan content), leading to runtime failures that waste agent cycles. When a chunk is in an inconsistent state, the orchestrator should reject it upfront with a clear error message rather than dispatching an agent that will inevitably fail.

This chunk adds injection-time validation to ensure chunks are in a valid state before being submitted to the work pool. It extends the existing `ve chunk validate` command with injection-specific checks and integrates this validation into `ve orch inject`.

## Success Criteria

1. **New validation function**: `validate_chunk_injectable(chunk_id)` in `src/chunks.py` that returns validation errors
2. **Status-content consistency check**: Detects ACTIVE/IMPLEMENTING status with empty PLAN.md (only template content, no actual plan)
3. **FUTURE status allows empty plan**: FUTURE chunks are allowed to have empty PLAN.md since they haven't been planned yet
4. **CLI integration**: `ve chunk validate --injectable [chunk_id]` performs injection-specific validation
5. **Orchestrator integration**: `ve orch inject` calls validation before creating work unit, rejecting invalid chunks with clear error
6. **Error messages**: Validation errors explain the illegal state and suggest remediation (e.g., "ACTIVE chunk has no plan content - run /chunk-plan first or change status to FUTURE")
7. **Test coverage**: Tests for each illegal state combination

