---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/artifact_manager.py
  - src/chunks.py
  - src/orchestrator/state.py
  - tests/test_orchestrator_state.py
code_references:
  - ref: src/artifact_manager.py#ArtifactManager::artifact_index
    implements: "Lazy ArtifactIndex property caching per-manager instance"
  - ref: src/orchestrator/state.py#StateStore::get_attention_queue
    implements: "Single SQL query with subquery for blocks_count (N+1 fix)"
  - ref: src/orchestrator/state.py#StateStore::get_ready_queue
    implements: "Single SQL query with subquery for blocks_count (N+1 fix)"
narrative: arch_review_remediation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- artifact_pattern_consolidation
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

This chunk addresses two performance issues related to repeated object construction and N+1 query patterns:

**(a) Redundant `ArtifactIndex` instantiation in `src/chunks.py`.** `ArtifactIndex` is instantiated repeatedly across `list_chunks` (~line 187), `get_last_active_chunk` (~line 265), `create_chunk` (~line 385), and `find_overlapping_chunks` (~line 740). While `ArtifactIndex` has file-level caching via `.artifact-order.json`, the repeated construction still incurs overhead from loading the cache file each time. The fix is to cache the `ArtifactIndex` as a lazily-initialized property on `ArtifactManager`, so that all methods share a single instance per manager lifetime.

**(b) N+1 query patterns in `src/orchestrator/state.py`.** `get_ready_queue` (around lines 721-782) and `get_attention_queue` (around lines 674-718) fetch all matching work units and then loop over them issuing individual `COUNT(*)` queries for each to compute `blocks_count`. This N+1 pattern degrades as the number of work units grows. Replace these with a single SQL query per method using a LEFT JOIN or subquery to compute `blocks_count` in one pass.

## Success Criteria

- `ArtifactIndex` is a lazily-initialized property on `ArtifactManager`, not instantiated per-call
- `get_ready_queue` and `get_attention_queue` each use a single SQL query (no N+1 pattern)
- Performance improvement is observable (fewer file reads, fewer SQL queries)
- All existing tests pass

