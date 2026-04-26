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

Existing ACTIVE chunks are audited for goals that don't describe code as it actually stands. Two failure modes get caught — both variants of "the chunk's GOAL.md lies about the system":

**(1) Retrospective framing** — goal text written in past or transitional tense that ages into a lie once the chunk is ACTIVE. Tells: `Currently,`, `was`, `we added`, `this chunk fixes`, `this chunk adds`, `the fix:`, `will change to`.

Anchor case: `docs/chunks/orch_activate_on_inject/GOAL.md:46` — the goal opens with *"Currently, the orchestrator injects FUTURE chunks and immediately runs the PLAN phase, but the `/chunk-plan` skill uses..."* That `Currently,` describes a world that no longer exists once the chunk is ACTIVE.

**(2) Over-claimed scope** — goal asserts behaviors the code doesn't implement. The chunk often admits this in its own metadata. Tells:
- Any `code_references[].status: partial`
- `implements:` text containing `does NOT implement`, `partial`, `only Step N of M`, `TODO`, `not yet`
- Success-criteria list count meaningfully exceeding the count of referenced symbols (e.g., 5 success criteria, 1 code_reference)

Anchor case: `docs/chunks/respect_future_intent/GOAL.md` — status: ACTIVE, lists 5 success criteria, but its single `code_reference` admits *"does NOT implement user intent detection, priority order, conflict handling, or safe pause protocol from success criteria"* with `status: partial`.

The audit fans out across sub-agents, **5 chunks per sub-agent**, run in parallel. Each sub-agent works through its assigned chunks one at a time and takes one of two actions per chunk:

- **Present-tense grammar fix (inline).** When retrospective framing is detected, the sub-agent rewrites the prose into present tense describing how the system works, using the implemented code as the source of truth. **The intent of the chunk does not change.** Only the tense and framing change. If a passage can't be reframed without altering meaning — e.g., the goal text is so tangled with retrospective claims that present-tense rewording would shift what the chunk asserts — the sub-agent leaves it alone and instead writes an inconsistency entry describing why.
- **Intent-vs-code consistency entry (log only).** When over-claimed scope is detected, the sub-agent writes an entry to `docs/trunk/INCONSISTENCIES/` per its README. The sub-agent does **not** revise the goal down or attempt to finish the missing implementation. Both of those decisions require operator judgment — change the intent, change the implementation, or accept the gap — and that triage happens later, manually, informed by the log.

The asymmetry mirrors the principles: tense is grammar (mechanical, safe to fix); intent is architecture (load-bearing, operator-only).

The discovery pass is exhaustive — every ACTIVE chunk under `docs/chunks/` is reviewed exactly once across the parallel sub-agents.

## Success Criteria

1. The audit enumerates all ACTIVE chunks under `docs/chunks/` and partitions them across sub-agents at 5 chunks per sub-agent. Every ACTIVE chunk is assigned to exactly one sub-agent.
2. Sub-agents run in parallel; each receives a self-contained prompt with its assigned chunk list, the detection criteria, the action rules ("rewrite tense inline; log intent mismatches; never change intent"), and a pointer to `docs/trunk/INCONSISTENCIES/README.md`.
3. The retrospective-framing detector catches `orch_activate_on_inject` (anchor case) — the sub-agent assigned this chunk produces an in-place rewrite that removes the leading `Currently,` framing while preserving the chunk's architectural assertion.
4. The over-claimed-scope detector catches `respect_future_intent` (anchor case) — the sub-agent assigned this chunk produces an inconsistency entry naming the partial-implementation evidence and listing fix paths (revise goal vs finish implementation) for later operator triage.
5. For every retrospective-framing fix, the sub-agent's edit changes only the tense/framing of the prose. The chunk's success criteria, code_paths, code_references, and architectural claims are untouched. (A diff that touches only narrative prose passes; a diff that adds, removes, or reworks success criteria fails this check.)
6. Every over-claimed-scope finding produces exactly one entry in `docs/trunk/INCONSISTENCIES/` with `status: open`. No goal revisions or implementation work happens during the audit.
7. After all sub-agents finish, the audit produces a parent-level summary listing: chunks rewritten (with the grep tells removed), inconsistency entries created (with filenames), and any chunks the sub-agents skipped or escalated.
8. `uv run ve init` runs cleanly after the rewrites.
9. `uv run pytest tests/` passes — no test should be affected by tense rewrites; if any breaks, investigate before silencing.

## Out of Scope

- Adding the verification pass to `/chunk-complete` (chunk 3 does that — running this audit is what catches everything that landed *before* the verification pass existed).
- Migrating SUPERSEDED chunks (chunk 5).
- Removing SUPERSEDED from the runtime (chunk 7).
- Revising any goal's intent or finishing any implementation surfaced by the over-claimed-scope detector. Those are explicitly deferred to manual operator triage informed by the inconsistency log.
- Auditing FUTURE, IMPLEMENTING, COMPOSITE, or HISTORICAL chunks. Only ACTIVE chunks fall in scope; other statuses either haven't reached the truthfulness bar yet (FUTURE/IMPLEMENTING) or are explicitly not asserting current reality (COMPOSITE shares ownership; HISTORICAL no longer governs).