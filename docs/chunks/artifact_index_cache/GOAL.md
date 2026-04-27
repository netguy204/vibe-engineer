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

Two performance hotspots related to repeated object construction and N+1 query patterns are addressed:

**(a) Cached `ArtifactIndex` on `ArtifactManager`.** A lazily-initialized `artifact_index` property on `ArtifactManager` ensures all methods (e.g., `list_chunks`, `get_last_active_chunk`, `create_chunk`, `find_overlapping_chunks` in `src/chunks.py`) share a single `ArtifactIndex` instance per manager lifetime, avoiding the per-call overhead of loading the `.artifact-order.json` cache file even though file-level caching exists.

**(b) Single-query attention and ready queues in `src/orchestrator/state.py`.** `get_ready_queue` and `get_attention_queue` each issue one SQL query with a subquery that computes `blocks_count` in one pass, replacing the prior N+1 pattern that fetched all matching work units and then issued an individual `COUNT(*)` query per row.

## Success Criteria

- `ArtifactIndex` is a lazily-initialized property on `ArtifactManager`, not instantiated per-call
- `get_ready_queue` and `get_attention_queue` each use a single SQL query (no N+1 pattern)
- Performance improvement is observable (fewer file reads, fewer SQL queries)
- All existing tests pass

