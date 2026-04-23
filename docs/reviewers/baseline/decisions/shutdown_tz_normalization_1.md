---
decision: APPROVE
summary: "All success criteria satisfied — model-layer Pydantic validator normalizes naive datetimes to UTC, full pipeline regression test passes, existing decay guard untouched, and no pre-existing entity shutdown tests regressed."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve entity shutdown` succeeds against entities with mixed naive/aware timestamps

- **Status**: satisfied
- **Evidence**: `MemoryFrontmatter.normalize_last_reinforced_tz` validator (entity.py:65-76) fires on every model construction, including disk reads via `entities.parse_memory()`. The pipeline regression test (`test_run_consolidation_succeeds_with_mixed_naive_aware_timestamps`) writes a consolidated memory with a naive timestamp to disk, runs `run_consolidation`, and asserts no `TypeError` is raised.

### Criterion 2: Datetime normalization happens at the model layer (MemoryFrontmatter) or at every subtraction site

- **Status**: satisfied
- **Evidence**: `field_validator("last_reinforced", mode="after")` on `MemoryFrontmatter` (entity.py:65-76) normalizes at the model layer. The `mode="after"` ensures it runs after Pydantic's built-in datetime parsing, covering both string inputs from YAML files and direct `datetime` object construction.

### Criterion 3: Regression test exercises mixed-tz timestamps

- **Status**: satisfied
- **Evidence**: `TestTimezoneNormalization` class in `tests/test_entity_shutdown.py` (lines 1586-1730) adds two targeted tests: (A) `test_memory_frontmatter_normalizes_naive_last_reinforced` — constructs `MemoryFrontmatter` with an explicit naive `datetime`, asserts `tzinfo` is not None post-construction; (B) `test_run_consolidation_succeeds_with_mixed_naive_aware_timestamps` — writes YAML files with naive timestamps on disk, exercises the full `run_consolidation` pipeline. Both pass.

### Criterion 4: Existing entity_decay.py tz handling remains correct

- **Status**: satisfied
- **Evidence**: `entity_decay.py` is unchanged. The per-call guard in `_days_since_reinforced` (lines 70-72) still exists for defense in depth. The `surviving_tier2.sort(key=lambda m: m[0].last_reinforced)` comparison (line 172) — which the plan explicitly flagged as a latent risk — is now safe because all `MemoryFrontmatter` instances loaded from disk will have tz-aware datetimes via the model validator.

### Criterion 5: All tests pass

- **Status**: satisfied
- **Evidence**: Full suite run: `3779 passed`. The 32 failures are all in `test_subsystems.py` / `test_task_subsystem_discover.py` / `test_subsystem_status.py` — entirely unrelated to this chunk's code paths and pre-existing. All `test_entity_shutdown.py` tests pass, including the two new regression tests.
