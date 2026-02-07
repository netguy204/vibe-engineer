---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/models.py
  - src/orchestrator/agent.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/state.py
  - src/cli/orch.py
  - src/templates/commands/chunk-rebase.md.jinja2
  - .claude/commands/chunk-rebase.md
  - tests/test_orchestrator_scheduler.py
code_references: []
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_exit_codes
- cli_help_text
- cli_json_output
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

Add a REBASE phase to the orchestrator's phase progression between IMPLEMENT and REVIEW. When parallel chunks are running, branches diverge from main as other chunks merge in. Currently this divergence is only discovered at final merge time (after COMPLETE), producing conflicts that halt automation and require manual operator intervention.

The REBASE phase merges the current trunk (main) into the worktree branch and runs an agent to resolve any conflicts in the context of the active chunk's goal. This means the REVIEW phase sees clean, already-integrated code — reviewing what will actually ship rather than a stale snapshot.

**Current phase progression:**
```
PLAN → IMPLEMENT → REVIEW → COMPLETE → merge to main
```

**New phase progression:**
```
PLAN → IMPLEMENT → REBASE → REVIEW → COMPLETE → merge to main
```

**What the REBASE phase does:**

The REBASE phase is entirely agent-driven. The scheduler spawns an agent in the worktree with instructions to:

1. Commit any uncommitted work left by the IMPLEMENT phase (the implementer may have forgotten to stage files, or may have left work across multiple commits that should be consolidated)
2. Merge the current trunk (main) into the worktree branch
3. If conflicts arise, resolve them in light of the chunk's GOAL.md — keep the chunk's changes where they implement the goal, accept trunk changes elsewhere
4. Run the project's test suite to verify the integrated result
5. Report success or failure

If the agent succeeds, the phase advances to REVIEW. If the agent cannot resolve conflicts or tests fail, the work unit is marked NEEDS_ATTENTION for operator help.

**Why agent-driven, not mechanical:**

The agent needs the full context of the chunk to handle the messy realities of the post-IMPLEMENT state. The IMPLEMENT phase may leave uncommitted files, may have produced multiple partial commits, or may have modified files that trunk also changed. A mechanical merge would lose the context needed to make the right decisions about all of this. The agent reads the GOAL.md, understands what the chunk is trying to accomplish, and can make informed choices about staging, commit consolidation, and conflict resolution as a unified operation.

This directly reduces the friction identified during the architecture review: every manual merge resolution we performed was caused by branches that diverged while running in parallel. By resolving conflicts before the reviewer sees the code, we also get higher-quality reviews since the reviewer evaluates the code in its actual integration context.

## Success Criteria

- A new `WorkUnitPhase.REBASE` value exists in the phase enum
- The phase progression map in `scheduler.py:907-913` includes `IMPLEMENT → REBASE` and `REBASE → REVIEW`
- On entering REBASE, the scheduler always spawns an agent in the worktree
- The agent commits any uncommitted work from the IMPLEMENT phase before merging
- The agent merges main into the worktree branch and resolves any conflicts in light of the chunk's GOAL.md
- The agent runs the test suite to verify the integrated result
- On agent success, the phase advances to REVIEW
- On agent failure (unresolvable conflicts or test failures), the work unit is marked NEEDS_ATTENTION with a descriptive reason including which files conflicted
- The state store migration adds REBASE as a valid phase value
- A REBASE-specific agent prompt template is created that instructs the agent on the commit-merge-resolve-test workflow
- Existing work units in IMPLEMENT phase are unaffected (they'll hit REBASE on their next phase transition)
- All existing scheduler tests pass; new tests cover: clean merge, conflicting merge with agent resolution, uncommitted work handling, and unresolvable merge (NEEDS_ATTENTION)
- The `ve orch status` and dashboard correctly display work units in REBASE phase

## Rejected Ideas

### Rebase instead of merge

We considered using `git rebase main` instead of `git merge main` to maintain linear history. Rejected because: rebase rewrites commit history, which complicates the log trail that the REVIEW and COMPLETE phases rely on. Merge commits are explicit about what was integrated and when. The worktree branches are short-lived anyway — linear history is a concern for main, not for ephemeral orch branches.

### Rebase before every phase

We considered merging trunk before every phase (PLAN, IMPLEMENT, REVIEW, COMPLETE). Rejected because: PLAN and IMPLEMENT phases actively modify files, and a trunk merge mid-work would create unnecessary disruption. The sweet spot is after IMPLEMENT completes and before REVIEW starts — the implementation is done, so we're integrating a stable set of changes.

### Mechanical merge with agent only on conflict

We considered having the scheduler perform `git merge main` mechanically first, then only spawning an agent if conflicts arise (skipping agent invocation on clean merges as a fast path). Rejected because: the IMPLEMENT phase may leave uncommitted files or multiple partial commits that need consolidation before merging. A mechanical merge would lose the context needed to handle these cases. The agent needs to see the full post-IMPLEMENT state to make informed decisions about staging, commit consolidation, and conflict resolution as a unified operation.