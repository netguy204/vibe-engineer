---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - docs/trunk/CHUNKS.md
  - docs/trunk/SPEC.md
  - docs/trunk/ARTIFACTS.md
  - src/templates/chunk/GOAL.md.jinja2
  - src/models/chunk.py
  - src/chunk_validation.py
  - src/cli/chunk.py
  - src/chunks.py
  - src/orchestrator/activation.py
  - tests/test_state_machine.py
  - tests/test_transitions.py
  - tests/test_chunk_validate_inject.py
code_references:
  - ref: docs/trunk/CHUNKS.md
    implements: "Canonical statement of the four intent-ownership principles"
  - ref: src/models/chunk.py#ChunkStatus
    implements: "ChunkStatus enum with COMPOSITE added; status answers how much intent the chunk owns"
  - ref: src/models/chunk.py#VALID_CHUNK_TRANSITIONS
    implements: "State machine transitions extended for COMPOSITE (IMPLEMENTING/ACTIVE→COMPOSITE; COMPOSITE→ACTIVE/HISTORICAL)"
  - ref: src/chunk_validation.py
    implements: "Terminal-for-injection check extended to treat COMPOSITE as settled"
  - ref: src/cli/chunk.py
    implements: "CLI status-filter help text lists COMPOSITE"
  - ref: src/orchestrator/activation.py#_is_post_implementing
    implements: "Post-IMPLEMENTING status check; derives reachable statuses dynamically so COMPOSITE is recognized automatically"
  - ref: docs/trunk/SPEC.md
    implements: "Status table and frontmatter schema example reflect new five-status taxonomy"
  - ref: docs/trunk/ARTIFACTS.md
    implements: "Cross-reference pointing readers at CHUNKS.md as the prerequisite read"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Chunk GOAL template STATUS VALUES block reframed as ownership-of-intent"
  - ref: tests/test_state_machine.py
    implements: "Tests for COMPOSITE transitions: IMPLEMENTING→COMPOSITE, ACTIVE→COMPOSITE, COMPOSITE→ACTIVE, COMPOSITE→HISTORICAL"
  - ref: tests/test_transitions.py#TestChunkTransitionValues::test_composite_transitions
    implements: "Exhaustive transition-set test for COMPOSITE"
  - ref: tests/test_chunk_validate_inject.py
    implements: "Inject-validation test for COMPOSITE-status chunks"
narrative: intent_ownership
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after: ["wiki_snapshot_vs_log"]
---


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