---
discovered_by: claude
discovered_at: 2026-04-26T02:37:48+00:00
severity: medium
status: open
resolved_by: null
artifacts:
  - docs/chunks/entity_memory_decay/GOAL.md
  - src/entity_decay.py
  - src/models/entity.py
  - src/entity_shutdown.py
  - src/entities.py
---

# entity_memory_decay has empty code_references despite implementation existing

## Claim

`docs/chunks/entity_memory_decay/GOAL.md` is ACTIVE and asserts seven
substantive success criteria covering recency-based decay, capacity
pressure, configurable thresholds, reinforcement-signal integration, an
audit trail, and bounded growth across 20+ cycles. Its frontmatter
declares five `code_paths` (entity_decay.py, models/entity.py,
entity_shutdown.py, entities.py, plus two test files) but its
`code_references` array is **empty**:

```yaml
code_references: []
```

A reader of the chunk has no way to navigate from the goal to the
specific symbols that implement it.

## Reality

The implementation actually exists in the named code_paths and is
backreferenced from those files to this chunk:

- `src/entity_decay.py#apply_decay` — recency-based decay and capacity
  pressure (the load-bearing pure function).
- `src/entity_decay.py#DecayResult` — partition of survivors, demotions,
  expirations, and decay events.
- `src/models/entity.py#DecayConfig` — configurable thresholds with the
  defaults the success criteria specify (`tier0_expiry_cycles=5`,
  `tier2_capacity=15`).
- `src/models/entity.py#DecayEvent` — audit log row schema for the
  `decay_log.jsonl` file.
- `src/entity_shutdown.py#run_consolidation` — integrates `apply_decay`
  as Step 8 of the consolidation pipeline (search "Step 8: Apply decay
  to bound memory growth").
- `src/entities.py#Entities::append_decay_events` and
  `src/entities.py#Entities::read_decay_log` — write and read the
  `decay_log.jsonl` audit trail per success criterion 7.
- `tests/test_entity_decay.py` and
  `tests/test_entity_decay_integration.py` — exercise the bounded-growth
  property over many simulated cycles.

The chunk's substantive claims appear to be realized; only the
`code_references` array is empty. This is undeclared *under-claim* in
metadata (the inverse of the typical over-claim failure mode): the goal
is honest about what was built, but the navigation pointers are missing.

## Workaround

None — the audit logs only. A reader needing to find the implementation
must grep `# Chunk: docs/chunks/entity_memory_decay` across the source
tree (which yields `entity_decay.py`, `models/entity.py`,
`entity_shutdown.py`, and `entities.py`) and read those backreferences
manually.

## Fix paths

1. **Populate `code_references`** (preferred): add ref/implements rows
   for the symbols listed under Reality above so the chunk's metadata
   matches the backreferences already present in the source.
2. **Audit the chunk under `/chunk-review`**: the missing references may
   indicate the chunk was completed outside the standard
   `chunk-complete` flow (which normally wires references from code
   backreferences). Running the review may surface other gaps.
