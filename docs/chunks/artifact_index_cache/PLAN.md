# Implementation Plan

## Approach

This chunk addresses two performance issues:

1. **Redundant ArtifactIndex instantiation**: Cache `ArtifactIndex` as a lazily-initialized property on `ArtifactManager` so all methods share a single instance per manager lifetime. The dependency chunk `artifact_pattern_consolidation` (ACTIVE) has already established the `ArtifactManager` base class pattern which Chunks inherits from.

2. **N+1 query patterns in state.py**: Replace the N+1 COUNT(*) queries in `get_ready_queue` and `get_attention_queue` with single SQL queries using LEFT JOIN and subqueries to compute `blocks_count` in one pass. The existing `list_blocked_by_chunk` method already uses the correct `json_each()` pattern for searching JSON arrays.

The approach follows existing patterns:
- The lazy property pattern is standard Python (see `_get_state_machine()` on `ArtifactManager`)
- The SQL optimization follows the `json_each()` pattern already established in `list_blocked_by_chunk`

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS a performance optimization to `ArtifactIndex` caching. The subsystem documents that `ArtifactIndex` provides cached ordering - we're improving that caching by moving it one level up to avoid repeated instantiation.

- **docs/subsystems/orchestrator** (STABLE): This chunk IMPLEMENTS a performance fix to the state store. The N+1 query pattern is a local optimization that doesn't affect the subsystem's invariants.

## Sequence

### Step 1: Add lazy ArtifactIndex property to ArtifactManager

Add a `_artifact_index` private attribute and an `artifact_index` property to `ArtifactManager` that lazily creates a single `ArtifactIndex` instance. This follows the pattern already used for `_get_state_machine()`.

Location: `src/artifact_manager.py`

```python
@property
def artifact_index(self) -> "ArtifactIndex":
    """Get or create a cached ArtifactIndex for this manager."""
    if self._artifact_index is None:
        from artifact_ordering import ArtifactIndex
        self._artifact_index = ArtifactIndex(self._project_dir)
    return self._artifact_index
```

Add `_artifact_index: "ArtifactIndex" | None = None` to `__init__`.

### Step 2: Update Chunks methods to use cached artifact_index

Update the four call sites in `src/chunks.py` that instantiate `ArtifactIndex`:
- `list_chunks()` (line ~186)
- `get_last_active_chunk()` (line ~264)
- `create_chunk()` (line ~384)
- `find_overlapping_chunks()` (line ~739)

Each should change from:
```python
artifact_index = ArtifactIndex(self.project_dir)
```
to:
```python
artifact_index = self.artifact_index
```

Location: `src/chunks.py`

### Step 3: Fix N+1 in get_attention_queue

Replace the loop-and-count pattern with a single SQL query using a subquery to count blocked work units:

```sql
SELECT w.*, (
    SELECT COUNT(*) FROM work_units b
    WHERE EXISTS (
        SELECT 1 FROM json_each(b.blocked_by)
        WHERE value = w.chunk
    )
) as blocks_count
FROM work_units w
WHERE w.status = ?
ORDER BY blocks_count DESC, w.updated_at ASC
```

Location: `src/orchestrator/state.py`, `get_attention_queue()` method (lines ~674-718)

### Step 4: Fix N+1 in get_ready_queue

Replace the loop-and-count pattern with a single SQL query:

```sql
SELECT w.*, (
    SELECT COUNT(*) FROM work_units b
    WHERE b.status IN (?, ?)
    AND EXISTS (
        SELECT 1 FROM json_each(b.blocked_by)
        WHERE value = w.chunk
    )
) as blocks_count
FROM work_units w
WHERE w.status = ?
ORDER BY blocks_count DESC, w.priority DESC, w.created_at ASC
```

Location: `src/orchestrator/state.py`, `get_ready_queue()` method (lines ~721-782)

### Step 5: Add tests for optimized queries

Add tests that verify the optimized queries return identical results to the previous implementation. The existing tests in `test_orchestrator_state.py` (`TestReadyQueueCriticalPath` class) provide good coverage of the expected behavior - verify they still pass.

Also add a simple test that exercises the artifact_index property caching on ArtifactManager to ensure the same instance is returned on repeated access.

Location: `tests/test_artifact_manager.py` (new file or add to existing), `tests/test_orchestrator_state.py`

### Step 6: Run full test suite

Run `uv run pytest tests/` to ensure all existing tests pass with the optimizations.

## Dependencies

- **artifact_pattern_consolidation** (ACTIVE): This chunk established `ArtifactManager` as the base class. Our change adds a cached property to that base class. This dependency is satisfied.

## Risks and Open Questions

- **Query plan performance**: The correlated subquery approach should be efficient for SQLite's query planner, but if work_units tables grow very large, consider adding an index on `blocked_by` (though JSON indexing in SQLite is limited). For typical orchestrator workloads (<1000 work units), this should not be an issue.

- **Thread safety**: `ArtifactIndex` itself has internal caching. Multiple methods accessing `self.artifact_index` in the same manager instance will share state, which is the intended behavior. SQLite connections are already handled per-StateStore instance with WAL mode.

- **Import cycle**: The lazy import of `ArtifactIndex` in the property getter avoids potential circular import issues between `artifact_manager.py` and `artifact_ordering.py`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->