
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add decay mechanics to the entity memory system, integrated into the existing shutdown consolidation pipeline (`src/entity_shutdown.py`). The decay logic runs as a post-consolidation step: after the LLM has associated new journals with existing tiers, apply recency-based decay and capacity pressure to bound memory growth.

The implementation follows three principles:

1. **Decay is deterministic, not LLM-driven.** The consolidation step (LLM) handles association and promotion. The decay step (code) handles expiration and demotion using timestamps and counts. This keeps decay auditable and testable without mocking API calls.

2. **Two complementary mechanisms.** Recency-based decay handles memories that stop being relevant over time. Capacity pressure handles the case where many memories are actively reinforced but the tier budget is exceeded. Both use `last_reinforced` as the primary signal.

3. **Configuration via a dataclass with sensible defaults.** Decay parameters (tier budgets, cycle thresholds) are configurable but have defaults derived from the investigation findings: 15 core memories, 5 cycles for tier-0 expiry. Configuration lives in code, not in files — there's no operator-facing config file for this yet.

This chunk builds on:
- `src/entities.py` — `Entities` class for memory CRUD and `list_memories`/`parse_memory`
- `src/entity_shutdown.py` — `run_consolidation` pipeline where decay integrates
- `src/models/entity.py` — `MemoryFrontmatter` model with `last_reinforced`, `salience`, `tier`, `recurrence_count`

Per DEC-008, decay configuration uses Pydantic `BaseModel` for validation.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md: tests are written first (TDD), assert semantic behavior at boundaries (not storage), and focus on the success criteria from GOAL.md. The core decay logic is a pure function (memories in, decisions out) — highly testable without filesystem or API mocks. A multi-cycle simulation test verifies the 20+ cycle boundedness criterion.

## Sequence

### Step 1: Define DecayConfig and DecayEvent models

Create a `DecayConfig` dataclass/Pydantic model with the tuning parameters, and a `DecayEvent` model for audit logging.

**DecayConfig fields:**
- `tier0_expiry_cycles: int = 5` — Journal memories expire after this many consolidation cycles without association
- `tier1_decay_cycles: int = 8` — Consolidated memories expire after this many cycles without reinforcement
- `tier2_demote_cycles: int = 10` — Core memories demote to tier-1 after this many cycles without reinforcement
- `tier2_capacity: int = 15` — Soft budget for core memories
- `tier1_capacity: int = 30` — Soft budget for consolidated memories

**DecayEvent fields:**
- `timestamp: datetime`
- `memory_title: str`
- `memory_id: str` (filename stem)
- `action: str` — one of: "expired", "demoted", "salience_reduced"
- `from_tier: str`
- `to_tier: str | None` (None for expiration)
- `reason: str` — human-readable explanation (e.g., "unreinforced for 7 consolidation cycles", "capacity pressure: 18/15 core memories")

Location: `src/models/entity.py`

### Step 2: Write tests for the decay functions (TDD red phase)

Write tests for the decay logic before implementing it. Tests go in `tests/test_entity_decay.py`. Each test maps to a success criterion from GOAL.md:

**Recency-based decay tests:**
- `test_tier0_expires_after_n_cycles_without_association` — Create journal memories with old `last_reinforced`, run decay, verify they're marked for expiration
- `test_tier0_survives_when_recently_reinforced` — Journal memory with recent `last_reinforced` survives
- `test_tier1_decays_salience_then_expires` — Consolidated memory unreinforced for N cycles loses salience, then expires
- `test_tier1_survives_when_reinforced` — Consolidated memory with recent touch survives
- `test_tier2_demotes_to_tier1_when_unreinforced` — Core memory unreinforced for M cycles demotes
- `test_tier2_survives_when_reinforced` — Core memory with recent reinforcement stays

**Capacity pressure tests:**
- `test_tier2_capacity_pressure_demotes_least_recent` — When core count exceeds budget, least-recently-reinforced memories demote first
- `test_tier2_under_budget_no_pressure` — When core count is within budget, no capacity-driven demotion
- `test_capacity_and_recency_combine` — Capacity pressure selects among unreinforced memories first

**Reinforcement signal tests:**
- `test_touch_events_update_last_reinforced` — Memories touched via `ve entity touch` have updated timestamps that prevent decay
- `test_consolidation_reinforcement_prevents_decay` — Memories reinforced during consolidation (via LLM association) resist decay

**Boundedness test:**
- `test_20_cycle_simulation_stays_bounded` — Simulate 20+ consolidation cycles, each adding 10-15 journal memories. Verify core count never exceeds capacity budget and startup payload stays under 4K tokens.

**Audit logging test:**
- `test_decay_produces_audit_events` — Verify that decay returns DecayEvent objects describing what was decayed and why

The decay function under test will have this signature:
```python
def apply_decay(
    memories: list[tuple[MemoryFrontmatter, str, Path]],  # (frontmatter, content, file_path)
    current_cycle: datetime,
    config: DecayConfig,
) -> DecayResult  # contains: survivors, demotions, expirations, events
```

This is a pure function — it takes memory data and returns decisions. The caller (run_consolidation) applies the decisions to disk.

### Step 3: Implement the decay functions (TDD green phase)

Create `src/entity_decay.py` with the core decay logic.

**`apply_decay()` function:**

1. **Calculate cycle age** for each memory: `(current_cycle - last_reinforced).days` divided by a cycle duration (1 day default, since consolidation runs at shutdown).

2. **Recency-based decay pass** (all tiers):
   - Tier 0: If cycles_since_reinforced >= `tier0_expiry_cycles` → expire
   - Tier 1: If cycles_since_reinforced >= `tier1_decay_cycles` → expire. If cycles_since_reinforced >= `tier1_decay_cycles // 2` → reduce salience by 1 (floor at 1)
   - Tier 2: If cycles_since_reinforced >= `tier2_demote_cycles` → demote to tier 1

3. **Capacity pressure pass** (tier 2 only, after recency pass):
   - Count surviving tier-2 memories
   - If count > `tier2_capacity`: sort by `last_reinforced` ascending (oldest first), demote excess memories to tier 1
   - Demoted memories retain their content and metadata but have `tier` changed to `consolidated`

4. **Return a `DecayResult`** with:
   - `survivors`: memories that passed both checks (unchanged)
   - `demotions`: list of (memory, new_tier) for memories that moved down
   - `expirations`: list of memories to remove
   - `events`: list of `DecayEvent` for audit logging

Location: `src/entity_decay.py`

### Step 4: Add a consolidation cycle counter to entity state

The decay system needs to know how many consolidation cycles have elapsed. Add a lightweight mechanism to track this.

**Approach:** Add a `decay_log.jsonl` file at `.entities/<name>/decay_log.jsonl` that records each cycle's decay events. The number of lines (or entries) in this file implicitly tracks cycle count. Additionally, each DecayEvent is appended here for audit.

Add to `src/entities.py`:
- `append_decay_events(entity_name, events: list[DecayEvent])` — Append decay events to the JSONL log
- `read_decay_log(entity_name) -> list[DecayEvent]` — Read all decay events for audit

The cycle count doesn't need to be explicit — the `last_reinforced` timestamp on each memory compared to `current_cycle` (now) gives the effective age. The decay function uses elapsed time, not an integer counter.

### Step 5: Integrate decay into the consolidation pipeline

Modify `run_consolidation()` in `src/entity_shutdown.py` to call `apply_decay()` after the LLM consolidation step and before writing tiers to disk.

**Integration point** — after Step 6 (parse response) and before Step 7 (write updated tiers):

1. Collect all memories from the consolidation result (consolidated + core) along with any surviving unconsolidated journals
2. Call `apply_decay(memories, now, config)`
3. Apply decay decisions:
   - **Expirations**: Don't write these memories to disk (they're dropped)
   - **Demotions**: Change the memory's tier before writing (tier 2 → write to consolidated dir)
   - **Survivors**: Write as normal
4. Append decay events to the entity's `decay_log.jsonl`
5. Update the return summary to include decay stats: `{"expired": N, "demoted": M}`

Also modify the consolidation to handle pre-existing journal memories that weren't associated by the LLM (the `unconsolidated` list). These need to be checked against tier-0 decay rules. Load all journal tier files, check which ones appear in `unconsolidated`, and apply tier-0 expiry to old ones.

### Step 6: Write integration tests for the full pipeline

Add tests in `tests/test_entity_decay_integration.py` that exercise the full flow through `run_consolidation()` with decay enabled.

**Tests:**
- `test_consolidation_with_decay_removes_old_journals` — Pre-populate journal memories with old timestamps, run consolidation, verify old journals are cleaned up
- `test_consolidation_with_decay_demotes_unreinforced_core` — Pre-populate core memories with old `last_reinforced`, run consolidation (with mocked API), verify they're moved to consolidated tier
- `test_decay_log_written` — After consolidation with decay, verify `decay_log.jsonl` contains the expected events
- `test_consolidation_summary_includes_decay_stats` — Verify the return dict from `run_consolidation()` includes decay statistics

These tests will mock the Anthropic API (same pattern as existing `test_entity_shutdown.py` tests) and use real filesystem via `tmp_path`.

### Step 7: Multi-cycle simulation test

Write a dedicated simulation test that validates the boundedness success criterion:

**`test_memory_stays_bounded_over_20_cycles`:**
1. Create an entity
2. For each of 20+ cycles:
   - Generate 10-15 synthetic journal memories with varied categories and saliences
   - For some memories, reuse titles/content from previous cycles (simulating recurring themes)
   - Run `apply_decay()` on the full memory set
   - Apply the decay decisions to the in-memory collection
   - Run a mock consolidation (promote recurring themes, merge similar)
3. After all cycles, assert:
   - Core memory count <= `tier2_capacity` (default 15)
   - Total startup payload (core content + consolidated titles) <= 4K tokens (~16K chars)
   - At least some memories survived all 20 cycles (the "daily skills" case)
   - At least some memories were expired (the "project-phase skills" case)

This test exercises the combined effect described in the GOAL: "skills used daily stay core forever; skills critical during a past project phase but no longer relevant gradually fade."

### Step 8: Update code_paths and backreferences

Update `docs/chunks/entity_memory_decay/GOAL.md` frontmatter with the code paths touched:
- `src/entity_decay.py` (new)
- `src/models/entity.py` (modified — DecayConfig, DecayEvent)
- `src/entity_shutdown.py` (modified — decay integration)
- `src/entities.py` (modified — decay log methods)
- `tests/test_entity_decay.py` (new)
- `tests/test_entity_decay_integration.py` (new)

Add `# Chunk: docs/chunks/entity_memory_decay` backreference comments to:
- `src/entity_decay.py` module-level
- `apply_decay()` function
- `DecayConfig` and `DecayEvent` classes in `src/models/entity.py`
- The decay integration block in `src/entity_shutdown.py#run_consolidation`

## Dependencies

- **entity_shutdown_skill** (ACTIVE): Provides `run_consolidation()` pipeline where decay integrates, and the `parse_consolidation_response()` output format that decay operates on
- **entity_touch_command** (ACTIVE): Provides the runtime reinforcement signal (`last_reinforced` updates via `ve entity touch`) that decay uses as its primary keep-alive signal
- **entity_memory_schema** (ACTIVE): Provides `MemoryFrontmatter` model with `last_reinforced`, `salience`, `tier` fields that decay reads

No new external libraries needed. The decay logic is pure Python datetime arithmetic.

## Risks and Open Questions

- **Cycle duration assumption**: The decay function uses elapsed time (`last_reinforced` vs `now`) rather than counting discrete consolidation events. This means if an entity runs multiple consolidation cycles per day, the effective decay rate is faster than intended. This is acceptable for now — the configurable thresholds can be tuned. If this becomes a problem, an explicit cycle counter could be added.
- **Journal cleanup scope**: The current `run_consolidation()` writes new journals but doesn't clean up old ones. The decay integration needs to load existing journal files to apply tier-0 expiry, which is new behavior. This must not break the existing flow where journals are preserved for archaeology.
- **Token counting**: The 4K token success criterion requires estimating token count from character count. The investigation used ~4 chars/token as a heuristic. A precise tokenizer is not worth adding as a dependency; the character-based estimate is sufficient for a soft budget.
- **Interaction with LLM consolidation**: The LLM may reference memories in its response that decay would remove. The order matters: LLM consolidation runs first (may promote or merge), then decay runs on the result. This ensures decay doesn't fight the LLM's judgment about current-cycle relevance.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->