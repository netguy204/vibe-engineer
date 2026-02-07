---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/cli/chunk.py
  - src/cli/narrative.py
  - src/cli/investigation.py
  - src/cli/subsystem.py
  - src/cli/friction.py
  - tests/test_chunk_list.py
  - tests/test_narrative_list.py
  - tests/test_investigation_list.py
  - tests/test_subsystem_list.py
  - tests/test_friction.py
code_references:
  - ref: src/cli/chunk.py#_chunk_to_json_dict
    implements: "Helper function for JSON serialization of chunk frontmatter using Pydantic's model_dump()"
  - ref: src/cli/chunk.py#_format_grouped_artifact_list_json
    implements: "JSON output formatter for grouped artifact listings in task context mode"
  - ref: src/cli/chunk.py#list_chunks
    implements: "CLI command with --json flag for outputting chunks as JSON array"
  - ref: src/cli/chunk.py#_list_task_chunks
    implements: "Cross-repo chunk listing handler with JSON output support"
  - ref: src/cli/narrative.py#_narrative_to_json_dict
    implements: "Helper function for JSON serialization of narrative frontmatter"
  - ref: src/cli/narrative.py#list_narratives
    implements: "CLI command with --json flag for outputting narratives as JSON array"
  - ref: src/cli/narrative.py#_list_task_narratives_cmd
    implements: "Cross-repo narrative listing handler with JSON output support"
  - ref: src/cli/investigation.py#_investigation_to_json_dict
    implements: "Helper function for JSON serialization of investigation frontmatter"
  - ref: src/cli/investigation.py#list_investigations
    implements: "CLI command with --json flag for outputting investigations as JSON array"
  - ref: src/cli/investigation.py#_list_task_investigations
    implements: "Cross-repo investigation listing handler with JSON output support"
  - ref: src/cli/subsystem.py#_subsystem_to_json_dict
    implements: "Helper function for JSON serialization of subsystem frontmatter"
  - ref: src/cli/subsystem.py#list_subsystems
    implements: "CLI command with --json flag for outputting subsystems as JSON array"
  - ref: src/cli/subsystem.py#_list_task_subsystems
    implements: "Cross-repo subsystem listing handler with JSON output support"
  - ref: src/cli/friction.py#list_entries
    implements: "CLI command with --json flag for outputting friction entries as JSON array"
  - ref: tests/test_chunk_list.py#TestJsonOutput
    implements: "Test class for ve chunk list --json functionality"
  - ref: tests/test_narrative_list.py#TestNarrativeListJsonOutput
    implements: "Test class for ve narrative list --json functionality"
  - ref: tests/test_investigation_list.py#TestInvestigationListJsonOutput
    implements: "Test class for ve investigation list --json functionality"
  - ref: tests/test_subsystem_list.py#TestSubsystemListJsonOutput
    implements: "Test class for ve subsystem list --json functionality"
  - ref: tests/test_friction_cli.py#TestFrictionListJsonOutput
    implements: "Test class for ve friction list --json functionality"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
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

FUTURE CHUNK APPROVAL REQUIREMENT:
ALL FUTURE chunks require operator approval before committing or injecting.
After refining this GOAL.md, you MUST present it to the operator and wait for
explicit approval. Do NOT commit or inject until the operator approves.
This applies whether triggered by "in the background", "create a future chunk",
or any other mechanism that creates a FUTURE chunk.

COMMIT BOTH FILES: When committing a FUTURE chunk after approval, add the entire
chunk directory (both GOAL.md and PLAN.md) to the commit, not just GOAL.md. The
`ve chunk create` command creates both files, and leaving PLAN.md untracked will
cause merge conflicts when the orchestrator creates a worktree for the PLAN phase.

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
- If this is the final chunk of a narrative, the narrative status should be set to COMPLETED
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

DEPENDS_ON:
- Declares explicit implementation dependencies that affect orchestrator scheduling
- Format: list of chunk directory name strings, or null
- Default: [] (empty list - explicitly no dependencies)

VALUE SEMANTICS (how the orchestrator interprets this field):

| Value             | Meaning                              | Oracle behavior   |
|-------------------|--------------------------------------|-------------------|
| `null` or omitted | "I don't know my dependencies"       | Consult oracle    |
| `[]` (empty list) | "I explicitly have no dependencies"  | Bypass oracle     |
| `["chunk_a"]`     | "I depend on these specific chunks"  | Bypass oracle     |

CRITICAL: The default `[]` means "I have analyzed this chunk and it has no dependencies."
This is an explicit assertion, not a placeholder. If you haven't analyzed dependencies yet,
change the value to `null` (or remove the field entirely) to trigger oracle consultation.

WHEN TO USE EACH VALUE:
- Use `[]` when you have analyzed the chunk and determined it has no implementation dependencies
  on other chunks in the same batch. This tells the orchestrator to skip conflict detection.
- Use `null` when you haven't analyzed dependencies yet and want the orchestrator's conflict
  oracle to determine if this chunk conflicts with others.
- Use `["chunk_a", "chunk_b"]` when you know specific chunks must complete before this one.

WHY THIS MATTERS:
The orchestrator's conflict oracle adds latency and cost to detect potential conflicts.
When you declare `[]`, you're asserting independence and enabling the orchestrator to
schedule immediately. When you declare `null`, you're requesting conflict analysis.

PURPOSE AND BEHAVIOR:
- When a list is provided (empty or not), the orchestrator uses it directly for scheduling
- When null, the orchestrator consults its conflict oracle to detect dependencies heuristically
- Dependencies express order within a single injection batch (intra-batch scheduling)
- The chunks listed in depends_on will be scheduled to complete before this chunk starts

CONTRAST WITH created_after:
- `created_after` tracks CAUSAL ORDERING (what work existed when this chunk was created)
- `depends_on` tracks IMPLEMENTATION DEPENDENCIES (what must complete before this chunk runs)
- `created_after` is auto-populated at creation time and should NOT be modified manually
- `depends_on` is agent-populated based on design requirements and may be edited

WHEN TO DECLARE EXPLICIT DEPENDENCIES:
- When you know chunk B requires chunk A's implementation to exist before B can work
- When the conflict oracle would otherwise miss a subtle dependency
- When you want to enforce a specific execution order within a batch injection
- When a narrative or investigation explicitly defines chunk sequencing

EXAMPLE:
  # Chunk has no dependencies (explicit assertion - bypasses oracle)
  depends_on: []

  # Chunk dependencies unknown (triggers oracle consultation)
  depends_on: null

  # Chunk B depends on chunk A completing first
  depends_on: ["auth_api"]

  # Chunk C depends on both A and B completing first
  depends_on: ["auth_api", "auth_client"]

VALIDATION:
- `null` is valid and triggers oracle consultation
- `[]` is valid and means "explicitly no dependencies" (bypasses oracle)
- Referenced chunks should exist in docs/chunks/ (warning if not found)
- Circular dependencies will be detected at injection time
- Dependencies on ACTIVE chunks are allowed (they've already completed)
-->

# Chunk Goal

## Minor Goal

Add machine-readable JSON output to artifact list commands, improving tooling integration and agent usability. Currently, orchestrator commands like `ve orch status` support `--json` output for programmatic access, but artifact commands (`ve chunk list`, `ve narrative list`, etc.) only provide human-readable text output. This asymmetry makes it harder to build tooling and agent workflows on top of artifact queries.

This chunk adds a `--json` flag to all artifact list commands that outputs structured JSON including directory names, status values, and frontmatter metadata. This enables agents and scripts to reliably parse artifact listings without fragile text parsing.

## Success Criteria

- `ve chunk list --json` outputs valid JSON array of chunk objects with fields: `name`, `status`, and all frontmatter fields (ticket, parent_chunk, narrative, investigation, subsystems, friction_entries, code_paths, code_references, depends_on, created_after)
- `ve narrative list --json` outputs valid JSON array of narrative objects with fields: `name`, `status`, and relevant frontmatter
- `ve investigation list --json` outputs valid JSON array of investigation objects with fields: `name`, `status`, and relevant frontmatter
- `ve subsystem list --json` outputs valid JSON array of subsystem objects with fields: `id`, `name`, and relevant frontmatter
- `ve friction list --json` outputs valid JSON array of friction entries with fields: `entry_id`, `status`, and content metadata
- JSON output follows the same filtering behavior as text output (e.g., `--status`, `--current`, `--recent` flags work correctly with `--json`)
- JSON output is parseable by standard tools (`jq`, Python's `json.loads()`)
- Pattern follows existing `--json` implementation in `ve orch status` (see `src/cli/orch.py` lines 61-71)
- External artifact references and parse errors are represented clearly in JSON output


