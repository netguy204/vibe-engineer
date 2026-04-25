---
status: IMPLEMENTING
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
created_after: ["wiki_snapshot_vs_log"]
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

The project has a canonical statement of what chunks are for. `docs/trunk/CHUNKS.md` declares four principles governing how chunks are used and how their status is interpreted. The status taxonomy in `src/templates/chunk/GOAL.md.jinja2` and `docs/trunk/SPEC.md` derives from those principles, and `docs/trunk/ARTIFACTS.md` points readers at CHUNKS.md as the prerequisite read.

### The four principles (final wording — land verbatim)

**1. Code owns implementation; chunks own intent; together they are the architecture.** Code says *how* the system works — mutable, refactorable, tactical. Chunks say *why* a piece of the system has the shape it has — the constraints, contracts, and boundaries that should outlive any particular implementation. Implementation without intent is code that future contributors will accidentally break. Intent without implementation is a wish.

**2. Chunks exist only for intent-bearing work.** Intent-less work — typos, dependency bumps, mechanical renames, one-off bug patches, performance tweaks that don't change shape, comment cleanup — bypasses the chunk system entirely. Just edit the code, commit, move on. The test is a single question: *does this code need to remember why it exists?* If yes, make a chunk. If no, don't. Over-chunking drowns the architectural signal in noise.

**3. A chunk's GOAL.md describes intent in present tense.** Written so it reads true at every status the chunk passes through. Goals describe how the system works (or, for FUTURE chunks, how it will work) — never what changed, never what we did, never the world as it was. Git owns the past. Avoid framing that ages into a lie:

- ❌ *"Currently the orchestrator does X, but we'll change it to Y."* — true at write time, false once ACTIVE.
- ✅ *"The orchestrator does Y when Z, because..."* — true at every status.

**4. Status answers a single question — how much of the intent does this chunk own?**

| Status | Ownership |
|--------|-----------|
| FUTURE | Not yet owned. Queued for later. |
| IMPLEMENTING | Being taken into ownership. At most one per worktree. |
| ACTIVE | Fully owns the intent that governs the code. |
| COMPOSITE | Shares ownership with other chunks. Must be read alongside its co-owners. |
| HISTORICAL | No longer owns intent. Kept for archaeological context — the approach was replaced, the code was rolled back, or the intent was abandoned. |

Each transition is an answer to the question, not a separate concept.

### Why the taxonomy changes

`COMPOSITE` is a new status, replacing the prior `SUPERSEDED`. Audit of the 12 existing SUPERSEDED chunks shows the old name conflated *"this chunk's approach was replaced"* (a HISTORICAL case under the new framing) with the conceptually distinct *"this chunk shares intent ownership with peers"* (the new COMPOSITE). Splitting them lets status answer the ownership question cleanly.

## Success Criteria

1. **`docs/trunk/CHUNKS.md` exists** containing the four numbered principles above, verbatim. The status table appears under principle 4. The whole doc fits on roughly one screen — it is a punchy reference, not an essay.

2. **`src/templates/chunk/GOAL.md.jinja2` STATUS VALUES block (currently lines 29-34)** matches the new taxonomy. The `SUPERSEDED` line is removed; a `COMPOSITE` line is added; the `ACTIVE` and `HISTORICAL` lines are rewritten to match the table above.

3. **`docs/trunk/SPEC.md` chunk status table (currently lines 214-219)** matches the same taxonomy. `SUPERSEDED` row removed, `COMPOSITE` row added, `ACTIVE` row drops the "or recently-merged work" hedge.

4. **`docs/trunk/ARTIFACTS.md`** has a one-line cross-reference in its chunk-related section pointing at `docs/trunk/CHUNKS.md` as the prerequisite for understanding what chunks are for and how their status is interpreted.

5. **CHUNKS.md reads true under its own principles.** Present-tense, declarative; would still read true a year from now without modification.

6. **`uv run ve init` runs cleanly** after the template change.

7. **`uv run pytest tests/` passes.** If any test breaks, the failure is meaningful — investigate rather than silence.

## Out of Scope (do NOT do these in this chunk)

- **Behavioral changes to skills/commands.** No edits to `/chunk-create` (the intent-test gate), `/chunk-complete` (present-tense verification pass), or CLAUDE.md wording. Seed doc lands first; behavior derives later.
- **Migration of existing SUPERSEDED chunks.** Twelve chunks currently carry `status: SUPERSEDED` (e.g., `websocket_keepalive`, `template_drift_prevention`). Moving them to HISTORICAL or COMPOSITE is a separate audit chunk. They keep their current status for now — the codebase will temporarily contain chunks whose status is not in the new taxonomy. That is acceptable.
- **Backfill audit of ACTIVE chunks** for retrospective framing tells (`Currently,`, `we added`, `this chunk fixes`). Separate sweep chunk.
- **Code-level changes** to status enums/validation in `src/`. *Verify* whether `COMPOSITE` or the absence of `SUPERSEDED` causes validation failures (likely Pydantic enums in `src/models.py`); if so, **stop and surface to the operator** rather than expanding scope. The expected outcome is that status is parsed as a free-form string and no code change is needed.

## Rejected Ideas

### Keep SUPERSEDED, just clarify its definition

Rejected because actual usage of SUPERSEDED across the 12 existing chunks overwhelmingly meant *"this chunk's approach was replaced"* — natural English and embedded usage both pointed at the HISTORICAL meaning. Redefining SUPERSEDED to mean "shares ownership with peers" would have fought both. Cleaner to retire the name and introduce COMPOSITE for the new concept.

### Make co-ownership a relationship field rather than a status

Considered: keep four statuses (FUTURE, IMPLEMENTING, ACTIVE, HISTORICAL), and add a `co_owners: [chunk_a]` frontmatter field for ACTIVE chunks sharing intent. Attractive for lifecycle simplicity but rejected: co-ownership is a meaningfully different *state* — readers should know up-front that this chunk is one voice among several before they read its goal. A status communicates that more loudly than a frontmatter field.

### Use chunks for all work; treat HISTORICAL as the dumping ground

This was the implicit current state, signaled by the existing `bug_type: implementation → HISTORICAL` rule. Rejected because it conflated *chunks that lost intent* (approach replaced) with *chunks that never had intent worth owning* (typo fixes). Per principle 2, the second category never enters the chunk system at all.

### Land seed doc + behavioral changes + migrations in one chunk

Rejected as too large. Seed doc is a unit of architectural intent; behavioral changes derive from it; migrations are mechanical sweeps. Each is independently shippable and reviewable.