---
status: FUTURE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: ["intent_principles"]
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

STATUS VALUES (status answers: how much of the intent does this chunk own?):
- FUTURE: Not yet owned. Queued for later.
- IMPLEMENTING: Being taken into ownership. At most one per worktree.
- ACTIVE: Fully owns the intent that governs the code.
- COMPOSITE: Shares ownership with other chunks. Must be read alongside its co-owners.
- HISTORICAL: No longer owns intent. Kept for archaeological context.

See docs/trunk/CHUNKS.md for the full principle.

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

`SUPERSEDED` is deprecated as a chunk status. The runtime continues to parse `status: SUPERSEDED` for backward compatibility — projects upgrading `ve` keep working without first migrating their corpus. But the on-ramp is closed: the state machine no longer accepts `ACTIVE → SUPERSEDED`, so no new chunk can become SUPERSEDED. The off-ramp (`SUPERSEDED → HISTORICAL`) stays open, so the existing SUPERSEDED set can only shrink as chunks drain organically. A deprecation warning fires when SUPERSEDED is parsed, pointing operators at `docs/trunk/CHUNKS.md` and the active-tense-chunks migration guide.

### Why deprecation, not removal

Removing `SUPERSEDED` from the runtime would create a chicken-and-egg upgrade trap: chunks with `status: SUPERSEDED` would fail Pydantic validation, blocking projects from upgrading; but those projects can't migrate off SUPERSEDED without first upgrading to a `ve` that supports `COMPOSITE`. Deprecation breaks the cycle. Existing SUPERSEDED chunks keep parsing; the on-ramp closes so the set can only shrink; projects migrate at their own pace via the migration chunk and `/audit-intent` skill.

This is the final chunk of the intent-ownership narrative. After it ships, the workflow speaks with one voice — five canonical statuses for new work, with SUPERSEDED still readable but visibly fading.

## Behavior changes

1. **State machine: drop `ACTIVE → SUPERSEDED`.** No chunk can transition into SUPERSEDED anymore. The transition table in `src/models/chunk.py` becomes:
   ```python
   ChunkStatus.ACTIVE: {ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL},  # SUPERSEDED removed
   ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},  # off-ramp preserved
   ```
2. **Keep `ChunkStatus.SUPERSEDED` in the enum.** Projects with existing SUPERSEDED chunks still parse cleanly.
3. **Emit a `DeprecationWarning` when SUPERSEDED is parsed.** Pydantic field validator on `ChunkFrontmatter.status` checks for SUPERSEDED and emits a warning naming the chunk, with a pointer to `docs/trunk/CHUNKS.md` and the migration guide. Once-per-chunk-per-session is fine; no need to spam.
4. **`ve chunk validate` reports SUPERSEDED chunks as a warning, not an error.** The validation surface should make the deprecation visible without breaking validation runs.
5. **CLI help text marks SUPERSEDED as deprecated.** `--status` flag's valid-statuses list either drops SUPERSEDED entirely (it's no longer a target) or annotates it as deprecated. Drop is cleaner — operators creating new work shouldn't see it.

## Documentation

- **`docs/trunk/SPEC.md`** — add a one-line note to the status table (or a sibling block): *"SUPERSEDED is deprecated. The runtime parses it for backward compatibility but no chunk transitions into it. Migrate via the active-tense-chunks migration guide."*
- **`docs/trunk/CHUNKS.md`** — already absent from the principle table. Add a brief footnote-style note at the bottom: *"Older corpora may carry chunks with `status: SUPERSEDED`. The runtime still parses that value but treats it as deprecated; the active-tense-chunks migration moves them into the current taxonomy."*
- **Migration guide** (`site/src/pages/docs/migrations/active-tense-chunks.astro`) — add a section explaining the deprecation status of SUPERSEDED and how the migration chunk drains it.

## Success Criteria

1. `VALID_CHUNK_TRANSITIONS[ChunkStatus.ACTIVE]` no longer includes `SUPERSEDED`.
2. `VALID_CHUNK_TRANSITIONS[ChunkStatus.SUPERSEDED]` still includes `HISTORICAL` (off-ramp preserved).
3. `ChunkStatus.SUPERSEDED` remains a valid enum value (parsing existing SUPERSEDED chunks still succeeds).
4. Parsing a chunk with `status: SUPERSEDED` emits a `DeprecationWarning` once. The warning text names the chunk and points at `docs/trunk/CHUNKS.md` and the migration guide.
5. `ve chunk validate` on a SUPERSEDED chunk produces a warning (not an error) recommending migration.
6. CLI help text for `ve chunk list --status` no longer lists SUPERSEDED as a primary option (or annotates it as deprecated).
7. `docs/trunk/SPEC.md` notes the deprecation in the status section.
8. `docs/trunk/CHUNKS.md` notes the deprecation as a footnote.
9. The active-tense-chunks migration guide explains the deprecation and the drain mechanism.
10. Tests cover: the new transition table (no `ACTIVE → SUPERSEDED`); the deprecation warning fires on parse; `SUPERSEDED → HISTORICAL` still works; `ve chunk validate` warns but doesn't error on SUPERSEDED.
11. `uv run ve init` runs cleanly.
12. `uv run pytest tests/` passes.

## Out of Scope

- **Removing SUPERSEDED from the runtime entirely.** Deferred indefinitely. Removal would only be safe after the entire ecosystem has migrated, and even then the upgrade-cycle risk argues for keeping SUPERSEDED parseable. If a future chunk eventually removes it, that chunk owns the migration coordination problem — not this one.
- **Migrating any specific chunks.** `intent_superseded_migration` (chunk 5 of this narrative) handles that. Chunk 7 doesn't depend on it: deprecation is safe whether the migration has run or not — in fact the deprecation warning *encourages* unmigrated projects to run the migration.
- **Other workflow doc updates.** `intent_workflow_docs` (chunk 4) handles CLAUDE.md and ARTIFACTS.md framing.