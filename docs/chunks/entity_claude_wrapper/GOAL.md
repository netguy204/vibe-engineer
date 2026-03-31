---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- src/cli/entity.py
- tests/test_entity_claude_cli.py
code_references: []
narrative: null
investigation: entity_session_harness
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- entity_session_tracking
- entity_transcript_extractor
- entity_api_memory_extraction
created_after:
- entity_session_tracking
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
- Format: subsystem_id is the subsystem directory name, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "validation"
      relationship: implements
    - subsystem_id: "frontmatter"
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
  should be stored in the chunk directory (e.g., docs/chunks/foo/migrate.py)
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

Create `ve entity claude --entity <name>` CLI command that implements the full entity
session lifecycle: launching Claude Code with entity startup, capturing the session on
exit, archiving the transcript, running shutdown for memory consolidation, and logging
the session.

This is the main user-facing command. The operator types `ve entity claude --entity steward`
and gets a fully managed entity session with automatic memory extraction on exit.

### Full lifecycle sequence

```
ve entity claude --entity steward
  │
  ├─ 1. Verify entity exists in .entities/steward/
  │
  ├─ 2. Launch: claude --prompt "/entity-startup steward"
  │     └─ Capture the subprocess PID
  │
  ├─ 3. User works... (any exit path: Ctrl+C, /exit, crash)
  │
  ├─ 4. On exit: read ~/.claude/sessions/<pid>.json → extract sessionId
  │
  ├─ 5. Archive transcript: copy ~/.claude/projects/<encoded>/<sessionId>.jsonl
  │     into .entities/steward/sessions/<sessionId>.jsonl
  │     (must happen before Claude Code can garbage collect it)
  │
  ├─ 6. Attempt shutdown via resume:
  │     claude --resume <sessionId> --prompt "/entity-shutdown steward"
  │     (the original agent reflects on its session and extracts memories)
  │
  ├─ 7. If resume fails (non-zero exit or timeout):
  │     Fall back to API-driven extraction:
  │     - Parse archived transcript via entity_transcript.py
  │     - Call shutdown_from_transcript() from entity_shutdown.py
  │
  └─ 8. Log session to .entities/steward/sessions.jsonl
        Print summary: session ID, transcript archived, memories extracted, consolidation results
```

### What to build

**1. New CLI command** in `src/cli/entity.py`:

```python
@entity.command()
@click.option("--entity", required=True, help="Entity name")
@click.pass_context
def claude(ctx, entity):
    """Launch Claude Code with entity lifecycle management."""
```

**2. Subprocess management:**
- Launch `claude --prompt "/entity-startup <name>"` via `subprocess.Popen`
- Capture the PID
- Wait for the process to exit (pass through stdin/stdout/stderr so the user gets
  the normal interactive Claude Code experience)
- On exit, read the session ID from `~/.claude/sessions/<pid>.json`

**3. Session ID extraction:**
- The file at `~/.claude/sessions/<pid>.json` is a JSON object keyed by PID string
  (or it may be a direct object with `sessionId` field — verify during implementation)
- Extract the `sessionId` UUID

**4. Post-exit sequence:**
- Call `entities.archive_transcript(entity_name, session_id, project_path)` (from entity_session_tracking)
- Attempt `claude --resume <sessionId> --prompt "/entity-shutdown <name>"` as a subprocess
  - Set a reasonable timeout (e.g., 5 minutes)
  - If it exits 0, shutdown succeeded via agent self-reflection
- If resume fails: call `shutdown_from_transcript()` (from entity_api_memory_extraction)
  using the archived transcript
- Call `entities.append_session(entity_name, session_record)` to log the session

**5. Output:**
- Print a summary to the terminal after shutdown completes:
  ```
  Entity session complete:
    Session ID: <uuid>
    Transcript archived: .entities/steward/sessions/<uuid>.jsonl
    Shutdown method: resume (or: transcript fallback)
    Memories extracted: N journals, M consolidated, K core
  ```

### Edge cases

- Entity doesn't exist → error with helpful message
- Session PID file not found → warn but still try to find session from sessions-index
- Transcript not found → warn, skip archiving, skip fallback extraction (resume may still work)
- Resume times out → kill the resume process, fall back to transcript extraction
- The `claude` binary must be on PATH — don't hardcode a path

## Success Criteria

- `ve entity claude --entity steward` launches Claude Code with `/entity-startup steward` injected
- The user gets a normal interactive Claude Code session (stdin/stdout pass-through)
- On exit, the session ID is captured and the transcript is archived
- Shutdown is attempted via resume first, with transcript extraction as fallback
- The session is logged to sessions.jsonl with timestamps
- A human-readable summary is printed after shutdown
- Tests cover the orchestration logic (with subprocess mocking)