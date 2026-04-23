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

Fix `ve entity shutdown` crash: "can't subtract offset-naive and offset-aware
datetimes" during post-API consolidation.

### The bug

`ve entity shutdown <name>` fails after the Anthropic API call returns
successfully. The consolidation pipeline subtracts datetimes where one side
is timezone-aware (from `datetime.now(timezone.utc)`) and the other is naive
(parsed from memory files that lack timezone markers in their stored ISO 8601
strings).

Error: `can't subtract offset-naive and offset-aware datetimes`

### Root cause analysis

The shutdown code (`src/entity_shutdown.py`) uses `datetime.now(timezone.utc)`
(aware) for new timestamps. But the `MemoryFrontmatter` model
(`src/models/entity.py:57`) parses `last_reinforced` from stored YAML via
Pydantic's datetime field, which produces naive datetimes when the stored
string lacks timezone info (e.g., `2026-04-20T14:30:00` vs
`2026-04-20T14:30:00+00:00`).

Long-running entities accumulate memory files written across different code
versions — some with timezone offsets, some without. When consolidation
subtracts these mixed datetimes, Python raises TypeError.

Note: `entity_decay.py` already handles this correctly with explicit
normalization (`if lr.tzinfo is None: lr = lr.replace(tzinfo=timezone.utc)`).
The consolidation pipeline in `entity_shutdown.py` lacks this same guard.

### The fix

1. Add a Pydantic validator on `MemoryFrontmatter.last_reinforced` (and any
   other datetime fields) that normalizes naive datetimes to UTC-aware.
   This fixes it at the model layer so all consumers get aware datetimes.

2. Alternatively/additionally, add the same guard pattern used in
   `entity_decay.py:68-71` to any datetime subtraction in
   `entity_shutdown.py`.

3. Add a regression test using a fixture entity with intentionally mixed-tz
   timestamps in memory files.

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
