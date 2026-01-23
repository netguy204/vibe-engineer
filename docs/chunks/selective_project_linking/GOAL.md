---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/ve.py
- tests/test_task_chunk_create.py
- tests/test_task_narrative_create.py
- tests/test_task_investigation_create.py
- tests/test_task_subsystem_discover.py
code_references:
  - ref: src/task_utils.py#parse_projects_option
    implements: "Parse --projects CLI option into resolved project refs"
  - ref: src/task_utils.py#create_task_chunk
    implements: "Optional project filtering for task chunk creation"
  - ref: src/task_utils.py#create_task_narrative
    implements: "Optional project filtering for task narrative creation"
  - ref: src/task_utils.py#create_task_investigation
    implements: "Optional project filtering for task investigation creation"
  - ref: src/task_utils.py#create_task_subsystem
    implements: "Optional project filtering for task subsystem creation"
  - ref: src/ve.py#create
    implements: "--projects CLI option for ve chunk create"
  - ref: src/ve.py#_start_task_chunk
    implements: "Task directory chunk creation with selective project linking"
  - ref: src/ve.py#create_narrative
    implements: "--projects CLI option for ve narrative create"
  - ref: src/ve.py#_create_task_narrative
    implements: "Task directory narrative creation with selective project linking"
  - ref: src/ve.py#create_investigation
    implements: "--projects CLI option for ve investigation create"
  - ref: src/ve.py#_create_task_investigation
    implements: "Task directory investigation creation with selective project linking"
  - ref: src/ve.py#discover
    implements: "--projects CLI option for ve subsystem discover"
  - ref: src/ve.py#_create_task_subsystem
    implements: "Task directory subsystem creation with selective project linking"
  - ref: tests/test_task_chunk_create.py#TestChunkCreateSelectiveProjects
    implements: "Tests for selective project linking in chunk creation"
  - ref: tests/test_task_narrative_create.py#TestNarrativeCreateSelectiveProjects
    implements: "Tests for selective project linking in narrative creation"
  - ref: tests/test_task_investigation_create.py#TestInvestigationCreateSelectiveProjects
    implements: "Tests for selective project linking in investigation creation"
  - ref: tests/test_task_subsystem_discover.py#TestSubsystemDiscoverSelectiveProjects
    implements: "Tests for selective project linking in subsystem discovery"
narrative: null
investigation: selective_artifact_linking
subsystems: []
created_after:
- friction_template_and_cli
- orch_conflict_template_fix
- orch_sandbox_enforcement
- orch_blocked_lifecycle
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

Add optional `--projects` flag to task artifact creation commands (`ve chunk create`, `ve investigation create`, `ve narrative create`, `ve subsystem create`) that filters which projects receive `external.yaml` references.

This enables operators to scope artifacts to relevant projects at creation time, reducing noise in project chunk histories while maintaining backward compatibility (omitting the flag links to all projects as before).

See investigation `docs/investigations/selective_artifact_linking/OVERVIEW.md` for full context, UX design exploration, and scenario pressure testing.

## Success Criteria

- `ve chunk create foo --projects svc-a,svc-b` creates external.yaml only in specified projects
- `ve chunk create foo` (no flag) links to all projects (backward compatible)
- Flag accepts flexible input: full `org/repo` or just `repo` name
- All four artifact types support the flag: chunk, investigation, narrative, subsystem
- Help text documents the flag behavior
- Tests cover selective linking, all-projects default, and invalid project handling

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->