---
decision: APPROVE
summary: "All seven success criteria satisfied with clean pure-function architecture, comprehensive tests (21 passing), and proper integration into the consolidation pipeline"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Tier-0 memories expire after N consolidation cycles without association (N is configurable, suggest default 5)

- **Status**: satisfied
- **Evidence**: `src/entity_decay.py:80-96` — tier-0 recency pass expires journals when `days_since >= config.tier0_expiry_cycles`. Default is 5 in `DecayConfig`. Tests: `TestTier0Decay` (3 tests including boundary case).

### Criterion 2: Tier-1 memories decay salience and eventually expire without reinforcement

- **Status**: satisfied
- **Evidence**: `src/entity_decay.py:98-135` — tier-1 pass reduces salience at half-threshold (`tier1_decay_cycles // 2`) and expires at full threshold. Salience floors at 1. Tests: `TestTier1Decay` (4 tests).

### Criterion 3: Tier-2 memories can be demoted to tier-1 when unreinforced and under capacity pressure

- **Status**: satisfied
- **Evidence**: `src/entity_decay.py:137-183` — two complementary mechanisms: recency-based demotion after `tier2_demote_cycles` days, then capacity pressure pass demotes least-recently-reinforced when count exceeds `tier2_capacity`. Tests: `TestTier2Decay` (2 tests) + `TestCapacityPressure` (3 tests including combined scenario).

### Criterion 4: Tier-2 capacity budget is configurable (suggest default 15 memories)

- **Status**: satisfied
- **Evidence**: `src/models/entity.py:122-126` — `DecayConfig.tier2_capacity` field with `default=15, ge=1`. Also `tier1_capacity=30` as a bonus. Configuration is Pydantic BaseModel per DEC-008.

### Criterion 5: Both reinforcement signals are respected: consolidation-time association AND runtime touch events

- **Status**: satisfied
- **Evidence**: Both signals update `last_reinforced` on the `MemoryFrontmatter`, which is the sole input signal to `apply_decay()`. Touch events update via `Entities.touch_memory()` (entity_touch_command chunk). Consolidation reinforcement happens when the LLM updates `last_reinforced` in its response. Tests: `TestReinforcementSignals` (2 tests).

### Criterion 6: After 20+ simulated consolidation cycles, the memory set remains bounded (startup payload stays under 4K tokens)

- **Status**: satisfied
- **Evidence**: `tests/test_entity_decay.py::TestBoundednessSimulation::test_20_cycle_simulation_stays_bounded` — runs 25 cycles, each adding 8 one-off journals + 5 recurring themes. Asserts core count ≤ 15, startup payload ≤ 4K tokens, recurring themes survive, early one-offs expire. Test passes.

### Criterion 7: Decay is logged so the operator can audit what was forgotten and why

- **Status**: satisfied
- **Evidence**: `DecayEvent` model in `src/models/entity.py:134-152` with timestamp, memory_title, memory_id, action, from_tier, to_tier, reason. `Entities.append_decay_events()` writes to `decay_log.jsonl`. `Entities.read_decay_log()` reads back. Integration test `test_decay_log_written` verifies end-to-end.
