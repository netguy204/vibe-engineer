---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/integrity.py
- src/chunks.py
- tests/test_integrity.py
code_references:
- ref: src/integrity.py#IntegrityValidator::validate_chunk
  implements: "Unified single-chunk validation entry point (replacement for deprecated standalone functions)"
- ref: src/chunks.py#Chunks::validate_subsystem_refs
  implements: "Chunk subsystem validation wrapper routing through IntegrityValidator"
- ref: src/chunks.py#Chunks::validate_investigation_ref
  implements: "Chunk investigation validation wrapper routing through IntegrityValidator"
- ref: src/chunks.py#Chunks::validate_narrative_ref
  implements: "Chunk narrative validation wrapper routing through IntegrityValidator"
- ref: src/chunks.py#Chunks::validate_friction_entries_ref
  implements: "Chunk friction entries validation wrapper routing through IntegrityValidator"
narrative: arch_review_cleanup
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- dead_code_removal
- narrative_compact_extract
- persist_retry_state
- repo_cache_dry
- reviewer_decisions_dedup
- worktree_merge_extract
- phase_aware_recovery
---

# Chunk Goal

## Minor Goal

Delete the four deprecated standalone validation functions in `src/integrity.py` (lines 772-914): `validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, and `validate_chunk_friction_entries_ref`. These functions are backward-compatibility shims that emit deprecation warnings and delegate to the `Chunks` class methods, which themselves already route through `IntegrityValidator`. No production code calls these functions -- the migration to `IntegrityValidator` is complete. Removing them eliminates ~142 lines of dead code and their associated test class (`TestDeprecatedStandaloneFunctions` in `tests/test_integrity.py`, 5 tests), reducing maintenance burden and cognitive load when navigating the validation subsystem. This is the first chunk in the arch_review_cleanup narrative's dead code removal tier.

## Success Criteria

- The four functions `validate_chunk_subsystem_refs`, `validate_chunk_investigation_ref`, `validate_chunk_narrative_ref`, and `validate_chunk_friction_entries_ref` no longer exist in `src/integrity.py`
- The `TestDeprecatedStandaloneFunctions` test class and all five of its test methods are removed from `tests/test_integrity.py`
- No remaining imports of these four function names exist anywhere in the non-worktree source or test files
- The backreference comments in `src/chunks.py` that reference `integrity.validate_chunk_*` are updated or removed to reflect the new reality (the `Chunks` methods route through `IntegrityValidator`, not through the deleted standalone functions)
- The `warnings` import in `src/integrity.py` is removed if no other code in the file uses it
- All existing tests pass (`uv run pytest tests/`)
