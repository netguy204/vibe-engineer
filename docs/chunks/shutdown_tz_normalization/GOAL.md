---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/entity_shutdown.py
- src/models/entity.py
- src/entity_decay.py
- tests/test_entity_shutdown.py
code_references:
- ref: src/models/entity.py#MemoryFrontmatter::normalize_last_reinforced_tz
  implements: "Pydantic field_validator that normalizes naive last_reinforced datetimes to UTC-aware on construction, preventing TypeError during datetime arithmetic in shutdown and decay pipelines"
- ref: tests/test_entity_shutdown.py#TestTimezoneNormalization
  implements: "Regression tests for mixed naive/aware datetime handling — model-level validator and full pipeline consolidation path"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- wiki_lint_command
- wiki_reindex_command
- wiki_rename_command
---

# Chunk Goal

## Minor Goal

`ve entity shutdown` runs cleanly through post-API consolidation against
entities whose memory files mix timezone-aware and timezone-naive
timestamps, instead of raising "can't subtract offset-naive and
offset-aware datetimes".

### The crash shape

The consolidation pipeline subtracts datetimes where one side is
timezone-aware (from `datetime.now(timezone.utc)`) and the other had been
naive (parsed from memory files whose stored ISO 8601 strings lacked
timezone markers, e.g. `2026-04-20T14:30:00` vs
`2026-04-20T14:30:00+00:00`). Long-running entities accumulate memory
files written across different code versions, so a single sleep cycle
can encounter both shapes. Without normalization, Python raises
`TypeError: can't subtract offset-naive and offset-aware datetimes`
after the Anthropic API call returns successfully — wiki updates land on
disk but journal extraction, memory consolidation, and core memory
recomputation are skipped.

### Where the timestamps come from

`src/entity_shutdown.py` uses `datetime.now(timezone.utc)` (aware) for
new timestamps. The `MemoryFrontmatter` model
(`src/models/entity.py`) parses `last_reinforced` from stored YAML via
Pydantic's datetime field, which produces a naive datetime when the
stored string lacks timezone info. `entity_decay.py` has its own
inline guard (`if lr.tzinfo is None: lr = lr.replace(tzinfo=timezone.utc)`)
for the same problem on the decay path.

### The normalization

1. A Pydantic `field_validator` on `MemoryFrontmatter.last_reinforced`
   normalizes naive datetimes to UTC-aware on construction, so every
   consumer of the model — shutdown, decay, anything else — sees aware
   datetimes.
2. The existing inline guard pattern in `entity_decay.py` remains in
   place; the model-layer fix is additive, not a replacement.
3. A regression test exercises a fixture entity with intentionally mixed
   naive and aware timestamps in its memory files.

### Cross-project context

Reported by the world-model project's `savings-instruments` entity (~23
sessions). Blocks all sleep-cycle consolidation for long-running wiki entities.
Wiki updates land on disk fine, but journal extraction, memory consolidation,
and core memory recomputation don't happen.

## Success Criteria

- `ve entity shutdown` succeeds against entities with mixed naive/aware
  timestamps in memory files
- Datetime normalization happens at the model layer (MemoryFrontmatter) or
  at every subtraction site
- Regression test exercises mixed-tz timestamps
- Existing entity_decay.py tz handling remains correct
- All tests pass
