---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- tests/test_models.py
code_references:
- ref: src/models.py#SubsystemFrontmatter
  implements: created_after field for subsystem causal ordering
- ref: src/models.py#NarrativeFrontmatter
  implements: created_after field for narrative causal ordering
- ref: src/models.py#InvestigationFrontmatter
  implements: created_after field for investigation causal ordering
- ref: src/models.py#ChunkFrontmatter
  implements: created_after field for chunk causal ordering
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after:
- chunk_frontmatter_model
---

# Chunk Goal

## Minor Goal

Add the `created_after: list[str]` field to all workflow artifact frontmatter models in `src/models.py`. This is the foundation for causal ordering, enabling merge-friendly parallel work by replacing sequence-number-based ordering with explicit dependency tracking.

This is the first chunk in the causal ordering initiative documented in `docs/investigations/0001-artifact_sequence_numbering`. The `created_after` field captures which artifacts existed (as "tips" with no dependents) when a new artifact was created, forming a directed acyclic graph (DAG) of causal relationships.

## Success Criteria

- `ChunkFrontmatter` has `created_after: list[str] = []` field
- `NarrativeFrontmatter` has `created_after: list[str] = []` field
- `InvestigationFrontmatter` has `created_after: list[str] = []` field
- `SubsystemFrontmatter` has `created_after: list[str] = []` field
- Field defaults to empty list (existing artifacts will be migrated in a later chunk)
- Field contains short names only (e.g., `["chunk_frontmatter_model"]`), not full directory names
- All existing tests pass
- New tests validate the field accepts lists of strings