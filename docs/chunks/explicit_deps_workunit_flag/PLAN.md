<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a straightforward Pydantic model extension. The `WorkUnit` model in `src/orchestrator/models.py` will gain a new `explicit_deps: bool = False` field. The existing patterns in the file show:

1. Optional fields use `= None` or `= []` default values
2. Fields have docstring-style comments explaining their purpose
3. The `model_dump_json_serializable()` method includes all fields

Since this field defaults to `False`, existing work units (created without explicit dependencies) will seamlessly continue using oracle-based conflict detection. The field acts as a signal to downstream consumers (scheduler, oracle) that this work unit's `blocked_by` list was populated from declared dependencies rather than auto-detection.

**Persistence impact**: The `StateStore` in `src/orchestrator/state.py` will require a schema migration (v8) to add the `explicit_deps` column. The `create_work_unit`, `update_work_unit`, and `_row_to_work_unit` methods need to handle this field.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a new field on the WorkUnit model, extending the orchestrator subsystem's data model. The orchestrator subsystem governs parallel agent scheduling, and `explicit_deps` is a foundational field for bypassing oracle conflict detection.

## Sequence

### Step 1: Add `explicit_deps` field to WorkUnit model

Add the new boolean field to the `WorkUnit` class in `src/orchestrator/models.py`:

```python
explicit_deps: bool = False  # Uses declared deps, skip oracle conflict detection
```

Place the field after `conflict_override` and before `created_at` to group it with conflict-related fields. Add a docstring-style comment explaining:
- What the field means (work unit uses explicitly declared dependencies)
- Its relationship to the oracle (when True, scheduler should skip oracle conflict analysis)
- How `blocked_by` is populated (from chunk's `depends_on` frontmatter at injection time)

Location: `src/orchestrator/models.py#WorkUnit`

### Step 2: Update `model_dump_json_serializable()` method

Add `explicit_deps` to the serialization dict in `WorkUnit.model_dump_json_serializable()`:

```python
"explicit_deps": self.explicit_deps,
```

This ensures the field is included in API responses and JSON persistence.

Location: `src/orchestrator/models.py#WorkUnit::model_dump_json_serializable`

### Step 3: Add schema migration v8 for `explicit_deps` column

Add `_migrate_v8()` method to `StateStore` in `src/orchestrator/state.py`:

```python
def _migrate_v8(self) -> None:
    """Add explicit_deps field for declared dependency bypass."""
    self.connection.executescript(
        """
        -- Add explicit_deps column for signaling oracle bypass
        ALTER TABLE work_units ADD COLUMN explicit_deps INTEGER DEFAULT 0;
        """
    )
```

SQLite stores booleans as integers (0/1). The migration adds the column with a default of 0 (False), ensuring existing rows preserve their current behavior.

Update `CURRENT_VERSION` to 8 and add v8 to the migrations dict in `_run_migrations`.

Location: `src/orchestrator/state.py#StateStore`

### Step 4: Update `create_work_unit()` to persist `explicit_deps`

Modify the INSERT statement in `create_work_unit()` to include `explicit_deps`:

- Add `explicit_deps` to the column list
- Add `work_unit.explicit_deps` to the values tuple (as 1 if True, 0 if False)

Location: `src/orchestrator/state.py#StateStore::create_work_unit`

### Step 5: Update `update_work_unit()` to persist `explicit_deps`

Modify the UPDATE statement in `update_work_unit()` to include `explicit_deps`.

Location: `src/orchestrator/state.py#StateStore::update_work_unit`

### Step 6: Update `_row_to_work_unit()` to read `explicit_deps`

Add handling for the `explicit_deps` column when reconstructing a WorkUnit from a database row:

```python
try:
    explicit_deps = bool(row["explicit_deps"]) if row["explicit_deps"] is not None else False
except (IndexError, KeyError):
    explicit_deps = False
```

Pass `explicit_deps=explicit_deps` to the WorkUnit constructor.

Location: `src/orchestrator/state.py#StateStore::_row_to_work_unit`

### Step 7: Verify existing tests pass

Run existing orchestrator tests to confirm the changes don't break anything:

```bash
uv run pytest tests/test_orchestrator_state.py tests/test_orchestrator_*.py -v
```

The changes should be backward compatible - existing tests create WorkUnits without `explicit_deps`, which defaults to `False`.

### Step 8: Add test for `explicit_deps` field behavior

Per TESTING_PHILOSOPHY.md, avoid trivial tests. The meaningful behaviors to test are:

1. **Validation behavior**: Verify that `explicit_deps` accepts boolean values and rejects non-booleans
2. **Round-trip persistence**: Create a WorkUnit with `explicit_deps=True`, save to database, read back, verify value is preserved
3. **Default behavior**: Create a WorkUnit without specifying `explicit_deps`, verify it defaults to `False`
4. **Serialization**: Verify `model_dump_json_serializable()` includes `explicit_deps`

Add tests to `tests/test_orchestrator_state.py` for persistence behavior. The model validation behavior is implicitly tested by Pydantic's type enforcement.

Location: `tests/test_orchestrator_state.py`

## Dependencies

None. This chunk adds a foundational field that other chunks in the `explicit_chunk_deps` narrative will build upon.

## Risks and Open Questions

- **Migration on production databases**: The ALTER TABLE adds a column with a default value. SQLite handles this efficiently for existing rows. No risk identified for typical orchestrator database sizes.

- **Boolean vs integer semantics**: SQLite stores booleans as integers. The `_row_to_work_unit()` method will convert 0/1 to False/True. Non-zero values will be treated as True (standard Python truthiness).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->