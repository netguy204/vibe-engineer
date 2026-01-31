---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/models.py
- src/orchestrator/state.py
- tests/test_orchestrator_state.py
code_references:
  - ref: src/orchestrator/models.py#WorkUnit::explicit_deps
    implements: "Boolean field signaling declared dependencies bypass oracle detection"
  - ref: src/orchestrator/models.py#WorkUnit::model_dump_json_serializable
    implements: "JSON serialization includes explicit_deps field"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v8
    implements: "Schema migration adding explicit_deps column to database"
  - ref: src/orchestrator/state.py#StateStore::create_work_unit
    implements: "Persistence of explicit_deps on work unit creation"
  - ref: src/orchestrator/state.py#StateStore::update_work_unit
    implements: "Persistence of explicit_deps on work unit update"
  - ref: src/orchestrator/state.py#StateStore::_row_to_work_unit
    implements: "Reading explicit_deps from database row"
  - ref: tests/test_orchestrator_state.py#TestExplicitDepsPersistence
    implements: "Test coverage for explicit_deps persistence behavior"
narrative: explicit_chunk_deps
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
created_after:
- orch_task_worktrees
depends_on: []
---

# Chunk Goal

## Minor Goal

Add an `explicit_deps` boolean field to the `WorkUnit` model in `src/orchestrator/models.py`. This field signals that a work unit uses explicitly declared dependencies (via the chunk's `depends_on` frontmatter) and should bypass the conflict oracle's auto-detection.

This is a foundational change for the explicit_chunk_deps narrative. When `explicit_deps=True`:
- The work unit's `blocked_by` list was populated from declared dependencies at injection time
- The scheduler should skip oracle conflict analysis for this work unit
- Dependencies are authoritative rather than heuristically detected

This enables predictable parallel execution for well-structured work batches where agents know the intended execution order upfront.

## Success Criteria

1. **Model field added**: `WorkUnit` class in `src/orchestrator/models.py` has an `explicit_deps: bool = False` field
2. **JSON serialization updated**: `model_dump_json_serializable()` method includes the `explicit_deps` field
3. **Default preserves current behavior**: Existing work units (without explicit deps) continue to use oracle conflict detection
4. **Tests pass**: Existing orchestrator tests continue to pass
5. **Field is documented**: The field has a docstring-style comment explaining its purpose and relationship to oracle bypass

